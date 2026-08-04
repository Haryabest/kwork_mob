"""ComfyUI-стиль: shape → refine → texture → export."""

from __future__ import annotations

import os
from pathlib import Path

from trellis_mesh_ops import apply_pre_export_ops, fill_mesh_holes
from trellis_runtime import (
    _export_trellis2_mesh,
    _free_cuda_memory,
    _mesh_to_cpu,
    _pipeline_type_resolved,
    _prepare_multi_cond,
    _progress,
    _release_vram_before_export,
    _require_nobg_dir,
    _resolve_attn_backend,
    _sampler_params,
    _sync_trellis_attn_modules,
    _trim_vram_before_decode,
    get_pipeline,
    inject_sampler_multi_image,
    multi_image_mode,
    pick_input_images,
    preflight_cuda,
    release_pipeline,
)


def _ss_resolution(pipeline_type: str) -> int:
    override = (os.getenv("TRELLIS2_SS_RESOLUTION") or "").strip()
    if override:
        try:
            val = int(override)
            # 32 для cascade — официальный default; 64 ломает sparse structure sampler
            if pipeline_type in ("1024_cascade", "1536_cascade") and val != 32:
                _progress(f"SS_RESOLUTION={val} ignored for {pipeline_type}, using 32")
                return 32
            return val
        except ValueError:
            pass
    return {"512": 32, "1024": 64, "1024_cascade": 32, "1536_cascade": 32}.get(pipeline_type, 32)


def _tex_params_with_downsampling(tex_defaults: dict) -> dict:
    params = _sampler_params("TEX", tex_defaults)
    raw = (os.getenv("TRELLIS2_DOWNSAMPLING") or "").strip()
    if raw:
        try:
            params["downsampling"] = int(raw)
        except ValueError:
            pass
    return params


def _sample_shape_cascade(pipe, pipeline_type: str, cond_512, cond_1024, coords, shape_params, max_tokens):
    if pipeline_type == "512":
        slat = pipe.sample_shape_slat(
            cond_512, pipe.models["shape_slat_flow_model_512"], coords, shape_params
        )
        return slat, 512
    if pipeline_type == "1024":
        slat = pipe.sample_shape_slat(
            cond_1024, pipe.models["shape_slat_flow_model_1024"], coords, shape_params
        )
        return slat, 1024
    if pipeline_type == "1024_cascade":
        return pipe.sample_shape_slat_cascade(
            cond_512,
            cond_1024,
            pipe.models["shape_slat_flow_model_512"],
            pipe.models["shape_slat_flow_model_1024"],
            512,
            1024,
            coords,
            shape_params,
            max_tokens,
        )
    if pipeline_type == "1536_cascade":
        return pipe.sample_shape_slat_cascade(
            cond_512,
            cond_1024,
            pipe.models["shape_slat_flow_model_512"],
            pipe.models["shape_slat_flow_model_1024"],
            512,
            1536,
            coords,
            shape_params,
            max_tokens,
        )
    raise ValueError(f"unsupported pipeline_type={pipeline_type}")


def run_comfy_staged(task_dir: Path, output: Path) -> Path:
    """ComfyUI: voxel gen → fill holes → refiner → fill holes → texture → mesh ops → export."""
    import torch
    from PIL import Image

    preflight_cuda()
    attn = _resolve_attn_backend()
    _sync_trellis_attn_modules(attn)

    photos_dir = _require_nobg_dir(task_dir)
    paths = pick_input_images(photos_dir, task_dir=task_dir)
    images = [Image.open(p).convert("RGBA") for p in paths]
    n_views = len(images)
    mode = multi_image_mode()

    # Voxel generator defaults (ComfyUI Mesh With Voxel Advanced Generator)
    ss_defaults = {"steps": 30, "guidance_strength": 7.5, "guidance_rescale": 0.2, "rescale_t": 1.0}
    shape_defaults = {"steps": 30, "guidance_strength": 7.5, "guidance_rescale": 0.1, "rescale_t": 2.0}
    # Mesh refiner defaults (ComfyUI Mesh Refiner node)
    shape_refine_defaults = {"steps": 12, "guidance_strength": 6.5, "guidance_rescale": 0.05, "rescale_t": 4.0}
    tex_defaults = {"steps": 12, "guidance_strength": 3.0, "guidance_rescale": 0.2, "rescale_t": 3.0}

    ss_params = _sampler_params("SS", ss_defaults)
    shape_params = _sampler_params("SHAPE", shape_defaults)
    shape_refine_params = _sampler_params("SHAPE_REFINE", shape_refine_defaults)
    tex_params = _tex_params_with_downsampling(tex_defaults)

    pipeline_type = _pipeline_type_resolved()
    max_tokens = int(os.getenv("TRELLIS2_MAX_NUM_TOKENS", "999999"))
    seed = int(os.getenv("TRELLIS2_SEED", "42"))
    gen_tex_slat = os.getenv("TRELLIS2_GENERATE_TEXTURE_SLAT", "1").lower() in ("1", "true", "yes")
    ss_res = _ss_resolution(pipeline_type)

    pipe = get_pipeline()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    _progress(
        f"stage2 voxel generator pipeline_type={pipeline_type} ss_res={ss_res} "
        f"views={n_views} multi_mode={mode if n_views > 1 else 'single'}"
    )
    torch.manual_seed(seed)

    with torch.no_grad():
        # Multi-view: cond batch=N; num_samples остаётся 1 (не путать с MAX_VIEWS).
        cond_512 = _prepare_multi_cond(pipe.get_cond(images, 512))
        cond_1024 = (
            _prepare_multi_cond(pipe.get_cond(images, 1024)) if pipeline_type != "512" else None
        )

        with inject_sampler_multi_image(pipe.sparse_structure_sampler, n_views, mode=mode):
            coords = pipe.sample_sparse_structure(cond_512, ss_res, 1, ss_params)

        with inject_sampler_multi_image(pipe.shape_slat_sampler, n_views, mode=mode):
            shape_slat, res = _sample_shape_cascade(
                pipe, pipeline_type, cond_512, cond_1024, coords, shape_params, max_tokens
            )

        _progress("stage3 mesh: decode shape + fill holes (Comfy node 1)")
        meshes, subs = pipe.decode_shape_slat(shape_slat, res)
        if meshes:
            fill_mesh_holes(meshes[0])

        _free_cuda_memory()

        if os.getenv("TRELLIS2_REFINE_SHAPE", "1").lower() in ("1", "true", "yes"):
            _progress("stage5 mesh refiner: shape slat")
            with inject_sampler_multi_image(pipe.shape_slat_sampler, n_views, mode=mode):
                shape_slat, res = _sample_shape_cascade(
                    pipe, pipeline_type, cond_512, cond_1024, coords, shape_refine_params, max_tokens
                )
            meshes, subs = pipe.decode_shape_slat(shape_slat, res)
            if meshes:
                _progress("fill holes after refiner (Comfy node 2)")
                fill_mesh_holes(meshes[0])
            _free_cuda_memory()

        tex_slat = None
        if gen_tex_slat:
            _progress("stage6 texturing: texture slat (Mesh Refiner tex)")
            cond_tex = cond_1024 if cond_1024 is not None else cond_512
            tex_key = "tex_slat_flow_model_1024" if pipeline_type != "512" else "tex_slat_flow_model_512"
            with inject_sampler_multi_image(pipe.tex_slat_sampler, n_views, mode=mode):
                tex_slat = pipe.sample_tex_slat(cond_tex, pipe.models[tex_key], shape_slat, tex_params)
            _free_cuda_memory()

        _trim_vram_before_decode(pipe)
        _progress("decode latent → MeshWithVoxel (VRAM trimmed)")
        if tex_slat is not None:
            out_meshes = pipe.decode_latent(shape_slat, tex_slat, res)
        else:
            out_meshes = meshes

        # Зашивка дыр после decode (мелкие/средние boundary loops).
        if out_meshes:
            hole_iters = max(3, int(os.getenv("TRELLIS2_HOLE_ITERATIONS", "5")))
            filled = fill_mesh_holes(out_meshes[0], iterations=hole_iters)
            _progress(f"post-decode fill_holes passes={filled} views={n_views}")

    if not out_meshes:
        raise RuntimeError("staged pipeline: пустой результат")

    mesh = out_meshes[0]
    _release_vram_before_export(pipe)
    _free_cuda_memory()
    ops_meta = apply_pre_export_ops(mesh)
    _progress(
        f"mesh ops textured_voxel={ops_meta.get('textured_voxel')} "
        f"reorient={ops_meta.get('reorient_deg')} "
        f"holes={ops_meta.get('holes_filled_passes')}"
    )
    _mesh_to_cpu(mesh)
    _free_cuda_memory()
    _progress("export GLB (cumesh to_glb из env)")
    _export_trellis2_mesh(mesh, output, task_dir=task_dir)
    release_pipeline()
    return output

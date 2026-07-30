"""ComfyUI-стиль: shape → mesh optimize → texture (отдельные этапы, меньше OOM)."""

from __future__ import annotations

import os
from pathlib import Path

from trellis_runtime import (
    _export_trellis2_mesh,
    _free_cuda_memory,
    _mesh_to_cpu,
    _pick_front_image,
    _pipeline_type_resolved,
    _progress,
    _release_vram_before_export,
    _require_nobg_dir,
    _resolve_attn_backend,
    _sampler_params,
    _sync_trellis_attn_modules,
    get_pipeline,
    preflight_cuda,
    release_pipeline,
)


def _ss_resolution(pipeline_type: str) -> int:
    override = (os.getenv("TRELLIS2_SS_RESOLUTION") or "").strip()
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    return {"512": 32, "1024": 64, "1024_cascade": 32, "1536_cascade": 32}.get(pipeline_type, 32)


def _fill_mesh_holes(mesh) -> None:
    if os.getenv("TRELLIS2_FILL_HOLES", "1").lower() not in ("1", "true", "yes"):
        return
    if not hasattr(mesh, "fill_holes"):
        return
    iters = max(1, int(os.getenv("TRELLIS2_HOLE_ITERATIONS", "1")))
    algo = (os.getenv("TRELLIS2_HOLE_FILL_ALGORITHM") or "flood_fill").strip().lower()
    for _ in range(iters):
        try:
            if algo != "flood_fill" and hasattr(mesh, "fill_holes"):
                mesh.fill_holes()
            else:
                mesh.fill_holes()
        except Exception:  # noqa: BLE001
            break


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
    """rmbg снаружи → voxel/shape → holes → refiner shape → texture → export GLB."""
    import torch
    from PIL import Image

    preflight_cuda()
    attn = _resolve_attn_backend()
    _sync_trellis_attn_modules(attn)

    photos_dir = _require_nobg_dir(task_dir)
    front = _pick_front_image(photos_dir)
    image = Image.open(front).convert("RGBA")

    ss_defaults = {"steps": 30, "guidance_strength": 7.5, "guidance_rescale": 0.2, "rescale_t": 1.0}
    shape_defaults = {"steps": 30, "guidance_strength": 7.5, "guidance_rescale": 0.1, "rescale_t": 2.0}
    shape_refine_defaults = {"steps": 12, "guidance_strength": 6.5, "guidance_rescale": 0.05, "rescale_t": 4.0}
    tex_defaults = {"steps": 20, "guidance_strength": 5.0, "guidance_rescale": 0.2, "rescale_t": 4.0}

    ss_params = _sampler_params("SS", ss_defaults)
    shape_params = _sampler_params("SHAPE", shape_defaults)
    shape_refine_params = _sampler_params("SHAPE_REFINE", shape_refine_defaults)
    tex_params = _sampler_params("TEX", tex_defaults)

    pipeline_type = _pipeline_type_resolved()
    max_tokens = int(os.getenv("TRELLIS2_MAX_NUM_TOKENS", "9999"))
    max_views = int(os.getenv("TRELLIS2_MAX_VIEWS", "4"))
    seed = int(os.getenv("TRELLIS2_SEED", "42"))

    pipe = get_pipeline()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    _progress(f"stage2 voxel generator pipeline_type={pipeline_type}")
    torch.manual_seed(seed)

    with torch.no_grad():
        cond_512 = pipe.get_cond([image], 512)
        cond_1024 = pipe.get_cond([image], 1024) if pipeline_type != "512" else None

        coords = pipe.sample_sparse_structure(
            cond_512, _ss_resolution(pipeline_type), max_views, ss_params
        )
        shape_slat, res = _sample_shape_cascade(
            pipe, pipeline_type, cond_512, cond_1024, coords, shape_params, max_tokens
        )

        _progress("stage3 mesh: decode shape + fill holes")
        meshes, subs = pipe.decode_shape_slat(shape_slat, res)
        if meshes:
            _fill_mesh_holes(meshes[0])

        _free_cuda_memory()

        if os.getenv("TRELLIS2_REFINE_SHAPE", "1").lower() in ("1", "true", "yes"):
            _progress("stage5 mesh refiner: shape slat (refine params)")
            shape_slat, res = _sample_shape_cascade(
                pipe, pipeline_type, cond_512, cond_1024, coords, shape_refine_params, max_tokens
            )
            meshes, subs = pipe.decode_shape_slat(shape_slat, res)
            if meshes:
                _fill_mesh_holes(meshes[0])
            _free_cuda_memory()

        _progress("stage6 texturing: texture slat")
        cond_tex = cond_1024 if cond_1024 is not None else cond_512
        tex_key = "tex_slat_flow_model_1024" if pipeline_type != "512" else "tex_slat_flow_model_512"
        tex_slat = pipe.sample_tex_slat(cond_tex, pipe.models[tex_key], shape_slat, tex_params)

        _progress("decode latent → MeshWithVoxel")
        out_meshes = pipe.decode_latent(shape_slat, tex_slat, res)

    if not out_meshes:
        raise RuntimeError("staged pipeline: пустой результат")

    mesh = out_meshes[0]
    _mesh_to_cpu(mesh)
    _release_vram_before_export(pipe)
    _free_cuda_memory()
    _progress("export GLB (remesh/simplify/decimation из env)")
    _export_trellis2_mesh(mesh, output, task_dir=task_dir)
    release_pipeline()
    return output

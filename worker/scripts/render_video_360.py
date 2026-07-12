"""Video 360 §17: рендер вращения модели → MP4 (Blender / Open3D / ffmpeg)."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _render_open3d(glb: Path, frames_dir: Path, n_frames: int) -> bool:
    try:
        import numpy as np
        import open3d as o3d
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        print(f"[video_360] open3d unavailable: {exc}")
        return False
    try:
        mesh = o3d.io.read_triangle_mesh(str(glb))
        if mesh.is_empty():
            return False
        mesh.compute_vertex_normals()
        frames_dir.mkdir(parents=True, exist_ok=True)
        vis = o3d.visualization.rendering.OffscreenRenderer(640, 480)
        mat = o3d.visualization.rendering.MaterialRecord()
        mat.shader = "defaultLit"
        vis.scene.add_geometry("model", mesh, mat)
        bounds = mesh.get_axis_aligned_bounding_box()
        center = bounds.get_center()
        extent = max(bounds.get_extent().max(), 1e-3)
        for i in range(n_frames):
            yaw = 2 * math.pi * i / n_frames
            eye = center + np.array([math.cos(yaw) * extent * 2.2, extent * 0.6, math.sin(yaw) * extent * 2.2])
            vis.setup_camera(60.0, center, eye, [0, 1, 0])
            img = vis.render_to_image()
            path = frames_dir / f"frame_{i:03d}.png"
            o3d.io.write_image(str(path), img)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[video_360] open3d render failed: {exc}")
        return False


def _render_blender(glb: Path, out_mp4: Path, n_frames: int) -> bool:
    blender = os.getenv("BLENDER_BIN") or shutil.which("blender")
    if not blender:
        return False
    script = f"""
import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r'{glb.as_posix()}')
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = {n_frames}
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.filepath = r'{out_mp4.as_posix()}'
# simple orbit
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam)
scene.camera = cam
for i, obj in enumerate(bpy.context.scene.objects):
    if obj.type == 'MESH':
        obj.keyframe_insert(data_path='rotation_euler', frame=1)
        obj.rotation_euler[2] = math.radians(360)
        obj.keyframe_insert(data_path='rotation_euler', frame={n_frames})
bpy.ops.render.render(animation=True)
"""
    py = out_mp4.parent / "_blender_360.py"
    py.write_text(script, encoding="utf-8")
    try:
        r = subprocess.run(
            [blender, "-b", "-P", str(py)],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        return r.returncode == 0 and out_mp4.exists()
    except Exception as exc:  # noqa: BLE001
        print(f"[video_360] blender failed: {exc}")
        return False
    finally:
        py.unlink(missing_ok=True)


def _ffmpeg_from_frames(frames_dir: Path, out_mp4: Path, fps: int = 24) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    pattern = str(frames_dir / "frame_%03d.png")
    r = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        print(f"[video_360] ffmpeg: {r.stderr[-400:]}")
    return r.returncode == 0 and out_mp4.exists()


def main(task_dir: str) -> None:
    root = Path(task_dir)
    glb = root / "model.glb"
    if not glb.exists():
        raise SystemExit("model.glb missing")
    n = int(os.getenv("VIDEO_360_FRAMES", "36"))
    out = root / "video_360.mp4"
    frames = root / "video_360_frames"

    if _render_blender(glb, out, n):
        print(f"[video_360] blender → {out}")
    elif _render_open3d(glb, frames, n) and _ffmpeg_from_frames(frames, out):
        print(f"[video_360] open3d+ffmpeg → {out}")
    else:
        raise SystemExit("video_360 render failed (need blender or open3d+ffmpeg)")

    manifest = {
        "type": "video_360",
        "fps": 24,
        "frames": n,
        "file": "video_360.mp4",
        "source_glb": "model.glb",
    }
    (root / "video_360.json").write_text(json.dumps(manifest), encoding="utf-8")
    print(f"[video_360] done {out.stat().st_size} bytes")


if __name__ == "__main__":
    main(sys.argv[1])

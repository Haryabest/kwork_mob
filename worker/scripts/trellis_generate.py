"""Генерация 3D через TRELLIS (12 multi-view фото)."""

import sys
from pathlib import Path


def main(task_dir: str):
    """Генерация базовой геометрии и текстуры."""
    output = Path(task_dir) / "raw_mesh.glb"
    # TODO: вызов TRELLIS pipeline
    output.touch()
    print(f"[trellis_generate] {task_dir}")


if __name__ == "__main__":
    main(sys.argv[1])

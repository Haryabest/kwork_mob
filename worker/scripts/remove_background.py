"""Двухступенчатое удаление фона: DeepLabV3+ → SAM fallback."""

import sys
from pathlib import Path


def main(task_dir: str):
    """Обработка 12 изображений в task_dir/photos/."""
    photos = Path(task_dir) / "photos"
    photos.mkdir(exist_ok=True)
    # TODO: DeepLabV3+ (confidence >= 0.85) → SAM fallback
    print(f"[remove_background] Обработка {task_dir}")


if __name__ == "__main__":
    main(sys.argv[1])

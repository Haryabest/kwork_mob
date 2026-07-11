"""Финальная валидация GLB: размер, PBR-карты, watermark HMAC."""

import sys


def main(task_dir: str):
    # TODO: проверка размера ≤15 МБ, наличие roughness/metallic/normal
    print(f"[validate_glb] {task_dir}")


if __name__ == "__main__":
    main(sys.argv[1])

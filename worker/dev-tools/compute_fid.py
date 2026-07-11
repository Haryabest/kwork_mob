"""
FID-метрика — ТОЛЬКО для локального dev-тестирования.
НЕ включается в Docker-образ production-воркера.
"""

import sys


def main(reference_dir: str, generated_dir: str):
    # TODO: вычисление FID (опционально, dev only)
    print(f"[compute_fid] dev-only: {reference_dir} vs {generated_dir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

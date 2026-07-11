"""Устойчивые водяные знаки DWT-DCT — ТОЛЬКО diffuse-карта + HMAC в extras."""

import hashlib
import hmac
import os
import sys


def apply_dwt_watermark(diffuse_path: str, payload: str, strength: float = 0.01) -> None:
    """DWT-DCT watermark только в альбедо."""
    # TODO: PyWavelets + scipy DCT
    pass


def generate_hmac(model_uuid: str, secret: str) -> str:
    return hmac.new(secret.encode(), model_uuid.encode(), hashlib.sha256).hexdigest()


def main(task_dir: str):
    secret = os.getenv("WATERMARK_HMAC_SECRET", "dev-secret")
    # TODO: применить DWT только к diffuse, записать HMAC в GLB extras
    
    print(f"[apply_watermark] {task_dir}")


if __name__ == "__main__":
    main(sys.argv[1])

# GPU-воркер production (§5): TRELLIS + SAM + постобработка
# FID (compute_fid.py) НЕ включается в production-образ
#
# Сборка production (рекомендуется):
#   docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 -t kwork-worker .
# Dev без TRELLIS (только для локальной отладки оркестрации):
#   docker build --build-arg INSTALL_TRELLIS=0 -t kwork-worker:dev .
#   WORKER_PIPELINE_MODE=stub
#
# Runtime E2E бюджет: ≤3 мин ПК / ≤5 мин облако (логируется worker_agent)

FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

ARG INSTALL_TRELLIS=0
ARG DOWNLOAD_WEIGHTS=1
ARG INSTALL_FLASH_ATTN=0
ARG TRELLIS_VERSION=2
ARG TRELLIS_REPO=https://github.com/microsoft/TRELLIS.2.git
ARG INSTALL_SAM=1
ARG INSTALL_BLENDER=1
ARG INSTALL_INSTANT_MESHES=1
ARG BLENDER_VERSION=4.2.3

RUN apt-get update && apt-get install -y \
    python3.10 python3-pip libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
    libxrender-dev libgomp1 git wget unzip ffmpeg curl ca-certificates xz-utils \
    nodejs npm postgresql-client cmake g++ libx11-dev libxi-dev libgl1-mesa-dev && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g @gltf-transform/cli || true

# Blender LTS headless (§6.4 PBR bake, §6 video_360 / USDZ)
RUN if [ "$INSTALL_BLENDER" = "1" ]; then \
      mkdir -p /opt/blender && \
      wget -q -O /tmp/blender.tar.xz \
        "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" && \
      tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 && \
      ln -sf /opt/blender/blender /usr/local/bin/blender && \
      rm -f /tmp/blender.tar.xz && \
      blender --version; \
    fi

# Instant Meshes → /usr/local/bin/instant_meshes (§5 / §6.3)
COPY scripts/install_instant_meshes.sh /tmp/install_instant_meshes.sh
RUN if [ "$INSTALL_INSTANT_MESHES" = "1" ]; then \
      chmod +x /tmp/install_instant_meshes.sh && \
      bash /tmp/install_instant_meshes.sh /usr/local/bin/instant_meshes || \
        echo "[warn] Instant Meshes install failed — Open3D fallback"; \
    fi && rm -f /tmp/install_instant_meshes.sh

WORKDIR /app

COPY requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=1200 \
    PIP_RETRIES=15
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir --timeout 1200 --retries 15 \
      torch torchvision --index-url https://download.pytorch.org/whl/cu128 && \
    pip3 install --no-cache-dir --timeout 1200 --retries 15 -r requirements.txt

# Segment Anything (SAM) weights
RUN mkdir -p /app/weights/sam && \
    if [ "$INSTALL_SAM" = "1" ]; then \
      pip3 install --no-cache-dir 'git+https://github.com/facebookresearch/segment-anything.git' || true; \
      wget -q -O /app/weights/sam/sam_vit_b.pth \
        https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth || true; \
    fi

COPY worker_agent.py /app/worker_agent.py
COPY scripts/ /app/scripts/
COPY entrypoint.sh /usr/local/bin/worker_entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/worker_entrypoint.sh && \
    chmod +x /usr/local/bin/worker_entrypoint.sh

RUN mkdir -p /var/log/worker /tmp/worker

# TRELLIS.2: clone отдельно — кэш слоя при повторной сборке
RUN if [ "$INSTALL_TRELLIS" = "1" ]; then \
      git clone --depth 1 --recursive "${TRELLIS_REPO}" /app/trellis && \
      test -f /app/trellis/trellis2/__init__.py; \
    fi

# setup.sh + xformers (без flash-attn по умолчанию) + веса (§5.1)
COPY scripts/install_trellis2.sh /tmp/install_trellis2.sh
RUN if [ "$INSTALL_TRELLIS" = "1" ]; then \
      chmod +x /tmp/install_trellis2.sh && \
      if [ "$TRELLIS_VERSION" = "2" ]; then \
        DOWNLOAD_WEIGHTS="${DOWNLOAD_WEIGHTS}" \
        INSTALL_FLASH_ATTN="${INSTALL_FLASH_ATTN}" \
        TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B \
        MAX_JOBS=2 \
          bash /tmp/install_trellis2.sh /app/trellis; \
      else \
        pip3 install --no-cache-dir -r /app/trellis/requirements.txt && \
        pip3 install --no-cache-dir -e /app/trellis; \
      fi && \
      rm -f /tmp/install_trellis2.sh; \
    fi

# Production: trellis только на облачном GPU (Intelion). Локально — stub.
ENV PYTHONUNBUFFERED=1 \
    WORKER_PIPELINE_MODE=stub \
    TRELLIS_VERSION=2 \
    TRELLIS_ROOT=/app/trellis \
    TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B \
    TRELLIS2_PIPELINE_TYPE=512 \
    TRELLIS2_LOW_VRAM=1 \
    TRELLIS2_DECIMATION=300000 \
    TRELLIS2_TEXTURE_SIZE=2048 \
    TRELLIS_ALLOW_STUB_FALLBACK=0 \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    ATTN_BACKEND=xformers \
    SAM_CHECKPOINT=/app/weights/sam/sam_vit_b.pth \
    SAM_MODEL_TYPE=vit_b \
    WORKER_E2E_BUDGET_SEC=300 \
    WORKER_E2E_BUDGET_LOCAL_SEC=180 \
    WORKER_SUBPROCESS_STREAM=1 \
    WORKER_TASK_DRAIN_TIMEOUT_SEC=3600 \
    PYTHONPATH=/app/scripts:/app/trellis \
    ORCHESTRATOR_WS_URL=ws://orchestrator:8000/ws/worker \
    ORCHESTRATOR_WS_FALLBACK_URL= \
    BLENDER_BIN=/usr/local/bin/blender \
    INSTANT_MESHES_BIN=/usr/local/bin/instant_meshes \
    RETOPO_ENGINE=instant_meshes \
    RETOPO_TARGET_FACES=150000

ENTRYPOINT ["/usr/local/bin/worker_entrypoint.sh"]
CMD ["python3", "/app/worker_agent.py"]

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

ARG INSTALL_TRELLIS=1
ARG DOWNLOAD_WEIGHTS=1
ARG TRELLIS_REPO=https://github.com/microsoft/TRELLIS.git
ARG INSTALL_SAM=1

RUN apt-get update && apt-get install -y \
    python3.10 python3-pip libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
    libxrender-dev libgomp1 git wget unzip ffmpeg curl ca-certificates \
    nodejs npm postgresql-client && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g @gltf-transform/cli || true

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Segment Anything (SAM) weights
RUN mkdir -p /app/weights/sam && \
    if [ "$INSTALL_SAM" = "1" ]; then \
      pip3 install --no-cache-dir 'git+https://github.com/facebookresearch/segment-anything.git' || true; \
      wget -q -O /app/weights/sam/sam_vit_b.pth \
        https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth || true; \
    fi

COPY worker_agent.py /usr/local/bin/worker_agent.py
COPY scripts/ /app/scripts/
COPY entrypoint.sh /usr/local/bin/worker_entrypoint.sh
RUN chmod +x /usr/local/bin/worker_entrypoint.sh

RUN mkdir -p /app/trellis /app/trellis/weights /var/log/worker /tmp/worker

# TRELLIS + веса в образ
RUN if [ "$INSTALL_TRELLIS" = "1" ]; then \
      git clone --depth 1 "${TRELLIS_REPO}" /app/trellis && \
      if [ -f /app/trellis/requirements.txt ]; then \
        pip3 install --no-cache-dir -r /app/trellis/requirements.txt || true; \
      fi && \
      if [ -f /app/trellis/setup.py ] || [ -f /app/trellis/pyproject.toml ]; then \
        pip3 install --no-cache-dir -e /app/trellis || true; \
      fi; \
    fi

RUN if [ "$DOWNLOAD_WEIGHTS" = "1" ] && [ -f /app/trellis/scripts/download_weights.sh ]; then \
      bash /app/trellis/scripts/download_weights.sh /app/trellis/weights || true; \
    elif [ "$DOWNLOAD_WEIGHTS" = "1" ] && [ -f /app/trellis/download_weights.py ]; then \
      python3 /app/trellis/download_weights.py --out /app/trellis/weights || true; \
    fi

# Production default: trellis (не stub)
ENV PYTHONUNBUFFERED=1 \
    WORKER_PIPELINE_MODE=trellis \
    TRELLIS_ROOT=/app/trellis \
    TRELLIS_WEIGHTS=/app/trellis/weights \
    TRELLIS_ALLOW_STUB_FALLBACK=0 \
    SAM_CHECKPOINT=/app/weights/sam/sam_vit_b.pth \
    SAM_MODEL_TYPE=vit_b \
    WORKER_E2E_BUDGET_SEC=300 \
    WORKER_E2E_BUDGET_LOCAL_SEC=180 \
    PYTHONPATH=/app/scripts:/app/trellis \
    ORCHESTRATOR_WS_URL=ws://orchestrator:8000/ws/worker \
    ORCHESTRATOR_WS_FALLBACK_URL=

ENTRYPOINT ["/usr/local/bin/worker_entrypoint.sh"]
CMD ["python3", "/usr/local/bin/worker_agent.py"]

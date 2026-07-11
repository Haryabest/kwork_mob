# GPU-воркер: TRELLIS + постобработка
# FID (compute_fid.py) НЕ включается в production-образ

FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.10 python3-pip libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
    libxrender-dev libgomp1 git wget unzip ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY worker_agent.py /usr/local/bin/worker_agent.py
COPY scripts/ /app/scripts/

# TRELLIS монтируется как volume или клонируется при сборке
RUN mkdir -p /app/trellis /var/log/worker

ENV PYTHONUNBUFFERED=1

CMD ["python3", "/usr/local/bin/worker_agent.py"]

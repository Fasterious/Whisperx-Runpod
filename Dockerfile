# WhisperX RunPod Serverless Docker Image
# Optimized for transcription with speaker diarization

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Set Python to not buffer output (useful for logs)
ENV PYTHONUNBUFFERED=1

# Set CUDA environment
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="${CUDA_HOME}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-venv \
    ffmpeg \
    git \
    wget \
    curl \
    ca-certificates \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Upgrade pip and install SSL certificates
RUN pip install --upgrade pip setuptools wheel certifi

# Configure pip to trust PyTorch hosts
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org download.pytorch.org"

# Create working directory
WORKDIR /app

# Install WhisperX first - let it install its own compatible dependencies
RUN pip install whisperx runpod requests

# Reinstall torch and torchaudio with CUDA 12.1 support (override CPU versions)
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall

# Copy application files
COPY handler.py /app/handler.py
COPY download_models.py /app/download_models.py

# Set default model (can be overridden at runtime)
ENV WHISPER_MODEL=large-v2

# Pre-download models during build for faster cold start
# HF_TOKEN is only used during build (ARG) and NOT stored in the image (security)
ARG HF_TOKEN=""
# Disable xet downloader (causes issues in Docker) and use classic HTTP
ENV HF_HUB_ENABLE_HF_TRANSFER=0
ENV HF_HUB_DISABLE_XET=1
RUN HF_TOKEN=${HF_TOKEN} python download_models.py

# HF_TOKEN will be provided at runtime via RunPod environment variables
ENV HF_TOKEN=""

# Expose port (optional, for health checks)
EXPOSE 8000

# Run the handler
CMD ["python", "-u", "handler.py"]

# MeetScript API Dockerfile
FROM python:3.12-slim

WORKDIR /app

# ── 使用清华镜像源加速 apt ────────────────────────────────────────
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main" > /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main" >> /etc/apt/sources.list \
    && echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security/ trixie-security main" >> /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources

# System dependencies for ffmpeg and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (清华 pypi 镜像)
COPY pyproject.toml .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir .

# Application
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 meetscript && chown -R meetscript:meetscript /app
USER meetscript

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

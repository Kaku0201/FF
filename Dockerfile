# Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libffi-dev \
        libssl-dev \
        tzdata && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove \
        build-essential python3-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]

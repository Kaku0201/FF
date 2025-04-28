# Dockerfile

FROM python:3.11-slim

# 1) 작업 디렉토리
WORKDIR /app

# 2) 의존성 복사 및 OS-level 빌드 도구 설치
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \       # 컴파일러(gcc 등)
      python3-dev \           # Python 헤더
      libffi-dev \            # aiohttp 같은 패키지용
      libssl-dev \            # cryptography(OpenSSL)용
      tzdata && \             # 시간대 파일
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove \
      build-essential python3-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# 3) 앱 코드 복사
COPY . .

# 4) 실행 커맨드
CMD ["python", "main.py"]

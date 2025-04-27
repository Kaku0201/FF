# Dockerfile
FROM python:3.11-slim
WORKDIR /app

# 의존성 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 복사
COPY . .

# 봇 실행
CMD ["python", "main.py"]
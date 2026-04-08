FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir playwright requests
RUN playwright install --with-deps chromium

COPY browser-agent /app/browser-agent
COPY data /app/data

ENV BACKEND_URL=http://backend:3000 \
    HEADLESS=true

CMD ["python", "/app/browser-agent/main.py"]


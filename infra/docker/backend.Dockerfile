FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

EXPOSE 3000

CMD ["bentoml", "serve", "backend.main:svc", "--host", "0.0.0.0", "--port", "3000"]


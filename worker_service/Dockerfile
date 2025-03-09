FROM python:3.10-slim

# Обновляем apt и устанавливаем необходимые библиотеки
RUN apt-get update && \
    apt-get install -y libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt



COPY worker/ /app


# Устанавливаем переменную окружения
ENV PROJECT_ROOT=/app

# Предположим, что точка входа - celery worker
# Или вы можете создать worker_main.py, где прописано celery -A ...
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--pool=solo"]

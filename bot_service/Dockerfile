FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ /app

# Устанавливаем переменную окружения
ENV PROJECT_ROOT=/app


# Предположим, бот запускается telegram_bot.py
CMD ["python", "telegram_bot.py"]

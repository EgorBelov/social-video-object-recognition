# Используем официальный образ Python
FROM python:3.12

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы зависимостей в контейнер
COPY requirements.txt /app/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . /app/

# Устанавливаем переменную окружения для работы с FastAPI
ENV PYTHONUNBUFFERED 1

# Открываем порт, на котором будет работать приложение
EXPOSE 8000

# Запускаем FastAPI сервер через Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

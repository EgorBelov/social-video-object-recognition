import hashlib
import os
import asyncio
from typing import Union
import httpx
from dotenv import load_dotenv
from telegram import Document, Update, Video
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Создаем асинхронное приложение телеграм-бота
application = Application.builder().token(API_TOKEN).build()


# Команда /start
async def start(update: Update, context):
    if update.message is None:
        return  # или raise или что-то, если ситуация невозможна
    await update.message.reply_text(
        "Привет! Я могу помочь найти видео с распознанными объектами.\n"
        "Отправь мне видео, чтобы я мог добавить его в систему, "
        "или введи /search <object>, чтобы найти готовые видео."
    )


# Обработка видео (MessageHandler)
async def handle_video(update: Update, context):
    """
    1) Сохранить файл (в папку `videos/`).
    2) Дернуть API: POST /videos -> вернёт video_id
    3) Дернуть API: POST /videos/{video_id}/process -> поставит задачу воркеру
    4) Сказать пользователю, что идёт обработка.
    """
    # Сначала сохраняем сообщение в локальную переменную
    message = update.message
    if message is None:
        return

    # Определяем переменную video_file как объединение типов Video и Document
    video_file: Union[Video, Document]

    if message.video is not None:
        video_file = message.video
    elif message.document is not None and message.document.mime_type is not None and message.document.mime_type.startswith('video/'):
        video_file = message.document
    else:
        await message.reply_text("Пожалуйста, отправьте видеофайл!")
        return

    file = await video_file.get_file()

    # os.makedirs("videos", exist_ok=True)
    # local_video_path = f"videos/{video_file.file_id}.mp4"
    # await file.download_to_drive(local_video_path)

    # Получаем PROJECT_ROOT из переменной окружения
    PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.getcwd())
    VIDEOS_DIR = os.path.join(PROJECT_ROOT, "videos")
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    local_video_path = os.path.join(VIDEOS_DIR, f"{video_file.file_id}.mp4")
    await file.download_to_drive(local_video_path)
    if update.message is None:
        return  # или raise или что-то, если ситуация невозможна
    await update.message.reply_text("Видео получено, создаю запись в системе...")

    sha256_hash = hashlib.sha256()
    with open(local_video_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    print(f"Video hash: {sha256_hash.hexdigest()}")  # Логирование хэша

    # Создаём запись о видео (асинхронно вызываем API)
    payload = {
        "title": f"TGVideo_{video_file.file_id}",
        "description": "Uploaded from Telegram",
        "url": local_video_path,     # Путь, который Worker потом найдёт
        "platform": "Telegram"
    }
    print(payload)
    try:
        async with httpx.AsyncClient() as client:
            # resp = await client.post(f"{API_URL}/videos/", json=payload)
            resp = await client.post(
                f"{API_URL}/videos/?title={payload['title']}&description={payload['description']}&url={payload['url']}&platform=Telegram&hash={sha256_hash.hexdigest()}")
            resp.raise_for_status()
            video_data = resp.json()  # Предположим, {"id":123,"title":"...","...":...}
            video_id = video_data["id"]
    except httpx.HTTPError as e:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text(f"Ошибка при создании записи о видео: {e}")
        return

    await update.message.reply_text(
        f"Запись о видео успешно создана (ID={video_id}). Отправляю задачу на обработку..."
    )

    # Ставим задачу на обработку
    try:
        async with httpx.AsyncClient() as client:
            resp_process = await client.post(f"{API_URL}/videos/{video_id}/process")
            resp_process.raise_for_status()
    except httpx.HTTPError as e:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text(f"Ошибка при постановке задачи в очередь: {e}")
        return
    if update.message is None:
        return  # или raise или что-то, если ситуация невозможна
    await update.message.reply_text(
        "Задача на обработку отправлена! "
        "Подождите, пока воркер обработает видео."
    )


# Команда /search
async def search_videos(update: Update, context):
    """
    /search <object> -> вызывает GET /search_by_object?object_name=<object>
    получает список видео + инфу о распознанных объектах,
    пытается отдать обработанные файлы в чат.
    """
    query = ' '.join(context.args)
    if not query:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text("Пожалуйста, введите запрос для поиска. Пример: /search car")
        return

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_URL}/search_by_object/",
                params={"object_name": query},
                timeout=30.0
            )
            if resp.status_code == 404:
                if update.message is None:
                    return  # или raise или что-то, если ситуация невозможна
                await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
                return
            resp.raise_for_status()
            results = resp.json()  # Предположим, список видео
    except httpx.HTTPError as e:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text(f"Ошибка при запросе к API: {e}")
        return

    if not results:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
        return

    # results может выглядеть так:
    # [
    #   {
    #     "title": "Video Title",
    #     "description": "Video desc",
    #     "url": "videos/...mp4",
    #     "objects": [
    #       {"label": "car", "count": 3},
    #       {"label": "person", "count": 2}
    #     ]
    #   }, ...
    # ]
    # Получаем PROJECT_ROOT из переменной окружения
    PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.getcwd())
    for video_item in results:
        title = video_item["title"]
        url = video_item["url"]
        objs = video_item.get("objects", [])
        obj_str = ", ".join([f"{o['label']}({o['count']})" for o in objs]) if objs else "нет объектов"

        message_text = f"Нашёл видео: {title}\nОбъекты: {obj_str}"
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text(message_text)
        # Строим абсолютный путь к исходному видео
        abs_video_path = os.path.join(PROJECT_ROOT, url)
        # Формируем путь к обработанному файлу, заменяя "videos" на "processed_videos"
        abs_processed_path = abs_video_path.replace(os.path.join(PROJECT_ROOT, "videos"), os.path.join(PROJECT_ROOT, "processed_videos"))
        print("Search: processed path:", abs_processed_path)
        if os.path.exists(abs_processed_path):
            try:
                with open(abs_processed_path, 'rb') as vid_file:
                    if update.message is None:
                        return  # или raise или что-то, если ситуация невозможна
                    await update.message.reply_video(video=vid_file)
            except Exception as e:
                if update.message is None:
                    return  # или raise или что-то, если ситуация невозможна
                await update.message.reply_text(f"Ошибка при отправке видео: {e}")
        else:
            await update.message.reply_text(
                "Обработанное видео не найдено или не готово. Возможно, обработка ещё не завершена."
            )
        # # Пытаемся найти обработанный файл локально (или на общем шаре)
        # processed_path = url.replace("videos/", "../../processed_videos/")

        # if os.path.exists(processed_path):
        #     try:
        #         with open(processed_path, 'rb') as vid_file:
        #             await update.message.reply_video(video=vid_file)
        #     except Exception as e:
        #         await update.message.reply_text(f"Ошибка при отправке видео: {e}")
        # else:
        #     await update.message.reply_text(
        #         "Обработанное видео не найдено или не готово. "
        #         "Возможно, обработка ещё не завершена."
        #     )


# ----- команда /status <video_id> -----
async def status_video(update: Update, context):
    """
    Пользователь вводит: /status 123
    Бот дергает API: GET /videos/123
    Если запись существует и обработанное видео доступно, отправляет его.
    """
    if not context.args:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text("Пожалуйста, укажите ID видео. Пример: /status 12")
        return
    video_id = context.args[0]
    if not video_id.isdigit():
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text("ID видео должно быть числом. Пример: /status 12")
        return

    # Шлём запрос к API, чтобы узнать, что с видео
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_URL}/videos/{video_id}")
            resp.raise_for_status()
            data = resp.json()  # например, {"id":123,"title":"...","url":"videos/xxx.mp4","hash":"abcd1234", ...}
    except httpx.HTTPError as e:
        if hasattr(e, 'response'):
            if e.response and e.response.status_code == 404:
                if update.message is None:
                    return  # или raise или что-то, если ситуация невозможна
                await update.message.reply_text(f"Видео с ID={video_id} не найдено.")
                return
            if update.message is None:
                return  # или raise или что-то, если ситуация невозможна
            await update.message.reply_text(f"Ошибка при запросе статуса видео: {str(e)}")
            return

    # Проверяем, есть ли у нас локально processed_videos/...
    video_path = data.get("url")
    if not video_path:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text("У видео нет поля url, не могу найти файл.")
        return
    PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.getcwd())
    abs_video_path = os.path.join(PROJECT_ROOT, video_path)
    abs_processed_path = abs_video_path.replace(os.path.join(PROJECT_ROOT, "videos"), os.path.join(PROJECT_ROOT, "processed_videos"))
    print("Status: processed path:", abs_processed_path)
    if os.path.exists(abs_processed_path):
        try:
            with open(abs_processed_path, 'rb') as vid_file:
                if update.message is None:
                    return  # или raise или что-то, если ситуация невозможна
                await update.message.reply_video(video=vid_file)
        except Exception as e:
            if update.message is None:
                return  # или raise или что-то, если ситуация невозможна
            await update.message.reply_text(f"Ошибка при отправке файла: {e}")
    else:
        if update.message is None:
            return  # или raise или что-то, если ситуация невозможна
        await update.message.reply_text(
            "Обработанное видео не найдено. Возможно, обработка ещё не завершена или видео не существует."
        )
    # PROJECT_ROOT = "E:/HSE_HERNYA/python_4_course/EgorBelov-social-video-object-recognition"
    # abs_video_path = os.path.join(PROJECT_ROOT, video_path)
    # processed_path = abs_video_path.replace(os.path.join(PROJECT_ROOT, "videos"), os.path.join(PROJECT_ROOT, "processed_videos"))
    # print(processed_path)
    # if os.path.exists(processed_path):
    #     # Предположим, раз файл есть — значит обработка завершена
    #     try:
    #         with open(processed_path, 'rb') as vid_file:
    #             await update.message.reply_video(video=vid_file)
    #     except Exception as e:
    #         await update.message.reply_text(f"Ошибка при отправке файла: {str(e)}")
    # else:
    #     # Файл не найден — видимо, ещё не обработан
    #     await update.message.reply_text(
    #         "Обработанное видео не найдено. "
    #         "Возможно, обработка ещё не завершена или видео не существует."
    #     )


# Регистрируем команды и хендлеры
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('search', search_videos))
application.add_handler(CommandHandler("status", status_video))
# Принимаем только видеофайлы
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))


# Запуск бота
if __name__ == "__main__":
    print("Telegram bot is starting...")
    application.run_polling()

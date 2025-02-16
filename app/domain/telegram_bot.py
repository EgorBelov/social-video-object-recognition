import cv2
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


import asyncio
from app.domain.object_recognition import calculate_video_hash, recognize_objects_on_video, save_video_in_db
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.api.views import create_video
from app.models.object import Object
from app.models.video import Video
from app.infrastructure.database import SessionLocal
from datetime import datetime





# Токен, полученный от BotFather
API_TOKEN = "8029380554:AAHeZmmWtbpfioHQ6yEFeTP2ZjkDbX1Y4Iw"

# Создаем объект Application
application = Application.builder().token(API_TOKEN).build()

# Функция для обработки команды /start
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я могу помочь найти видео с распознанными объектами. Отправь мне видео.")






def check_video_integrity(processed_video_path):
    # Пробуем открыть видео с помощью OpenCV, чтобы удостовериться, что оно не повреждено
    cap = cv2.VideoCapture(processed_video_path)
    if not cap.isOpened():
        print(f"Ошибка при открытии обработанного видео: {processed_video_path}")
        return False
    cap.release()
    return True

# Функция для обработки видео
async def handle_video(update: Update, context):
    if update.message.video:
        video_file = update.message.video
    elif update.message.document and update.message.document.mime_type.startswith('video/'):
        video_file = update.message.document
    else:
        await update.message.reply_text("Пожалуйста, отправьте видео!")
        return

    # Скачиваем видео
    file = await video_file.get_file()
    video_path = f"videos/{video_file.file_id}.mp4"
    
     
    await file.download_to_drive(video_path)
    await update.message.reply_text("Видео получено, начинаю обработку...")

    # Сохраняем видео в базу данных
    title = f"Video {video_file.file_id}"
    description = "Описание видео"
    video_id, is_new = save_video_in_db(video_path, title, description)
    # Проверка, если видео уже существует в базе данных
    if not is_new:  # Если video_id == None, это значит, что видео уже обработано
        await update.message.reply_text("Это видео уже было обработано. Отправляю его снова.")
        # Отправляем обработанное видео
        await send_processed_video_and_info(video_path, video_id, update)
        return

    # В противном случае, запускаем обработку видео и отправляем его обратно
    await process_and_send_video(video_path, video_id, update)

  
  
async def send_processed_video_and_info(video_path,video_id, update):
    # Путь к обработанному видео
    processed_video_path = video_path.replace("videos/", "processed_videos/")


    # Извлекаем распознанные объекты из базы данных
    db = SessionLocal()
    video_hash = calculate_video_hash(video_path)
    existing_video = db.query(Video).filter(Video.hash == video_hash).first()

    if existing_video:
        # Извлекаем все объекты для этого видео
        recognized_objects = db.query(Object).filter(Object.video_id == existing_video.id).all()
        if recognized_objects:
            # Преобразуем каждый объект в строку с его меткой (label) и количеством
            objects_message = "В этом видео были найдены следующие объекты:\n" + "\n".join(
                [f"{obj.label}: {obj.count} раз(а)" for obj in recognized_objects]
            )
            await update.message.reply_text(objects_message)
        else:
            await update.message.reply_text("Объекты не были распознаны в этом видео.")

    # Проверка на существование обработанного видео
    if os.path.exists(processed_video_path) and os.path.getsize(processed_video_path) > 0:
        with open(processed_video_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file)  # Отправляем обработанное видео
    else:
        await update.message.reply_text("Произошла ошибка: видео не найдено или повреждено.")

    db.close()
  
async def process_and_send_video(video_path, video_id, update):
    # Обрабатываем видео
    recognized_labels  = recognize_objects_on_video(video_path, video_id)

    processed_video_path = video_path.replace("videos/", "processed_videos/")

    # Извлекаем распознанные объекты из базы данных
    db = SessionLocal()
    recognized_objects = db.query(Object).filter(Object.video_id == video_id).all()

    if recognized_objects:
        # Формируем сообщение с объектами и количеством встреч
        objects_message = "В этом видео были найдены следующие объекты:\n"
        for obj in recognized_objects:
            objects_message += f"{obj.label}: {obj.count} раз(а)\n"
        await update.message.reply_text(objects_message)
    else:
        await update.message.reply_text("Объекты не были распознаны в этом видео.")
    
    if os.path.exists(processed_video_path) and os.path.getsize(processed_video_path) > 0:
        with open(processed_video_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file)  
    else:
        await update.message.reply_text("Произошла ошибка: видео не найдено или повреждено.")




async def search_videos(update: Update, context):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Пожалуйста, введите запрос для поиска.")
        return

    db = SessionLocal()

    # Ищем видео с нужным объектом
    results = db.query(Video).join(Object).filter(Object.label.like(f"%{query}%")).all()

    if not results:
        await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
        db.close()
        return

    # Отправляем найденные видео
    for video in results:
        processed_video_path = video.url.replace("videos/", "processed_videos/")

        # Проверяем, существует ли обработанное видео
        if os.path.exists(processed_video_path):
            try:
                # Отправляем видео в Telegram
                with open(processed_video_path, 'rb') as video_file:
                    await update.message.reply_video(video=video_file)
            except Exception as e:
                await update.message.reply_text(f"Произошла ошибка при отправке видео: {str(e)}")
        else:
            await update.message.reply_text(f"Видео {video.title} не найдено или не обработано.")

    db.close()






# Регистрация команд и обработчиков
application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler("search", search_videos))


application.add_handler(MessageHandler(filters.ALL, handle_video))



# Запуск бота
application.run_polling()

import hashlib
import os
from celery import Celery
import cv2
from dotenv import load_dotenv
import numpy as np
import requests
from infrastructure.database import SessionLocal
from models.video import Video
from models.object import Object
from datetime import datetime
# from common.celery_app import celery_app
load_dotenv()


def calculate_video_hash(video_path):
    """Вычисление SHA256 хэш-суммы файла."""
    sha256_hash = hashlib.sha256()
    with open(video_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    print(f"Video hash: {sha256_hash.hexdigest()}")  # Логирование хэша
    return sha256_hash.hexdigest()

# Путь к файлам модели YOLO
# yolo_cfg = r"E:\HSE_HERNYA\python_4_course\EgorBelov-social-video-object-recognition\yolo_model\yolov4.cfg"
# yolo_weights = r"E:\HSE_HERNYA\python_4_course\EgorBelov-social-video-object-recognition\yolo_model\yolov4.weights"
# yolo_names = r"E:\HSE_HERNYA\python_4_course\EgorBelov-social-video-object-recognition\yolo_model\coco.names"


# Определяем базовую директорию как ту, где лежит этот файл tasks.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Пути к моделям YOLO: внутри контейнера мы будем использовать относительные пути
# Предположим, что мы копируем папку yolo_model в /app/yolo_model
yolo_dir = os.path.join(BASE_DIR, "yolo_model")
yolo_cfg = os.path.join(yolo_dir, "yolov4.cfg")
yolo_weights = os.path.join(yolo_dir, "yolov4.weights")
yolo_names = os.path.join(yolo_dir, "coco.names")


# Проверяем, что файлы существуют
if not os.path.exists(yolo_cfg):
    raise FileNotFoundError(f"Не найден файл конфигурации: {yolo_cfg}")
if not os.path.exists(yolo_weights):
    raise FileNotFoundError(f"Не найдены веса: {yolo_weights}")
if not os.path.exists(yolo_names):
    raise FileNotFoundError(f"Не найден файл классов: {yolo_names}")


# Загрузка сети YOLO
net = cv2.dnn.readNetFromDarknet(yolo_cfg, yolo_weights)

# Получаем имена всех слоев
layer_names = net.getLayerNames()

# Получаем выходные слои
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]  # Правильный способ получения выходных слоев

# Загрузка классов объектов
with open(yolo_names, "r") as f:
    classes = [line.strip() for line in f.readlines()]


# celery_app = Celery("worker", broker="amqp://guest:guest@localhost:5672//")  # или ваш RabbitMQ DSN
celery_app = Celery("worker", broker="amqp://guest:guest@rabbitmq:5672//")


@celery_app.task(name="tasks.recognize_objects_on_video")
def recognize_objects_on_video(video_id):

    # api_url = "http://127.0.0.1:8000"
    api_url = os.getenv("API_URL", "")

    resp = requests.get(f"{api_url}/videos/{video_id}")
    if resp.status_code != 200:
        print(f"Не удалось получить данные видео (id={video_id}), статус: {resp.status_code}")
        return

    video_data = resp.json()  # допустим, {"id": 24, "title": "...", "description": "...", "url": "videos/xxx.mp4", ...}
    video_path = video_data.get("url")
    if not video_path:
        print(f"В данных видео (id={video_id}) отсутствует поле url.")
        return

    # Открываем видео
    # cap = cv2.VideoCapture("../../" + video_path)
    # Получаем PROJECT_ROOT, например, /app
    PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    # Если API сохраняет видео с путём "videos/xxx.mp4", то формируем абсолютный путь:
    abs_video_path = os.path.join(PROJECT_ROOT, video_path)  # video_path из БД, например "videos/xxx.mp4"
    print("Путь к исходному видео:", abs_video_path, os.path.exists(abs_video_path))
    cap = cv2.VideoCapture(abs_video_path)
    if not cap.isOpened():
        print(f"Ошибка при открытии видео: {video_path}")
        return

    # Получаем параметры видео
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if width == 0 or height == 0:
        print("Неверные размеры видео")
        cap.release()
        return

    # Создаем директорию для сохранения обработанного видео
    # output_path = video_path.replace("videos/", "../../processed_videos/")
    # output_dir = os.path.dirname(output_path)
    # os.makedirs(output_dir, exist_ok=True)

    PROCESSED_DIR = os.path.join(PROJECT_ROOT, "processed_videos")
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    # Заменяем часть пути:
    processed_path = abs_video_path.replace(os.path.join(PROJECT_ROOT, "videos"), PROCESSED_DIR)
    print("Путь к обработанному видео:", processed_path)
    # Создаем объект VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Кодек для MP4
    # video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    video_writer = cv2.VideoWriter(processed_path, fourcc, fps, (width, height))
    if not video_writer.isOpened():
        print("Ошибка создания VideoWriter")
        cap.release()
        return

    # Создаем сессию для работы с базой данных
    db = SessionLocal()

    recognized_labels = []  # Список для хранения распознанных объектов

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Обработка кадра YOLO
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        outs = net.forward(output_layers)

        class_ids, confidences, boxes = [], [], []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    # Вычисление координат
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

                    # Определяем метку объекта (label)
                    label = classes[class_id]

                    if label not in recognized_labels:
                        recognized_labels.append(label)

                    # Проверка на наличие объекта в базе данных
                    existing_object = db.query(Object).filter(
                        Object.video_id == video_id,
                        Object.label == label,
                    ).first()

                    if existing_object:
                        # Увеличиваем счетчик встреч объекта
                        existing_object.count += 1
                        db.commit()
                    else:
                        # Если объекта нет, создаем новый и добавляем в БД
                        recognized_object = Object(
                            label=label,
                            confidence=float(confidence),
                            video_id=video_id,
                            count=1  # Начальный счетчик = 1
                        )
                        db.add(recognized_object)
                        db.commit()

        # Применяем Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                label = classes[class_ids[i]]
                confidence = confidences[i]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Записываем обработанный кадр
        if video_writer.isOpened():
            video_writer.write(frame)

    # Сохраняем все изменения в базе данных
    db.commit()

    # Освобождаем ресурсы
    cap.release()
    if video_writer.isOpened():
        video_writer.release()
    db.close()
    print(f"Обработанное видео сохранено: {processed_path}")
    return recognized_labels


# def save_video_in_db(video_path, title, description):

#     # Проверка на наличие уже загруженного видео
#     video_hash = calculate_video_hash(video_path)

#     db = SessionLocal()

#     # Ищем видео с таким же хэшем в базе данных
#     existing_video = db.query(Video).filter(Video.hash == video_hash).first()

#     if existing_video:
#         # Если видео с таким хэшем уже есть, возвращаем его id и флаг, что видео уже есть
#         db.close()
#         return existing_video.id, False  # Видео уже есть, не обрабатываем его

#     # Сохраняем данные о видео
#     video = Video(
#         title=title,
#         description=description,
#         url=video_path,
#         platform="Telegram",  # или другая платформа
#         timestamp=datetime.now(),  # Пример времени
#         hash=video_hash  # Сохраняем хэш
#     )
#     db.add(video)
#     db.commit()

#     # Возвращаем ID видео для использования в распознавании объектов
#     video_id = video.id
#     db.close()
#     return video_id, True

# Пример использования
if __name__ == "__main__":
    video_path = "E:/Downloads/0_Fireplace_Fire_720x1280.mp4"  # Путь к видео
    recognize_objects_on_video(video_path)

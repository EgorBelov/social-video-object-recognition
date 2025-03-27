# worker_service/worker/worker_main.py
import sys
import os
from tasks import recognize_objects_on_video
from tasks import celery_app


sys.path.append(os.path.dirname(__file__))


def run_worker_test():
    # Пример тестового вызова
    video_path = "E:/HSE_HERNYA/python_4_course/EgorBelov-social-video-object-recognition/videos/BAACAgIAAxkBAAIBNmext9Kf5wG9_1plI77XSVXEaXlQAALhZgACJaKISeiuV_R3u1TrNgQ.mp4"
    # Предположим, у нас уже есть запись в БД c video_id = 1
    recognize_objects_on_video(video_path, video_id=1)


if __name__ == "__main__":
    # Пример, если у вас есть tasks.process_video
    print("Начинаю обработку видео:")
    result = celery_app.send_task("tasks.recognize_objects_on_video", args=["E:/HSE_HERNYA/python_4_course/EgorBelov-social-video-object-recognition/videos/BAACAgIAAxkBAAIBNmext9Kf5wG9_1plI77XSVXEaXlQAALhZgACJaKISeiuV_R3u1TrNgQ.mp4", 1])
    print("Task dispatched:", result.id)

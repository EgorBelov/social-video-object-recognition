from fastapi import FastAPI
from app.api import views
from app.infrastructure.object_recognition import save_video_in_db, recognize_objects_on_video

def process_video(video_path, title, description):
    # Сначала сохраняем видео в базу данных
    video_id = save_video_in_db(video_path, title, description)

    # Затем начинаем распознавание объектов и сохраняем результаты в БД
    recognize_objects_on_video(video_path, video_id)


app = FastAPI()

app.include_router(views.router)

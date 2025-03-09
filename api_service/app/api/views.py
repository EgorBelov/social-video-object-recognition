from fastapi import APIRouter, Depends
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from infrastructure.database import SessionLocal
from models.video import Video
from models.object import Object
from datetime import datetime

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from celery import Celery

celery_app = Celery("worker", broker="amqp://guest:guest@rabbitmq:5672//")

router = APIRouter()

# Получение сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/videos/")
async def create_video(title: str, description: str, url: str, platform: str, hash: str, db: Session = Depends(get_db)):
    db_video = Video(title=title, description=description, url=url, platform=platform, timestamp=datetime.now(), hash = hash)
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@router.get("/videos/{video_id}")
async def read_video(video_id: int, db: Session = Depends(get_db)):
    db_video = db.query(Video).filter(Video.id == video_id).first()
    return db_video


@router.get("/search_by_object/")
async def search_videos_by_object(object_name: str):
    db: Session = SessionLocal()

    # Ищем видео с нужным объектом
    results = db.query(Video).join(Object).filter(Object.label.like(f"%{object_name}%")).all()

    if not results:
        db.close()
        raise HTTPException(status_code=404, detail=f"По запросу '{object_name}' ничего не найдено.")

    # Отправляем список найденных видео
    video_info = []
    for video in results:
        objects = db.query(Object).filter(Object.video_id == video.id).all()
        video_data = {
            "title": video.title,
            "description": video.description,
            "url": video.url,
            "objects": [{"label": obj.label, "count": obj.count} for obj in objects]
        }
        video_info.append(video_data)
    
    db.close()
    return video_info


@router.post("/videos/{video_id}/process")
async def process_video(video_id: int, db: Session = Depends(get_db)):
    
    
    celery_app.send_task("tasks.recognize_objects_on_video", args=[video_id])
    return {"message": f"Video {video_id} queued for processing"}

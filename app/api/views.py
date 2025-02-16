from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import SessionLocal
from app.models.video import Video
from app.models.object import Object
from datetime import datetime

router = APIRouter()

# Получение сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/videos/")
async def create_video(title: str, description: str, url: str, platform: str, db: Session = Depends(get_db)):
    db_video = Video(title=title, description=description, url=url, platform=platform, timestamp=datetime.now())
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@router.get("/videos/{video_id}")
def read_video(video_id: int, db: Session = Depends(get_db)):
    db_video = db.query(Video).filter(Video.id == video_id).first()
    return db_video

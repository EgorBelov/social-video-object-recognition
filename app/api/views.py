from fastapi import APIRouter, Depends
from fastapi import APIRouter, HTTPException
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


# @app.post("/process_video/")
# async def process_video(video: UploadFile = File(...), title: str = '', description: str = ''):
#     try:
#         # Сохраняем видео в базу данных
#         video_path = f"videos/{video.filename}"
#         with open(video_path, "wb") as buffer:
#             buffer.write(await video.read())

#         # Сохраняем видео и начинаем обработку
#         video_id = save_video_in_db(video_path, title, description)
#         recognize_objects_on_video(video_path, video_id)

#         return {"message": "Видео успешно обработано", "video_id": video_id}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
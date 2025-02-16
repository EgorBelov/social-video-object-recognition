from fastapi import FastAPI, UploadFile, File, HTTPException
from api import views
from domain.object_recognition import save_video_in_db, recognize_objects_on_video

app = FastAPI()

# Подключаем маршруты
app.include_router(views.router)




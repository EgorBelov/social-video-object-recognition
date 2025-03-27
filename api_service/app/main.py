from fastapi import FastAPI, UploadFile, File, HTTPException
from api import views
from infrastructure.database import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI()

# Подключаем маршруты
app.include_router(views.router)

from fastapi import FastAPI, UploadFile, File, HTTPException
from api import views


app = FastAPI()

# Подключаем маршруты
app.include_router(views.router)




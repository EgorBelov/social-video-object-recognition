from fastapi import FastAPI, UploadFile, File, HTTPException
from api import views
import os
from infrastructure.database import Base, engine


Base.metadata.create_all(bind=engine)

app = FastAPI()

# Подключаем маршруты
app.include_router(views.router)


@app.get("/ping")
def ping():
    instance_name = os.getenv("INST_NAME", "unknown")
    return {"message": f"Hello from {instance_name}!"}

# app/init_db.py
import sys
import os

from database import engine
from models import Base

# Создаем все таблицы, описанные в моделях
Base.metadata.create_all(bind=engine)
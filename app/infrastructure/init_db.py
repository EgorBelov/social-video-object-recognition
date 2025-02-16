# app/init_db.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database import engine
from app.models import Base

# Создаем все таблицы, описанные в моделях
Base.metadata.create_all(bind=engine)
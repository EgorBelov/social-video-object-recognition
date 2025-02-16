from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

import app.main as main

client = TestClient(main)

def test_create_video():
    response = client.post("/videos/", json={"title": "Test Video", "description": "Test Description", "url": "http://test.com", "platform": "Telegram"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Video"
    assert "id" in data
    assert "timestamp" in data

def test_read_video():
    # Сначала создаем видео
    client.post("/videos/", json={"title": "Test Video", "description": "Test Description", "url": "http://test.com", "platform": "Telegram"})

    # Получаем видео по ID
    response = client.get("/videos/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Test Video"
    assert data["description"] == "Test Description"


def test_search_videos_by_object():
    # Сначала создаем видео с объектами
    client.post("/videos/", json={"title": "Test Video", "description": "Test Description", "url": "http://test.com", "platform": "Telegram"})
    # Мокаем данные объектов
    client.post("/videos/1/objects/", json={"label": "person", "count": 3})

    # Ищем видео по объекту
    response = client.get("/search_by_object/?object_name=person")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == "Test Video"
    assert "objects" in data[0]
    assert data[0]["objects"][0]["label"] == "person"
    
    
def test_video_processing_and_send():
    # Отправляем видео
    with open("test_video.mp4", "rb") as video_file:
        response = client.post("/videos/", files={"file": video_file})

    assert response.status_code == 200
    video_data = response.json()
    video_id = video_data["id"]

    # Проверяем, что видео было успешно обработано
    processed_video_path = video_data["url"].replace("videos/", "processed_videos/")

    response = client.get(f"/videos/{video_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == video_id
    assert data["url"] == processed_video_path

    # Проверяем поиск по объектам
    response = client.get("/search_by_object/?object_name=person")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0





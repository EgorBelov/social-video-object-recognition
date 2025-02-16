from fastapi.testclient import TestClient
import main

client = TestClient(main)

def test_create_video():
    response = client.post("/videos/", json={"title": "Test Video", "description": "Test Description", "url": "http://test.com", "platform": "Telegram"})
    assert response.status_code == 200
    assert response.json()["title"] == "Test Video"

def test_read_video():
    response = client.get("/videos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

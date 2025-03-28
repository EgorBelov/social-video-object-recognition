import time
import pytest
import requests
import random
hash = random.getrandbits(128)

COMPOSE_API_URL = "http://localhost:80"   # Порт, проброшенный из docker-compose

def wait_for_service(url, timeout=30):
    """Проверяем, что сервис отзывается."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url + "/docs")
            if resp.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

@pytest.mark.e2e
def test_end_to_end_scenario():
    # 1. Ждем, что API поднялся
    ready = wait_for_service(COMPOSE_API_URL)
    assert ready, "API не поднялся за 30 секунд"

    # 2. Создаем видео
    payload = {
        "title": "E2ETest",
        "description": "desc",
        "url": "videos/e2e_test.mp4",
        "platform": "Telegram",
        "hash": hash
    }
    resp_create = requests.post(f"{COMPOSE_API_URL}/videos/", params=payload)
    assert resp_create.status_code == 200
    video_data = resp_create.json()
    video_id = video_data["id"]

    # 3. Запускаем обработку
    resp_process = requests.post(f"{COMPOSE_API_URL}/videos/{video_id}/process")
    assert resp_process.status_code == 200

    # 4. Ждем ~ N секунд, пока worker не закончит работу
    time.sleep(10)

    # 5. Проверяем, что video действительно обработано
    resp_status = requests.get(f"{COMPOSE_API_URL}/videos/{video_id}")
    assert resp_status.status_code == 200
    result_data = resp_status.json()

    # Например, проверяем наличие каких-то полей, или опрашиваем эндпойнт /search_by_object
    # ...

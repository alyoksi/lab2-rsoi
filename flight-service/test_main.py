from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

def test_get_flights():
    response = client.get("/api/v1/flights?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "totalElements" in data
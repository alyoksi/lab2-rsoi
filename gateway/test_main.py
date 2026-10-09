from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

@patch("httpx.AsyncClient.get")
def test_gateway_get_flights(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "page": 1,
        "pageSize": 10,
        "totalElements": 1,
        "items": [{"flightNumber": "AFL031"}]
    }
    mock_get.return_value = mock_response

    response = client.get("/api/v1/flights?page=1&size=10")
    assert response.status_code == 200
    assert response.json()["totalElements"] == 1

@patch("httpx.AsyncClient.get")
def test_gateway_get_privilege(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "balance": 1500,
        "status": "GOLD",
        "history": []
    }
    mock_get.return_value = mock_response

    response = client.get("/api/v1/privilege", headers={"X-User-Name": "Test Max"})
    assert response.status_code == 200
    assert response.json()["balance"] == 1500
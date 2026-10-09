import os

os.environ["DB_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from main import app, engine, Base, SessionLocal, Airport, Flight
import datetime

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    a1 = Airport(id=1, name="Шереметьево", city="Москва", country="Россия")
    a2 = Airport(id=2, name="Пулково", city="Санкт-Петербург", country="Россия")
    db.add_all([a1, a2])
    db.commit()
    
    f1 = Flight(
        id=1,
        flight_number="AFL031",
        datetime=datetime.datetime(2021, 10, 8, 20, 0, tzinfo=datetime.timezone.utc),
        from_airport_id=2,
        to_airport_id=1,
        price=1500
    )
    db.add(f1)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_health():
    response = client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

def test_get_flights():
    response = client.get("/api/v1/flights?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["totalElements"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["flightNumber"] == "AFL031"

def test_get_flight_by_number():
    response = client.get("/api/v1/flights/AFL031")
    assert response.status_code == 200
    assert response.json()["flightNumber"] == "AFL031"

    response_404 = client.get("/api/v1/flights/UNKNOWN")
    assert response_404.status_code == 404
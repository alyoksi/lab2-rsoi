import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, Base, get_db, Airport, Flight
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    a1 = Airport(id=1, name="Шереметьево", city="Москва", country="Россия")
    a2 = Airport(id=2, name="Пулково", city="Санкт-Петербург", country="Россия")
    db.add_all([a1, a2])
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
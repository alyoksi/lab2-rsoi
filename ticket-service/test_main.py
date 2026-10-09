import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, Base, get_db, Ticket
import uuid

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

def test_health():
    response = client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

def test_ticket_lifecycle():
    t_uid = str(uuid.uuid4())
    
    # 1. Покупка (создание) билета
    payload = {
        "flightNumber": "AFL031",
        "price": 1500,
        "username": "Test Max",
        "ticketUid": t_uid
    }
    res = client.post("/api/v1/tickets", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ticketUid"] == t_uid
    assert data["status"] == "PAID"

    # 2. Получение всех билетов пользователя
    res_all = client.get("/api/v1/tickets", headers={"X-User-Name": "Test Max"})
    assert res_all.status_code == 200
    assert len(res_all.json()) == 1

    # 3. Получение конкретного билета
    res_one = client.get(f"/api/v1/tickets/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_one.status_code == 200
    assert res_one.json()["ticketUid"] == t_uid

    # 4. Отмена (возврат) билета
    res_del = client.delete(f"/api/v1/tickets/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_del.status_code == 200

    # 5. Проверка изменения статуса на CANCELED
    res_canceled = client.get(f"/api/v1/tickets/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_canceled.json()["status"] == "CANCELED"
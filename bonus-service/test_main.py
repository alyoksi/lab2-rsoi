import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, Base, get_db, Privilege
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
    db = TestingSessionLocal()
    p = Privilege(username="Test Max", status="GOLD", balance=1500)
    db.add(p)
    db.commit()
    db.close()

def test_health():
    response = client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

def test_get_privilege():
    response = client.get("/api/v1/privilege", headers={"X-User-Name": "Test Max"})
    assert response.status_code == 200
    assert response.json()["balance"] == 1500
    assert response.json()["status"] == "GOLD"

def test_use_and_refund_bonus():
    t_uid = str(uuid.uuid4())
    payload = {
        "ticketUid": t_uid,
        "price": 1500,
        "paidFromBalance": True
    }
    # Использование бонусов
    res = client.post("/api/v1/privilege/use", json=payload, headers={"X-User-Name": "Test Max"})
    assert res.status_code == 200
    assert res.json()["paidByBonuses"] == 1500
    assert res.json()["balance"] == 0

    # Возврат бонусов при отмене
    res_ref = client.delete(f"/api/v1/privilege/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_ref.status_code == 200
import os

os.environ["DB_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from main import app, engine, Base, SessionLocal, Privilege
import uuid

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    p = Privilege(username="Test Max", status="GOLD", balance=1500)
    db.add(p)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

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
    res = client.post("/api/v1/privilege/use", json=payload, headers={"X-User-Name": "Test Max"})
    assert res.status_code == 200
    assert res.json()["paidByBonuses"] == 1500
    assert res.json()["balance"] == 0

    res_ref = client.delete(f"/api/v1/privilege/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_ref.status_code == 200
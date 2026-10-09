import os

os.environ["DB_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from main import app, engine, Base, SessionLocal, Ticket
import uuid

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health():
    response = client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

def test_ticket_lifecycle():
    t_uid = str(uuid.uuid4())
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

    res_all = client.get("/api/v1/tickets", headers={"X-User-Name": "Test Max"})
    assert res_all.status_code == 200
    assert len(res_all.json()) == 1

    res_one = client.get(f"/api/v1/tickets/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_one.status_code == 200
    assert res_one.json()["ticketUid"] == t_uid

    res_del = client.delete(f"/api/v1/tickets/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_del.status_code == 200

    res_canceled = client.get(f"/api/v1/tickets/{t_uid}", headers={"X-User-Name": "Test Max"})
    assert res_canceled.json()["status"] == "CANCELED"
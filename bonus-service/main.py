import os
import uuid
import datetime
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, UUID
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from pydantic import BaseModel
from typing import Optional

DB_URL = os.getenv("DB_URL", "postgresql://program:test@localhost:5432/privileges")
connect_args = {"check_same_thread": False} if "sqlite" in DB_URL else {}
engine = create_engine(DB_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Privilege(Base):
    __tablename__ = "privilege"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False)
    status = Column(String(80), nullable=False, default="BRONZE")
    balance = Column(Integer, default=0)

class PrivilegeHistory(Base):
    __tablename__ = "privilege_history"
    id = Column(Integer, primary_key=True, index=True)
    privilege_id = Column(Integer, ForeignKey("privilege.id"))
    ticket_uid = Column(UUID(as_uuid=True), nullable=False)
    datetime = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    balance_diff = Column(Integer, nullable=False)
    operation_type = Column(String(20), nullable=False)

    privilege = relationship("Privilege")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Bonus Service")

@app.on_event("startup")
def seed_bonus():
    db = SessionLocal()
    if db.query(Privilege).filter(Privilege.username == "Test Max").count() == 0:
        p = Privilege(username="Test Max", status="GOLD", balance=1500)
        db.add(p)
        db.commit()
        db.refresh(p)
        h = PrivilegeHistory(
            privilege_id=p.id,
            ticket_uid=uuid.UUID("049161bb-badd-4fa8-9d90-87c9a82b0668"), # Преобразуем в UUID
            datetime=datetime.datetime(2021, 10, 8, 19, 59, 19),
            balance_diff=1500,
            operation_type="FILL_IN_BALANCE"
        )
        db.add(h)
        db.commit()
    db.close()

@app.get("/manage/health")
def health():
    return {"status": "OK"}

def get_or_create_privilege(db: Session, username: str):
    p = db.query(Privilege).filter(Privilege.username == username).first()
    if not p:
        p = Privilege(username=username, status="BRONZE", balance=0)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p

@app.get("/api/v1/privilege")
def get_privilege(x_user_name: str = Header(..., alias="X-User-Name"), db: Session = Depends(get_db)):
    p = get_or_create_privilege(db, x_user_name)
    history = db.query(PrivilegeHistory).filter(PrivilegeHistory.privilege_id == p.id).all()
    h_list = []
    for h in history:
        h_list.append({
            "date": h.datetime.isoformat() + "Z",
            "ticketUid": str(h.ticket_uid),
            "balanceDiff": h.balance_diff,
            "operationType": h.operation_type
        })
    return {
        "balance": p.balance,
        "status": p.status,
        "history": h_list
    }

class BalanceOperation(BaseModel):
    ticketUid: str
    price: int
    paidFromBalance: bool

@app.post("/api/v1/privilege/use")
def use_or_accrue_bonus(data: BalanceOperation, x_user_name: str = Header(..., alias="X-User-Name"), db: Session = Depends(get_db)):
    p = get_or_create_privilege(db, x_user_name)
    paid_by_bonuses = 0
    paid_by_money = data.price

    if data.paidFromBalance:
        paid_by_bonuses = min(p.balance, data.price)
        paid_by_money = data.price - paid_by_bonuses
        p.balance -= paid_by_bonuses
        op_type = "DEBIT_THE_ACCOUNT"
        diff = -paid_by_bonuses
    else:
        accrued = int(data.price * 0.1)
        p.balance += accrued
        op_type = "FILL_IN_BALANCE"
        diff = accrued

    db.commit()

    h = PrivilegeHistory(
        privilege_id=p.id,
        ticket_uid=uuid.UUID(data.ticketUid), # Преобразуем строку в uuid.UUID
        datetime=datetime.datetime.utcnow(),
        balance_diff=diff,
        operation_type=op_type
    )
    db.add(h)
    db.commit()

    return {
        "paidByMoney": paid_by_money,
        "paidByBonuses": paid_by_bonuses,
        "balance": p.balance,
        "status": p.status
    }

@app.delete("/api/v1/privilege/{ticket_uid}")
def refund_bonus(ticket_uid: str, x_user_name: str = Header(..., alias="X-User-Name"), db: Session = Depends(get_db)):
    try:
        u_uid = uuid.UUID(ticket_uid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    p = get_or_create_privilege(db, x_user_name)
    h = db.query(PrivilegeHistory).filter(PrivilegeHistory.privilege_id == p.id, PrivilegeHistory.ticket_uid == u_uid).first()
    if h:
        p.balance -= h.balance_diff
        if p.balance < 0:
            p.balance = 0
        db.delete(h)
        db.commit()
    return {"status": "OK"}
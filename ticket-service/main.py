import os
import uuid
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, UUID
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import Optional

DB_URL = os.getenv("DB_URL", "postgresql://program:test@localhost:5432/tickets")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Ticket(Base):
    __tablename__ = "ticket"
    id = Column(Integer, primary_key=True, index=True)
    ticket_uid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    username = Column(String(80), nullable=False)
    flight_number = Column(String(20), nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="PAID")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Ticket Service")

class TicketCreate(BaseModel):
    flightNumber: str
    price: int
    username: str
    ticketUid: Optional[str] = None

@app.get("/manage/health")
def health():
    return {"status": "OK"}

@app.get("/api/v1/tickets")
def get_tickets(x_user_name: str = Header(..., alias="X-User-Name"), db: Session = Depends(get_db)):
    tickets = db.query(Ticket).filter(Ticket.username == x_user_name).all()
    result = []
    for t in tickets:
        result.append({
            "ticketUid": str(t.ticket_uid),
            "flightNumber": t.flight_number,
            "price": t.price,
            "status": t.status
        })
    return result

@app.get("/api/v1/tickets/{ticket_uid}")
def get_ticket(ticket_uid: str, x_user_name: str = Header(..., alias="X-User-Name"), db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.ticket_uid == ticket_uid, Ticket.username == x_user_name).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {
        "ticketUid": str(t.ticket_uid),
        "flightNumber": t.flight_number,
        "price": t.price,
        "status": t.status
    }

@app.post("/api/v1/tickets")
def create_ticket(data: TicketCreate, db: Session = Depends(get_db)):
    t_uid = uuid.UUID(data.ticketUid) if data.ticketUid else uuid.uuid4()
    t = Ticket(
        ticket_uid=t_uid,
        username=data.username,
        flight_number=data.flightNumber,
        price=data.price,
        status="PAID"
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {
        "ticketUid": str(t.ticket_uid),
        "flightNumber": t.flight_number,
        "price": t.price,
        "status": t.status
    }

@app.delete("/api/v1/tickets/{ticket_uid}")
def cancel_ticket(ticket_uid: str, x_user_name: str = Header(..., alias="X-User-Name"), db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.ticket_uid == ticket_uid, Ticket.username == x_user_name).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    t.status = "CANCELED" 
    db.commit()
    return {"status": "CANCELED"}
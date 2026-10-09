import os
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from pydantic import BaseModel
from typing import List, Optional

DB_URL = os.getenv("DB_URL", "postgresql://program:test@localhost:5432/flights")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Airport(Base):
    __tablename__ = "airport"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    city = Column(String(255))
    country = Column(String(255))

class Flight(Base):
    __tablename__ = "flight"
    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String(20), nullable=False)
    datetime = Column(DateTime(timezone=True), nullable=False)
    from_airport_id = Column(Integer, ForeignKey("airport.id"))
    to_airport_id = Column(Integer, ForeignKey("airport.id"))
    price = Column(Integer, nullable=False)

    from_airport = relationship("Airport", foreign_keys=[from_airport_id])
    to_airport = relationship("Airport", foreign_keys=[to_airport_id])

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Flight Service")

@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    if db.query(Airport).count() == 0:
        a1 = Airport(id=1, name="Шереметьево", city="Москва", country="Россия")
        a2 = Airport(id=2, name="Пулково", city="Санкт-Петербург", country="Россия")
        db.add_all([a1, a2])
        db.commit()
    if db.query(Flight).count() == 0:
        import datetime
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

@app.get("/manage/health")
def health():
    return {"status": "OK"}

@app.get("/api/v1/flights")
def get_flights(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Flight)
    total = query.count()
    offset = (page - 1) * size
    flights = query.offset(offset).limit(size).all()

    items = []
    for f in flights:
        items.append({
            "flightNumber": f.flight_number,
            "fromAirport": f"{f.from_airport.city} {f.from_airport.name}",
            "toAirport": f"{f.to_airport.city} {f.to_airport.name}",
            "date": f.datetime.strftime("%Y-%m-%d %H:%M"),
            "price": f.price
        })
    return {
        "page": page,
        "pageSize": size,
        "totalElements": total,
        "items": items
    }

@app.get("/api/v1/flights/{flight_number}")
def get_flight(flight_number: str, db: Session = Depends(get_db)):
    f = db.query(Flight).filter(Flight.flight_number == flight_number).first()
    if not f:
        raise HTTPException(status_code=404, detail="Flight not found")
    return {
        "flightNumber": f.flight_number,
        "fromAirport": f"{f.from_airport.city} {f.from_airport.name}",
        "toAirport": f"{f.to_airport.city} {f.to_airport.name}",
        "date": f.datetime.strftime("%Y-%m-%d %H:%M"),
        "price": f.price
    }
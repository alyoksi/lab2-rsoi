import os
import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel

FLIGHT_URL = os.getenv("FLIGHT_SERVICE_URL", "http://localhost:8060")
TICKET_URL = os.getenv("TICKET_SERVICE_URL", "http://localhost:8070")
BONUS_URL = os.getenv("BONUS_SERVICE_URL", "http://localhost:8050")

app = FastAPI(title="Gateway Service")

@app.get("/manage/health")
def health():
    return {"status": "OK"}

@app.get("/api/v1/flights")
async def get_flights(page: int = 1, size: int = 10):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{FLIGHT_URL}/api/v1/flights", params={"page": page, "size": size})
        return resp.json()

@app.get("/api/v1/privilege")
async def get_privilege(x_user_name: str = Header(..., alias="X-User-Name")):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BONUS_URL}/api/v1/privilege", headers={"X-User-Name": x_user_name})
        return resp.json()

@app.get("/api/v1/tickets")
async def get_tickets(x_user_name: str = Header(..., alias="X-User-Name")):
    async with httpx.AsyncClient() as client:
        t_resp = await client.get(f"{TICKET_URL}/api/v1/tickets", headers={"X-User-Name": x_user_name})
        tickets = t_resp.json()

        result = []
        for t in tickets:
            f_resp = await client.get(f"{FLIGHT_URL}/api/v1/flights/{t['flightNumber']}")
            f_data = f_resp.json() if f_resp.status_code == 200 else {}
            result.append({
                "ticketUid": t["ticketUid"],
                "flightNumber": t["flightNumber"],
                "fromAirport": f_data.get("fromAirport", ""),
                "toAirport": f_data.get("toAirport", ""),
                "date": f_data.get("date", ""),
                "price": t["price"],
                "status": t["status"]
            })
        return result

@app.get("/api/v1/tickets/{ticket_uid}")
async def get_ticket(ticket_uid: str, x_user_name: str = Header(..., alias="X-User-Name")):
    async with httpx.AsyncClient() as client:
        t_resp = await client.get(f"{TICKET_URL}/api/v1/tickets/{ticket_uid}", headers={"X-User-Name": x_user_name})
        if t_resp.status_code != 200:
            raise HTTPException(status_code=t_resp.status_code, detail=t_resp.json().get("detail", "Not found"))
        t = t_resp.json()

        f_resp = await client.get(f"{FLIGHT_URL}/api/v1/flights/{t['flightNumber']}")
        f_data = f_resp.json() if f_resp.status_code == 200 else {}

        return {
            "ticketUid": t["ticketUid"],
            "flightNumber": t["flightNumber"],
            "fromAirport": f_data.get("fromAirport", ""),
            "toAirport": f_data.get("toAirport", ""),
            "date": f_data.get("date", ""),
            "price": t["price"],
            "status": t["status"]
        })

class TicketPurchaseRequest(BaseModel):
    flightNumber: str
    price: int
    paidFromBalance: bool

@app.post("/api/v1/tickets")
async def purchase_ticket(data: TicketPurchaseRequest, x_user_name: str = Header(..., alias="X-User-Name")):
    async with httpx.AsyncClient() as client:
        # 1. Check flight
        f_resp = await client.get(f"{FLIGHT_URL}/api/v1/flights/{data.flightNumber}")
        if f_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Flight not found")
        f_data = f_resp.json()

        import uuid
        ticket_uid = str(uuid.uuid4())

        # 2. Use bonus service
        b_resp = await client.post(
            f"{BONUS_URL}/api/v1/privilege/use",
            json={"ticketUid": ticket_uid, "price": data.price, "paidFromBalance": data.paidFromBalance},
            headers={"X-User-Name": x_user_name}
        )
        b_data = b_resp.json()

        # 3. Create ticket
        t_resp = await client.post(
            f"{TICKET_URL}/api/v1/tickets",
            json={
                "flightNumber": data.flightNumber,
                "price": data.price,
                "username": x_user_name,
                "ticketUid": ticket_uid
            }
        )
        t_data = t_resp.json()

        return {
            "ticketUid": t_data["ticketUid"],
            "flightNumber": t_data["flightNumber"],
            "fromAirport": f_data.get("fromAirport", ""),
            "toAirport": f_data.get("toAirport", ""),
            "date": f_data.get("date", ""),
            "price": t_data["price"],
            "paidByMoney": b_data["paidByMoney"],
            "paidByBonuses": b_data["paidByBonuses"],
            "status": t_data["status"],
            "privilege": {
                "balance": b_data["balance"],
                "status": b_data["status"]
            }
        }

@app.delete("/api/v1/tickets/{ticket_uid}")
async def cancel_ticket(ticket_uid: str, x_user_name: str = Header(..., alias="X-User-Name")):
    async with httpx.AsyncClient() as client:
        t_resp = await client.delete(f"{TICKET_URL}/api/v1/tickets/{ticket_uid}", headers={"X-User-Name": x_user_name})
        if t_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Ticket not found")

        await client.delete(f"{BONUS_URL}/api/v1/privilege/{ticket_uid}", headers={"X-User-Name": x_user_name})
        return Response(status_code=204)

@app.get("/api/v1/me")
async def get_me(x_user_name: str = Header(..., alias="X-User-Name")):
    async with httpx.AsyncClient() as client:
        tickets_resp = await get_tickets(x_user_name=x_user_name)
        priv_resp = await get_privilege(x_user_name=x_user_name)

        return {
            "tickets": tickets_resp,
            "privilege": {
                "balance": priv_resp["balance"],
                "status": priv_resp["status"]
            }
        }
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

deliveries_db = {}
next_id = 1

VALID_STATUSES = ["created", "in_transit", "delivered"]

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid payload format or missing required fields"}
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/deliveries", status_code=201)
def create_delivery(data: dict = Body(...)):
    global next_id
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    
    recipient = data.get("recipient")
    address = data.get("address")
    
    if not recipient or not address or not isinstance(recipient, str) or not isinstance(address, str) or not recipient.strip() or not address.strip():
        raise HTTPException(status_code=400, detail="Recipient and address must be non-empty strings")
    
    delivery = {
        "id": next_id,
        "recipient": recipient.strip(),
        "address": address.strip(),
        "status": "created"
    }
    deliveries_db[next_id] = delivery
    next_id += 1
    return delivery

@app.get("/deliveries")
def get_deliveries(status: Optional[str] = None):
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Unknown status filter")
        return [d for d in deliveries_db.values() if d["status"] == status]
    return list(deliveries_db.values())

@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return deliveries_db[delivery_id]

@app.patch("/deliveries/{delivery_id}/status")
def update_delivery_status(delivery_id: int, data: dict = Body(...)):
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if not isinstance(data, dict) or "status" not in data:
        raise HTTPException(status_code=400, detail="Status field is required")
    
    new_status = data.get("status")
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Unknown status value")
    
    current_status = deliveries_db[delivery_id]["status"]
    
    allowed_transitions = {
        "created": "in_transit",
        "in_transit": "delivered"
    }
    
    if allowed_transitions.get(current_status) != new_status:
        raise HTTPException(status_code=409, detail="Invalid status transition")
    
    deliveries_db[delivery_id]["status"] = new_status
    return deliveries_db[delivery_id]

@app.delete("/deliveries/{delivery_id}")
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries_db:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    if deliveries_db[delivery_id]["status"] != "created":
        raise HTTPException(status_code=409, detail="Can only delete deliveries with status 'created'")
    
    del deliveries_db[delivery_id]
    return Response(status_code=204)
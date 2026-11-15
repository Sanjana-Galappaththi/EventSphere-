from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.user import User
from app.core.deps import require_role
from app.agents.bus import bus

router = APIRouter()

class ScanRequest(BaseModel):
    qr_code: str
    event_id: int

@router.post("/scan")
def scan_ticket(
    scan_in: ScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["staff", "admin"])) # Only staff/admin can scan
):
    conversation_id = str(uuid.uuid4())
    
    # Send message to TicketAgent to evaluate the scan
    response = bus.send_message(
        db=db, sender="ScannerRouter", receiver="TicketAgent",
        performative="REQUEST",
        content={"action": "scan_ticket", "qr_code": scan_in.qr_code, "event_id": scan_in.event_id},
        conversation_id=conversation_id
    )
    
    if response.get("status") != "AGREE":
        raise HTTPException(status_code=400, detail=response.get("reason"))
        
    # Notify the user or log it
    bus.send_message(
        db=db, sender="ScannerRouter", receiver="NotificationAgent",
        performative="INFORM",
        content={"message": f"Check-in successful: {response.get('attendee')}"},
        conversation_id=conversation_id
    )
    
    return {"message": response.get("reason"), "attendee": response.get("attendee")}
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingRequest, BookingResponse
from app.core.deps import get_current_user
from app.agents.bus import bus

router = APIRouter()

@router.post("/", response_model=BookingResponse)
def book_tickets(
    booking_in: BookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation_id = str(uuid.uuid4())
    
    # 1. Ask BookingAgent to reserve the tickets
    agent_response = bus.send_message(
        db=db, sender="BookingRouter", receiver="BookingAgent", 
        performative="REQUEST", 
        content={
            "action": "reserve_tickets", 
            "category_id": booking_in.ticket_category_id, 
            "quantity": booking_in.quantity
        },
        conversation_id=conversation_id
    )

    if agent_response.get("status") != "AGREE":
        raise HTTPException(status_code=400, detail=agent_response.get("reason"))

    # 2. Simulated Payment
    payment_reference = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    
    # 3. Create the Booking record
    new_booking = Booking(
        user_id=current_user.id,
        ticket_category_id=booking_in.ticket_category_id,
        quantity=booking_in.quantity,
        total_price=agent_response.get("total_price"),
        status="confirmed",
        payment_reference=payment_reference
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    # 4. Ask TicketAgent to generate the QR codes
    ticket_response = bus.send_message(
        db=db, sender="BookingRouter", receiver="TicketAgent", 
        performative="REQUEST", 
        content={"action": "issue_tickets", "booking_id": new_booking.id, "quantity": booking_in.quantity},
        conversation_id=conversation_id
    )
    
    # 5. Notify the user
    bus.send_message(
        db=db, sender="BookingRouter", receiver="NotificationAgent", 
        performative="INFORM", 
        content={"message": f"Booking confirmed! Payment Ref: {payment_reference}"},
        conversation_id=conversation_id
    )

    db.refresh(new_booking)
    return new_booking
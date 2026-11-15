from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models.hire import HireRequest
from app.models.user import User
from app.schemas.hire import HireRequestCreate, HireRequestResponse
from app.core.deps import get_current_user
from app.agents.bus import bus

# --- EXPLICITLY IMPORT THE AGENTS SO THEY REGISTER WITH THE BUS ---
from app.agents.venue_agent import venue_agent
# ------------------------------------------------------------------

router = APIRouter()

@router.post("/", response_model=HireRequestResponse)
def request_hire(
    hire_in: HireRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation_id = str(uuid.uuid4())
    
    # Ask VenueAgent for a decision
    response = bus.send_message(
        db=db, sender="HireRouter", receiver="VenueAgent",
        performative="REQUEST",
        content={
            "action": "request_hire",
            "venue_id": hire_in.venue_id,
            "start_time": hire_in.start_time.isoformat(),
            "end_time": hire_in.end_time.isoformat(),
            "guest_count": hire_in.guest_count
        },
        conversation_id=conversation_id
    )

    # Check if the agent actually responded
    if response is None:
        raise HTTPException(status_code=500, detail="VenueAgent failed to respond. Check the logs.")

    if response.get("status") == "REFUSE":
        raise HTTPException(status_code=400, detail=response.get("reason"))
    elif response.get("status") == "PROPOSE":
        # Return alternatives to the user
        raise HTTPException(status_code=409, detail={
            "message": response.get("reason"),
            "alternatives": response.get("alternatives")
        })

    # If AGREE, save the hire request
    new_hire = HireRequest(
        user_id=current_user.id,
        venue_id=hire_in.venue_id,
        start_time=hire_in.start_time,
        end_time=hire_in.end_time,
        purpose=hire_in.purpose,
        guest_count=hire_in.guest_count,
        status="approved", # Auto-approved for routine requests
        quoted_price=response.get("price")
    )
    db.add(new_hire)
    db.commit()
    db.refresh(new_hire)
    return new_hire
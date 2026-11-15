from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.event import Event, TicketCategory
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.message_log import MessageLog
from app.models.user import User
from app.core.deps import require_role

router = APIRouter()

@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    # Calculate total revenue and tickets sold
    total_revenue = db.query(func.sum(Booking.total_price)).filter(Booking.status == "confirmed").scalar() or 0
    tickets_sold = db.query(func.sum(Booking.quantity)).filter(Booking.status == "confirmed").scalar() or 0
    total_checkins = db.query(Ticket).filter(Ticket.is_admitted == True).count()

    return {
        "total_revenue_cents": total_revenue,
        "tickets_sold": tickets_sold,
        "total_checkins": total_checkins
    }

@router.get("/logs")
def get_agent_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    # Fetch the latest 50 messages exchanged between agents
    logs = db.query(MessageLog).order_by(MessageLog.timestamp.desc()).limit(50).all()
    return [
        {
            "id": log.id,
            "conversation_id": log.conversation_id,
            "sender": log.sender,
            "receiver": log.receiver,
            "performative": log.performative,
            "content": log.content,
            "time": log.timestamp
        }
        for log in logs
    ]
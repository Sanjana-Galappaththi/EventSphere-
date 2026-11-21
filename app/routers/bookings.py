import io, uuid
import qrcode
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from app.templates_config import templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.security import get_current_user, require_user
from app.agents.message_bus import MessageBus, make_msg

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.get("", response_class=HTMLResponse)
async def my_bookings(request: Request, db: Session = Depends(get_db),
                       user: models.User = Depends(require_user)):
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id
    ).order_by(models.Booking.created_at.desc()).all()
    return templates.TemplateResponse("bookings/list.html", {
        "request": request, "bookings": bookings, "user": user
    })

@router.post("/book")
async def book_tickets(
    request: Request,
    ticket_category_id: int = Form(...), quantity: int = Form(...),
    db: Session = Depends(get_db), user: models.User = Depends(require_user)
):
    conv_id = str(uuid.uuid4())
    result = await MessageBus.publish(make_msg(
        "API", "BookingAgent", "REQUEST",
        {"action": "book_tickets", "user_id": user.id,
         "ticket_category_id": ticket_category_id, "quantity": quantity},
        conv_id
    ), db)

    # Notify user
    if result.get("performative") == "INFORM":
        await MessageBus.publish(result, db)
        event_id = db.query(models.TicketCategory).filter(
            models.TicketCategory.id == ticket_category_id
        ).first().event_id
        return RedirectResponse(f"/bookings?booked=1", status_code=302)
    else:
        reason = result.get("content", {}).get("reason", "Booking failed.")
        cat = db.query(models.TicketCategory).filter(
            models.TicketCategory.id == ticket_category_id
        ).first()
        event = cat.event if cat else None
        raise HTTPException(400, detail=reason)

@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int, request: Request,
    db: Session = Depends(get_db), user: models.User = Depends(require_user)
):
    conv_id = str(uuid.uuid4())
    result = await MessageBus.publish(make_msg(
        "API", "BookingAgent", "REQUEST",
        {"action": "cancel_booking", "booking_id": booking_id, "user_id": user.id},
        conv_id
    ), db)

    if result.get("performative") == "AGREE":
        return RedirectResponse("/bookings?cancelled=1", status_code=302)
    else:
        raise HTTPException(400, detail=result.get("content", {}).get("reason", "Cancel failed."))

@router.get("/ticket/{ticket_id}/qr")
async def ticket_qr(ticket_id: int, request: Request, db: Session = Depends(get_db),
                     user: models.User = Depends(require_user)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket or ticket.booking.user_id != user.id:
        raise HTTPException(404)
    img = qrcode.make(ticket.qr_code)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@router.get("/ticket/{ticket_id}", response_class=HTMLResponse)
async def ticket_view(ticket_id: int, request: Request, db: Session = Depends(get_db),
                       user: models.User = Depends(require_user)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket or ticket.booking.user_id != user.id:
        raise HTTPException(404)
    return templates.TemplateResponse("bookings/ticket.html", {
        "request": request, "ticket": ticket, "user": user
    })

@router.post("/waitlist")
async def join_waitlist(
    request: Request,
    ticket_category_id: int = Form(...), quantity: int = Form(1),
    db: Session = Depends(get_db), user: models.User = Depends(require_user)
):
    conv_id = str(uuid.uuid4())
    result = await MessageBus.publish(make_msg(
        "API", "WaitlistAgent", "REQUEST",
        {"action": "join_waitlist", "user_id": user.id,
         "ticket_category_id": ticket_category_id, "quantity": quantity},
        conv_id
    ), db)
    cat = db.query(models.TicketCategory).filter(
        models.TicketCategory.id == ticket_category_id
    ).first()
    return RedirectResponse(f"/events/{cat.event_id}?waitlisted=1", status_code=302)

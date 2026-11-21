import json, uuid
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from app.database import get_db
from app import models
from app.security import get_current_user, require_admin
from app.agents.message_bus import MessageBus, make_msg

router = APIRouter(prefix="/events", tags=["events"])

@router.get("", response_class=HTMLResponse)
async def list_events(
    request: Request,
    q: str = "", category: str = "",
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    query = db.query(models.Event).filter(models.Event.status == models.EventStatus.published)
    if q:
        query = query.filter(models.Event.title.ilike(f"%{q}%"))
    if category:
        query = query.filter(models.Event.category == category)
    events = query.order_by(models.Event.start_time).all()
    categories = db.query(models.Event.category).distinct().all()
    return templates.TemplateResponse("events/list.html", {
        "request": request, "events": events, "user": user,
        "q": q, "category": category,
        "categories": [c[0] for c in categories]
    })

@router.get("/new", response_class=HTMLResponse)
async def new_event_form(request: Request, db: Session = Depends(get_db),
                          user: models.User = Depends(require_admin)):
    venues = db.query(models.Venue).all()
    return templates.TemplateResponse("events/form.html", {
        "request": request, "venues": venues, "user": user, "event": None
    })

@router.post("/new")
async def create_event(
    request: Request,
    title: str = Form(...), category: str = Form(...), venue_id: int = Form(...),
    start_time: str = Form(...), end_time: str = Form(...), description: str = Form(""),
    action: str = Form("draft"),
    tc_names: List[str] = Form([]), tc_prices: List[str] = Form([]), tc_quantities: List[str] = Form([]),
    db: Session = Depends(get_db), user: models.User = Depends(require_admin)
):
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    # Validate via VenueAgent
    conv_id = str(uuid.uuid4())
    result = await MessageBus.publish(make_msg(
        "API", "VenueAgent", "REQUEST",
        {"action": "check_slot", "venue_id": venue_id,
         "start_time": start_dt.isoformat(), "end_time": end_dt.isoformat()},
        conv_id
    ), db)

    if result.get("performative") == "REFUSE":
        venues = db.query(models.Venue).all()
        return templates.TemplateResponse("events/form.html", {
            "request": request, "venues": venues, "user": user, "event": None,
            "error": result["content"].get("reason", "Venue not available")
        })

    # Validate total tickets <= venue capacity
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    total_tickets = sum(int(q) for q in tc_quantities if q)
    if total_tickets > venue.capacity:
        venues = db.query(models.Venue).all()
        return templates.TemplateResponse("events/form.html", {
            "request": request, "venues": venues, "user": user, "event": None,
            "error": f"Total tickets ({total_tickets}) cannot exceed venue capacity ({venue.capacity})."
        })

    status = models.EventStatus.published if action == "publish" else models.EventStatus.draft
    event = models.Event(
        title=title, category=category, venue_id=venue_id,
        start_time=start_dt, end_time=end_dt, description=description, status=status
    )
    db.add(event)
    db.flush()

    for name, price, qty in zip(tc_names, tc_prices, tc_quantities):
        if name and price and qty:
            tc = models.TicketCategory(
                event_id=event.id, name=name,
                price=float(price), quantity=int(qty)
            )
            db.add(tc)
    db.commit()
    return RedirectResponse(f"/events/{event.id}", status_code=302)

@router.get("/{event_id}", response_class=HTMLResponse)
async def event_detail(event_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    user_bookings = []
    if user:
        user_bookings = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.event_id == event_id,
            models.Booking.status == models.BookingStatus.confirmed
        ).all()
    return templates.TemplateResponse("events/detail.html", {
        "request": request, "event": event, "user": user, "user_bookings": user_bookings
    })

@router.post("/{event_id}/publish")
async def publish_event(event_id: int, request: Request, db: Session = Depends(get_db),
                         user: models.User = Depends(require_admin)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if event:
        event.status = models.EventStatus.published
        db.commit()
    return RedirectResponse(f"/events/{event_id}", status_code=302)

@router.post("/{event_id}/cancel")
async def cancel_event(event_id: int, request: Request, db: Session = Depends(get_db),
                        user: models.User = Depends(require_admin)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(404)
    event.status = models.EventStatus.cancelled
    db.commit()
    # Notify BookingAgent to process refunds
    await MessageBus.publish(make_msg(
        "API", "BookingAgent", "INFORM",
        {"action": "event_cancelled", "event_id": event_id},
        str(uuid.uuid4())
    ), db)
    return RedirectResponse(f"/events/{event_id}", status_code=302)

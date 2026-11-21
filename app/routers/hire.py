import json, uuid
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app import models
from app.security import get_current_user, require_user, require_admin
from app.agents.message_bus import MessageBus, make_msg

router = APIRouter(prefix="/hire", tags=["hire"])

@router.get("", response_class=HTMLResponse)
async def hire_form(request: Request, db: Session = Depends(get_db),
                     user: models.User = Depends(require_user)):
    venues = db.query(models.Venue).filter(models.Venue.is_hireable == True).all()
    my_requests = db.query(models.HireRequest).filter(
        models.HireRequest.user_id == user.id
    ).order_by(models.HireRequest.created_at.desc()).all()
    return templates.TemplateResponse("hire/form.html", {
        "request": request, "venues": venues, "user": user,
        "my_requests": my_requests
    })

@router.post("/request")
async def submit_hire_request(
    request: Request,
    venue_id: int = Form(...), start_time: str = Form(...), end_time: str = Form(...),
    purpose: str = Form(...), guest_count: int = Form(...),
    db: Session = Depends(get_db), user: models.User = Depends(require_user)
):
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except Exception:
        return RedirectResponse("/hire?error=Invalid+date+or+time+format", status_code=303)

    if end_dt <= start_dt:
        return RedirectResponse("/hire?error=End+time+must+be+after+start+time", status_code=303)

    hire_req = models.HireRequest(
        user_id=user.id, venue_id=venue_id,
        start_time=start_dt, end_time=end_dt,
        purpose=purpose, guest_count=guest_count,
        status=models.HireStatus.pending
    )
    db.add(hire_req)
    db.commit()
    db.refresh(hire_req)

    conv_id = str(uuid.uuid4())
    result = await MessageBus.publish(make_msg(
        "API", "VenueAgent", "REQUEST",
        {"action": "hire_request", "venue_id": venue_id,
         "start_time": start_dt.isoformat(), "end_time": end_dt.isoformat(),
         "guest_count": guest_count, "hire_request_id": hire_req.id},
        conv_id
    ), db)

    # Dispatch agent response to NotificationAgent if applicable
    if result and result.get("receiver") == "NotificationAgent":
        await MessageBus.publish(result, db)

    return RedirectResponse("/hire?submitted=1", status_code=303)

@router.get("/admin", response_class=HTMLResponse)
async def admin_hire_list(request: Request, db: Session = Depends(get_db),
                           user: models.User = Depends(require_admin)):
    requests = db.query(models.HireRequest).order_by(
        models.HireRequest.created_at.desc()
    ).all()
    return templates.TemplateResponse("hire/admin.html", {
        "request": request, "hire_requests": requests, "user": user
    })

@router.post("/{hire_id}/approve")
async def approve_hire(hire_id: int, request: Request, db: Session = Depends(get_db),
                        user: models.User = Depends(require_admin)):
    req = db.query(models.HireRequest).filter(models.HireRequest.id == hire_id).first()
    if req:
        req.status = models.HireStatus.confirmed
        notif = models.Notification(
            user_id=req.user_id,
            message=f"✅ Your venue hire request for '{req.venue.name}' has been approved by admin."
        )
        db.add(notif)
        db.commit()
    return RedirectResponse("/hire/admin", status_code=302)

@router.post("/{hire_id}/reject")
async def reject_hire(hire_id: int, request: Request, note: str = Form(""),
                       db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    req = db.query(models.HireRequest).filter(models.HireRequest.id == hire_id).first()
    if req:
        req.status = models.HireStatus.rejected
        req.admin_note = note
        notif = models.Notification(
            user_id=req.user_id,
            message=f"❌ Your venue hire request was rejected. Reason: {note or 'No reason given.'}"
        )
        db.add(notif)
        db.commit()
    return RedirectResponse("/hire/admin", status_code=302)

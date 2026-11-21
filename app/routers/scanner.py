import uuid
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from app.templates_config import templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.security import require_staff_or_admin
from app.agents.message_bus import MessageBus, make_msg

router = APIRouter(prefix="/scanner", tags=["scanner"])

@router.get("", response_class=HTMLResponse)
async def scanner_page(request: Request, db: Session = Depends(get_db),
                        user: models.User = Depends(require_staff_or_admin)):
    events = db.query(models.Event).filter(
        models.Event.status == models.EventStatus.published
    ).order_by(models.Event.start_time).all()
    return templates.TemplateResponse("scanner/scan.html", {
        "request": request, "user": user, "events": events
    })

@router.post("/scan")
async def scan_ticket(
    request: Request,
    qr_code: str = Form(...), event_id: str = Form(""),
    db: Session = Depends(get_db), user: models.User = Depends(require_staff_or_admin)
):
    conv_id = str(uuid.uuid4())
    result = await MessageBus.publish(make_msg(
        "API", "TicketAgent", "REQUEST",
        {"action": "scan_ticket", "qr_code": qr_code.strip(),
         "event_id": event_id if event_id else None},
        conv_id
    ), db)
    content = result.get("content", {})
    return JSONResponse({
        "success": result.get("performative") == "AGREE",
        "result": content.get("result", "error"),
        "reason": content.get("reason", ""),
        "attendee": content.get("attendee", ""),
        "event": content.get("event", ""),
        "category": content.get("category", "")
    })

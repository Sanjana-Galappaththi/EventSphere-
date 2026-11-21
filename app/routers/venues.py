from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templates_config import templates
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import models
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/venues", tags=["venues"])

@router.get("", response_class=HTMLResponse)
async def list_venues(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    venues = db.query(models.Venue).all()
    return templates.TemplateResponse("venues/list.html", {
        "request": request, "venues": venues, "user": user
    })

@router.get("/new", response_class=HTMLResponse)
async def new_venue_form(request: Request, db: Session = Depends(get_db),
                          user: models.User = Depends(require_admin)):
    return templates.TemplateResponse("venues/form.html", {"request": request, "user": user, "venue": None})

@router.post("/new")
async def create_venue(
    request: Request,
    name: str = Form(...), location: str = Form(...), capacity: int = Form(...),
    description: str = Form(""), image_url: str = Form(""),
    hourly_hire_rate: float = Form(...), is_hireable: bool = Form(False),
    db: Session = Depends(get_db), user: models.User = Depends(require_admin)
):
    venue = models.Venue(
        name=name, location=location, capacity=capacity,
        description=description, image_url=image_url or None,
        hourly_hire_rate=hourly_hire_rate, is_hireable=is_hireable
    )
    db.add(venue)
    db.commit()
    return RedirectResponse("/venues", status_code=302)

@router.get("/{venue_id}", response_class=HTMLResponse)
async def venue_detail(venue_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(404, "Venue not found")
    return templates.TemplateResponse("venues/detail.html", {
        "request": request, "venue": venue, "user": user
    })

@router.get("/{venue_id}/edit", response_class=HTMLResponse)
async def edit_venue_form(venue_id: int, request: Request, db: Session = Depends(get_db),
                           user: models.User = Depends(require_admin)):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(404, "Venue not found")
    return templates.TemplateResponse("venues/form.html", {
        "request": request, "venue": venue, "user": user
    })

@router.post("/{venue_id}/edit")
async def update_venue(
    venue_id: int, request: Request,
    name: str = Form(...), location: str = Form(...), capacity: int = Form(...),
    description: str = Form(""), image_url: str = Form(""),
    hourly_hire_rate: float = Form(...), is_hireable: bool = Form(False),
    db: Session = Depends(get_db), user: models.User = Depends(require_admin)
):
    venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(404, "Venue not found")
    venue.name = name; venue.location = location; venue.capacity = capacity
    venue.description = description; venue.image_url = image_url or None
    venue.hourly_hire_rate = hourly_hire_rate; venue.is_hireable = is_hireable
    db.commit()
    return RedirectResponse(f"/venues/{venue_id}", status_code=302)

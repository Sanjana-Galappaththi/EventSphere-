from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, EventStatus, BookingStatus, HireStatus, TicketStatus

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    class Config:
        from_attributes = True

class VenueCreate(BaseModel):
    name: str
    location: str
    capacity: int
    description: Optional[str] = None
    image_url: Optional[str] = None
    hourly_hire_rate: float
    is_hireable: bool = True

class TicketCategoryCreate(BaseModel):
    name: str
    price: float
    quantity: int

class EventCreate(BaseModel):
    title: str
    category: str
    venue_id: int
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    ticket_categories: List[TicketCategoryCreate]

class BookingCreate(BaseModel):
    ticket_category_id: int
    quantity: int

class HireRequestCreate(BaseModel):
    venue_id: int
    start_time: datetime
    end_time: datetime
    purpose: str
    guest_count: int

class AgentMessageSchema(BaseModel):
    conversation_id: str
    sender: str
    receiver: str
    performative: str
    content: dict

class InboxMessage(BaseModel):
    sender: str
    performative: str
    content: dict
    conversation_id: str

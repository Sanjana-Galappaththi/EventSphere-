from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TicketCategoryCreate(BaseModel):
    name: str
    price: int  # In cents
    quantity: int

class EventCreate(BaseModel):
    title: str
    category: str
    venue_id: int
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    ticket_categories: List[TicketCategoryCreate]

class EventResponse(BaseModel):
    id: int
    title: str
    status: str
    venue_id: int
    class Config:
        from_attributes = True
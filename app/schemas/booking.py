from pydantic import BaseModel
from typing import List, Optional

class BookingRequest(BaseModel):
    ticket_category_id: int
    quantity: int

class TicketResponse(BaseModel):
    id: int
    qr_code: str
    is_admitted: bool

class BookingResponse(BaseModel):
    id: int
    quantity: int
    total_price: int
    status: str
    payment_reference: str
    tickets: List[TicketResponse]

    class Config:
        from_attributes = True
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class HireRequestCreate(BaseModel):
    venue_id: int
    start_time: datetime
    end_time: datetime
    purpose: str
    guest_count: int

class HireRequestResponse(BaseModel):
    id: int
    venue_id: int
    start_time: datetime
    end_time: datetime
    purpose: str
    guest_count: int
    status: str
    quoted_price: Optional[float] = None

    class Config:
        from_attributes = True

class HireAlternative(BaseModel):
    venue_name: str
    start_time: datetime
    end_time: datetime
    estimated_price: float
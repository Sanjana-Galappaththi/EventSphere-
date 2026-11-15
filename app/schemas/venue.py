from pydantic import BaseModel
from typing import Optional

class VenueCreate(BaseModel):
    name: str
    location: str
    capacity: int
    description: Optional[str] = None
    image_url: Optional[str] = None
    hourly_rate: float
    is_available_for_hire: bool = True

class VenueResponse(VenueCreate):
    id: int
    class Config:
        from_attributes = True
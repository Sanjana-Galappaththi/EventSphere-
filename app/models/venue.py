from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from app.database import Base

class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    description = Column(Text)
    image_url = Column(String)
    hourly_rate = Column(Float, nullable=False)
    is_available_for_hire = Column(Boolean, default=True)
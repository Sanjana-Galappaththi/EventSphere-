from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base

class HireRequest(Base):
    __tablename__ = "hire_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    purpose = Column(String, nullable=False)
    guest_count = Column(Integer, nullable=False)
    status = Column(String, default="pending") # pending, approved, rejected, escalated
    quoted_price = Column(Float)

    user = relationship("User")
    venue = relationship("Venue")
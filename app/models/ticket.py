from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    qr_code = Column(String, unique=True, index=True, nullable=False)
    is_admitted = Column(Boolean, default=False)
    admitted_at = Column(DateTime)

    booking = relationship("Booking", back_populates="tickets")
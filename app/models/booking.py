from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticket_category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)
    status = Column(String, default="confirmed") # confirmed, cancelled
    payment_reference = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    ticket_category = relationship("TicketCategory")
    tickets = relationship("Ticket", back_populates="booking")
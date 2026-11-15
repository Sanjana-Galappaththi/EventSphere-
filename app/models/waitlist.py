from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class Waitlist(Base):
    __tablename__ = "waitlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticket_category_id = Column(Integer, ForeignKey("ticket_categories.id"))
    status = Column(String, default="waiting") # waiting, offered, claimed
    offer_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
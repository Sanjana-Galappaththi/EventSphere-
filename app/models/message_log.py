from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.database import Base

class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, index=True)
    sender = Column(String)
    receiver = Column(String)
    performative = Column(String) # REQUEST, AGREE, REFUSE, PROPOSE, INFORM, FAILURE
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
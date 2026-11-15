from sqlalchemy.orm import Session
from app.models.message_log import MessageLog
from datetime import datetime

class MessageBus:
    def __init__(self):
        self.agents = {}
        
    def register_agent(self, agent_name: str, agent_instance):
        self.agents[agent_name] = agent_instance
        
    def send_message(self, db: Session, sender: str, receiver: str, performative: str, content: dict, conversation_id: str):
        # 1. Log the message to the database (Traceability requirement)
        log = MessageLog(
            conversation_id=conversation_id,
            sender=sender,
            receiver=receiver,
            performative=performative,
            content=str(content),
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        
        # 2. Deliver the message to the receiver agent if it exists
        if receiver in self.agents:
            return self.agents[receiver].receive_message(db, sender, performative, content, conversation_id)
        return None

# Global instance of the message bus
bus = MessageBus()
import json
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Any
from sqlalchemy.orm import Session
from app.models import AgentMessage

class MessageBus:
    """In-process message bus for agent communication."""
    _subscribers: Dict[str, List[Callable]] = {}

    @classmethod
    def subscribe(cls, agent_name: str, handler: Callable):
        if agent_name not in cls._subscribers:
            cls._subscribers[agent_name] = []
        cls._subscribers[agent_name].append(handler)

    @classmethod
    async def publish(cls, msg: dict, db: Session) -> dict:
        """Log message and deliver to subscriber."""
        # Persist to DB
        record = AgentMessage(
            conversation_id=msg.get("conversation_id", str(uuid.uuid4())),
            sender=msg["sender"],
            receiver=msg["receiver"],
            performative=msg["performative"],
            content=json.dumps(msg["content"])
        )
        db.add(record)
        db.commit()

        # Deliver
        receiver = msg["receiver"]
        if receiver in cls._subscribers:
            for handler in cls._subscribers[receiver]:
                try:
                    result = await handler(msg, db)
                    return result or {}
                except Exception as e:
                    return {"performative": "FAILURE", "content": {"error": str(e)}}
        return {"performative": "INFORM", "content": {"status": "no_handler"}}

def make_msg(sender: str, receiver: str, performative: str, content: dict, conv_id: str = None) -> dict:
    return {
        "sender": sender,
        "receiver": receiver,
        "performative": performative,
        "content": content,
        "conversation_id": conv_id or str(uuid.uuid4())
    }

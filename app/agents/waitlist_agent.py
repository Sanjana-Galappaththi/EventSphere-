from app.agents.base import BaseAgent
from app.agents.bus import bus
from app.models.waitlist import Waitlist # We need to create this model
from datetime import datetime, timedelta

class WaitlistAgent(BaseAgent):
    def __init__(self):
        super().__init__("WaitlistAgent")

    def receive_message(self, db, sender, performative, content, conversation_id):
        if performative == "INFORM" and content.get("action") == "seat_freed":
            # A seat was freed up. Find who is waiting.
            category_id = content.get("category_id")
            
            # Find the oldest active waitlist entry
            entry = db.query(Waitlist).filter(
                Waitlist.ticket_category_id == category_id,
                Waitlist.status == "waiting"
            ).order_by(Waitlist.created_at.asc()).first()

            if entry:
                # Offer the seat and hold it for 10 minutes
                entry.status = "offered"
                entry.offer_expires_at = datetime.utcnow() + timedelta(minutes=10)
                db.commit()

                # Notify the user
                bus.send_message(
                    db, sender="WaitlistAgent", receiver="NotificationAgent",
                    performative="INFORM",
                    content={"message": f"Good news! A seat is available. You have 10 minutes to claim it."},
                    conversation_id=conversation_id
                )
                return {"status": "AGREE", "message": "Seat offered to waitlist user"}
            
            return {"status": "INFORM", "message": "No one on waitlist"}

        return {"status": "REFUSE", "reason": "Unknown request"}

waitlist_agent = WaitlistAgent()
bus.register_agent("WaitlistAgent", waitlist_agent)
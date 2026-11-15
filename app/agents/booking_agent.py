from app.agents.base import BaseAgent
from app.agents.bus import bus
from app.models.event import TicketCategory

class BookingAgent(BaseAgent):
    def __init__(self):
        super().__init__("BookingAgent")

    def receive_message(self, db, sender, performative, content, conversation_id):
        if performative == "REQUEST" and content.get("action") == "reserve_tickets":
            category_id = content.get("category_id")
            quantity = content.get("quantity")

            # Rule 1: Max 6 tickets per booking
            if quantity > 6:
                return {"status": "REFUSE", "reason": "You can only book up to 6 tickets per transaction."}
            if quantity <= 0:
                return {"status": "REFUSE", "reason": "Quantity must be greater than 0."}

            # Rule 2: Concurrency control (Lock the row)
            # with_for_update() locks the row in the DB so no two requests can read it at the same time
            category = db.query(TicketCategory).filter(TicketCategory.id == category_id).with_for_update().first()
            
            if not category:
                return {"status": "FAILURE", "reason": "Ticket category not found."}

            # Rule 3: Check capacity
            if category.remaining < quantity:
                return {"status": "REFUSE", "reason": f"Only {category.remaining} tickets remaining."}

            # If we get here, we can reserve
            category.remaining -= quantity
            db.commit() # Save the new remaining amount immediately to release the lock

            return {
                "status": "AGREE", 
                "reason": "Tickets reserved successfully.",
                "total_price": category.price * quantity
            }
            
        return {"status": "REFUSE", "reason": "Unknown request"}

booking_agent = BookingAgent()
bus.register_agent("BookingAgent", booking_agent)
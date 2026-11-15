from app.agents.base import BaseAgent
from app.agents.bus import bus
from app.models.ticket import Ticket
from app.models.booking import Booking
from app.models.event import TicketCategory
from datetime import datetime
import uuid
import qrcode
import io
import base64

class TicketAgent(BaseAgent):
    def __init__(self):
        super().__init__("TicketAgent")

    def generate_qr_base64(self, data: str) -> str:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def receive_message(self, db, sender, performative, content, conversation_id):
        if performative == "REQUEST" and content.get("action") == "issue_tickets":
            booking_id = content.get("booking_id")
            quantity = content.get("quantity")
            
            tickets = []
            for _ in range(quantity):
                qr_code = str(uuid.uuid4())
                ticket = Ticket(
                    booking_id=booking_id,
                    qr_code=qr_code,
                    is_admitted=False
                )
                db.add(ticket)
                tickets.append(qr_code)
            
            db.commit()
            return {"status": "AGREE", "reason": "Tickets issued", "qr_codes": tickets}

        if performative == "REQUEST" and content.get("action") == "scan_ticket":
            qr_code = content.get("qr_code")
            event_id = content.get("event_id")
            
            # 1. Find the ticket
            ticket = db.query(Ticket).filter(Ticket.qr_code == qr_code).first()
            if not ticket:
                return {"status": "REFUSE", "reason": "Invalid ticket code."}
                
            # 2. Check if cancelled
            if ticket.booking.status == "cancelled":
                return {"status": "REFUSE", "reason": "Ticket has been cancelled."}
                
            # 3. Check if already admitted
            if ticket.is_admitted:
                return {"status": "REFUSE", "reason": "Ticket already used."}
                
            # 4. Check if it's the right event
            actual_event_id = ticket.booking.ticket_category.event_id
            if actual_event_id != event_id:
                return {"status": "REFUSE", "reason": "Wrong event for this ticket."}

            # 5. If all checks pass, admit them
            ticket.is_admitted = True
            ticket.admitted_at = datetime.utcnow()
            db.commit()

            return {"status": "AGREE", "reason": "Admit", "attendee": ticket.booking.user.full_name}

        return {"status": "REFUSE", "reason": "Unknown request"}

ticket_agent = TicketAgent()
bus.register_agent("TicketAgent", ticket_agent)
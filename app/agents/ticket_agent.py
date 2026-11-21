"""
TicketAgent — Goal: Admit each ticket exactly once.
Decisions:
  - Issue unique QR codes.
  - At the door: return admit / already_used / wrong_event / cancelled / outside_check_in_time.
  - Detect suspicious repeated scans (possible shared screenshots) — advanced feature.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
from app.agents.message_bus import MessageBus, make_msg

CHECK_IN_OPEN_BEFORE = timedelta(hours=2)
CHECK_IN_CLOSE_AFTER = timedelta(hours=1)
SUSPICIOUS_SCAN_THRESHOLD = 3  # flag if same code scanned 3+ times before admission

class TicketAgent:
    NAME = "TicketAgent"

    @classmethod
    def register(cls):
        MessageBus.subscribe(cls.NAME, cls.handle)

    @classmethod
    async def handle(cls, msg: dict, db: Session) -> dict:
        performative = msg["performative"]
        content = msg["content"]
        conv_id = msg.get("conversation_id", str(uuid.uuid4()))

        if performative == "REQUEST" and content.get("action") == "scan_ticket":
            return await cls.scan_ticket(content, conv_id, db)
        return make_msg(cls.NAME, msg["sender"], "FAILURE", {"error": "Unknown action"}, conv_id)

    @classmethod
    async def scan_ticket(cls, content: dict, conv_id: str, db: Session) -> dict:
        qr_code = content["qr_code"]
        event_id = content.get("event_id")

        ticket = db.query(models.Ticket).filter(models.Ticket.qr_code == qr_code).first()

        if not ticket:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"result": "invalid", "reason": "Ticket not found. Invalid QR code."}, conv_id)

        # Increment scan count (for suspicious scan detection)
        ticket.scan_count += 1
        db.commit()

        booking = ticket.booking
        event = booking.event
        now = datetime.utcnow()

        # Check event match
        if event_id and event.id != int(event_id):
            return make_msg(cls.NAME, "API", "REFUSE", {
                "result": "wrong_event",
                "reason": f"This ticket is for '{event.title}', not this event."
            }, conv_id)

        # Check cancelled
        if ticket.status == models.TicketStatus.cancelled:
            return make_msg(cls.NAME, "API", "REFUSE", {
                "result": "cancelled",
                "reason": "This ticket has been cancelled."
            }, conv_id)

        # Check already used
        if ticket.status == models.TicketStatus.used:
            # Suspicious scan detection
            if ticket.scan_count >= SUSPICIOUS_SCAN_THRESHOLD:
                return make_msg(cls.NAME, "API", "REFUSE", {
                    "result": "suspicious",
                    "reason": f"Ticket already used and scanned {ticket.scan_count} times. Possible fraudulent use."
                }, conv_id)
            return make_msg(cls.NAME, "API", "REFUSE", {
                "result": "already_used",
                "reason": f"Ticket already checked in at {ticket.checked_in_at.strftime('%H:%M on %d %b %Y')}."
            }, conv_id)

        # Check check-in window
        check_in_open = event.start_time - CHECK_IN_OPEN_BEFORE
        check_in_close = event.start_time + CHECK_IN_CLOSE_AFTER

        if now < check_in_open:
            return make_msg(cls.NAME, "API", "REFUSE", {
                "result": "too_early",
                "reason": f"Check-in opens at {check_in_open.strftime('%H:%M on %d %b %Y')}."
            }, conv_id)

        if now > check_in_close:
            return make_msg(cls.NAME, "API", "REFUSE", {
                "result": "outside_check_in_time",
                "reason": f"Check-in closed at {check_in_close.strftime('%H:%M on %d %b %Y')}."
            }, conv_id)

        # Admit ticket
        ticket.status = models.TicketStatus.used
        ticket.checked_in_at = now
        db.commit()

        return make_msg(cls.NAME, "API", "AGREE", {
            "result": "admitted",
            "ticket_id": ticket.id,
            "attendee": booking.user.name,
            "event": event.title,
            "category": booking.ticket_category.name,
            "checked_in_at": now.isoformat()
        }, conv_id)

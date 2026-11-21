"""
BookingAgent — Goal: Sell tickets fairly without overselling.
Decisions:
  - Accept or refuse ticket request (quantity limits, timing, capacity).
  - Calculate refund on cancellation.
  - Full refunds when event is cancelled.
  - Uses DB-level locking to prevent concurrent overselling.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app import models
from app.agents.message_bus import MessageBus, make_msg

MAX_TICKETS_PER_BOOKING = 6
FULL_REFUND_DAYS = 7   # full refund if cancelled 7+ days before event
PARTIAL_REFUND_PCT = 50  # 50% refund if cancelled within 7 days

class BookingAgent:
    NAME = "BookingAgent"

    @classmethod
    def register(cls):
        MessageBus.subscribe(cls.NAME, cls.handle)

    @classmethod
    async def handle(cls, msg: dict, db: Session) -> dict:
        performative = msg["performative"]
        content = msg["content"]
        conv_id = msg.get("conversation_id", str(uuid.uuid4()))

        if performative == "REQUEST" and content.get("action") == "book_tickets":
            return await cls.book_tickets(content, conv_id, db)
        elif performative == "REQUEST" and content.get("action") == "cancel_booking":
            return await cls.cancel_booking(content, conv_id, db)
        elif performative == "INFORM" and content.get("action") == "event_cancelled":
            return await cls.handle_event_cancelled(content, conv_id, db)
        return make_msg(cls.NAME, msg["sender"], "FAILURE", {"error": "Unknown action"}, conv_id)

    @classmethod
    async def book_tickets(cls, content: dict, conv_id: str, db: Session) -> dict:
        user_id = content["user_id"]
        ticket_category_id = content["ticket_category_id"]
        quantity = content["quantity"]

        if quantity > MAX_TICKETS_PER_BOOKING:
            return make_msg(cls.NAME, "API", "REFUSE", {
                "reason": f"Maximum {MAX_TICKETS_PER_BOOKING} tickets per booking."
            }, conv_id)

        if quantity < 1:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Quantity must be at least 1."}, conv_id)

        # Lock the row to prevent race conditions
        cat = db.execute(
            select(models.TicketCategory)
            .filter(models.TicketCategory.id == ticket_category_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not cat:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Ticket category not found."}, conv_id)

        available = cat.quantity - cat.sold
        if available < quantity:
            return make_msg(cls.NAME, "API", "REFUSE", {
                "reason": f"Only {available} ticket(s) available in this category."
            }, conv_id)

        event = db.query(models.Event).filter(models.Event.id == cat.event_id).first()
        if not event or event.status != models.EventStatus.published:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Event is not available for booking."}, conv_id)

        if event.start_time < datetime.utcnow():
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Cannot book tickets for past events."}, conv_id)

        # Deduct seats
        cat.sold += quantity
        total = cat.price * quantity
        payment_ref = f"PAY-{secrets.token_hex(8).upper()}"

        booking = models.Booking(
            user_id=user_id,
            event_id=cat.event_id,
            ticket_category_id=ticket_category_id,
            quantity=quantity,
            total_amount=total,
            payment_reference=payment_ref,
            status=models.BookingStatus.confirmed
        )
        db.add(booking)
        db.flush()

        # Issue tickets via TicketAgent
        tickets = []
        for _ in range(quantity):
            qr = secrets.token_urlsafe(32)
            t = models.Ticket(booking_id=booking.id, qr_code=qr)
            db.add(t)
            tickets.append(qr)
        db.commit()

        return make_msg(cls.NAME, "NotificationAgent", "INFORM", {
            "action": "booking_confirmed",
            "booking_id": booking.id,
            "user_id": user_id,
            "event_title": event.title,
            "quantity": quantity,
            "total": total,
            "payment_ref": payment_ref,
            "tickets": tickets
        }, conv_id)

    @classmethod
    async def cancel_booking(cls, content: dict, conv_id: str, db: Session) -> dict:
        booking_id = content["booking_id"]
        user_id = content["user_id"]

        booking = db.query(models.Booking).filter(
            models.Booking.id == booking_id,
            models.Booking.user_id == user_id
        ).first()

        if not booking:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Booking not found."}, conv_id)

        if booking.status == models.BookingStatus.cancelled:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Booking already cancelled."}, conv_id)

        event = booking.event
        days_until = (event.start_time - datetime.utcnow()).days

        if days_until >= FULL_REFUND_DAYS:
            refund = booking.total_amount
        else:
            refund = round(booking.total_amount * PARTIAL_REFUND_PCT / 100, 2)

        # Restore seats
        cat = db.query(models.TicketCategory).filter(
            models.TicketCategory.id == booking.ticket_category_id
        ).with_for_update().first()
        if cat:
            cat.sold = max(0, cat.sold - booking.quantity)

        # Cancel tickets
        for ticket in booking.tickets:
            ticket.status = models.TicketStatus.cancelled

        booking.status = models.BookingStatus.cancelled
        booking.cancelled_at = datetime.utcnow()
        booking.refund_amount = refund
        db.commit()

        # Notify waitlist
        from app.agents.message_bus import MessageBus
        await MessageBus.publish(make_msg(
            cls.NAME, "WaitlistAgent", "INFORM",
            {"action": "seats_released", "ticket_category_id": booking.ticket_category_id,
             "quantity": booking.quantity},
            conv_id
        ), db)

        return make_msg(cls.NAME, "API", "AGREE", {
            "booking_id": booking_id,
            "refund_amount": refund,
            "refund_policy": f"{'Full' if days_until >= FULL_REFUND_DAYS else f'{PARTIAL_REFUND_PCT}%'} refund "
                           f"({days_until} days until event)"
        }, conv_id)

    @classmethod
    async def handle_event_cancelled(cls, content: dict, conv_id: str, db: Session) -> dict:
        event_id = content["event_id"]
        bookings = db.query(models.Booking).filter(
            models.Booking.event_id == event_id,
            models.Booking.status == models.BookingStatus.confirmed
        ).all()

        for booking in bookings:
            booking.status = models.BookingStatus.cancelled
            booking.cancelled_at = datetime.utcnow()
            booking.refund_amount = booking.total_amount  # full refund
            for ticket in booking.tickets:
                ticket.status = models.TicketStatus.cancelled
            cat = db.query(models.TicketCategory).filter(
                models.TicketCategory.id == booking.ticket_category_id
            ).first()
            if cat:
                cat.sold = max(0, cat.sold - booking.quantity)

        db.commit()
        return make_msg(cls.NAME, "NotificationAgent", "INFORM", {
            "action": "bulk_refund_done",
            "event_id": event_id,
            "count": len(bookings)
        }, conv_id)

"""
WaitlistAgent — Goal: Pass freed seats to waiting customers.
Decisions:
  - Choose who gets released seats (FIFO).
  - Hold them for a time limit (15 minutes).
  - Expire unclaimed holds and re-offer them on a timer (proactive behaviour).
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
from app.agents.message_bus import MessageBus, make_msg

HOLD_DURATION = timedelta(minutes=15)

class WaitlistAgent:
    NAME = "WaitlistAgent"

    @classmethod
    def register(cls):
        MessageBus.subscribe(cls.NAME, cls.handle)

    @classmethod
    async def handle(cls, msg: dict, db: Session) -> dict:
        performative = msg["performative"]
        content = msg["content"]
        conv_id = msg.get("conversation_id", str(uuid.uuid4()))

        if performative == "INFORM" and content.get("action") == "seats_released":
            return await cls.offer_seats(content, conv_id, db)
        elif performative == "REQUEST" and content.get("action") == "join_waitlist":
            return await cls.join_waitlist(content, conv_id, db)
        elif performative == "REQUEST" and content.get("action") == "expire_sweep":
            return await cls.expire_sweep(conv_id, db)
        return make_msg(cls.NAME, msg["sender"], "FAILURE", {"error": "Unknown action"}, conv_id)

    @classmethod
    async def join_waitlist(cls, content: dict, conv_id: str, db: Session) -> dict:
        user_id = content["user_id"]
        ticket_category_id = content["ticket_category_id"]
        quantity = content["quantity"]

        # Check not already on waitlist
        existing = db.query(models.WaitlistEntry).filter(
            models.WaitlistEntry.user_id == user_id,
            models.WaitlistEntry.ticket_category_id == ticket_category_id,
            models.WaitlistEntry.status.in_([models.WaitlistStatus.waiting, models.WaitlistStatus.offered])
        ).first()
        if existing:
            return make_msg(cls.NAME, "API", "REFUSE",
                          {"reason": "Already on waitlist for this category."}, conv_id)

        entry = models.WaitlistEntry(
            user_id=user_id,
            ticket_category_id=ticket_category_id,
            quantity=quantity,
            status=models.WaitlistStatus.waiting
        )
        db.add(entry)
        db.commit()
        return make_msg(cls.NAME, "API", "AGREE",
                      {"message": "Added to waitlist.", "entry_id": entry.id}, conv_id)

    @classmethod
    async def offer_seats(cls, content: dict, conv_id: str, db: Session) -> dict:
        ticket_category_id = content["ticket_category_id"]
        seats_available = content["quantity"]

        # FIFO: get oldest waiting entry
        entries = db.query(models.WaitlistEntry).filter(
            models.WaitlistEntry.ticket_category_id == ticket_category_id,
            models.WaitlistEntry.status == models.WaitlistStatus.waiting
        ).order_by(models.WaitlistEntry.created_at).all()

        offered = 0
        for entry in entries:
            if offered >= seats_available:
                break
            if entry.quantity <= (seats_available - offered):
                entry.status = models.WaitlistStatus.offered
                entry.offered_at = datetime.utcnow()
                entry.offer_expires_at = datetime.utcnow() + HOLD_DURATION
                offered += entry.quantity

                # Notify user
                notif = models.Notification(
                    user_id=entry.user_id,
                    message=f"🎉 Seats available! You have {HOLD_DURATION.seconds // 60} minutes to complete your booking."
                )
                db.add(notif)
        db.commit()
        return make_msg(cls.NAME, "API", "INFORM",
                      {"offered_to": offered, "entries_updated": offered}, conv_id)

    @classmethod
    async def expire_sweep(cls, conv_id: str, db: Session) -> dict:
        """Proactive: called by APScheduler — expire old holds and re-offer."""
        now = datetime.utcnow()
        expired = db.query(models.WaitlistEntry).filter(
            models.WaitlistEntry.status == models.WaitlistStatus.offered,
            models.WaitlistEntry.offer_expires_at < now
        ).all()

        re_offer_counts = {}
        for entry in expired:
            entry.status = models.WaitlistStatus.expired
            cat_id = entry.ticket_category_id
            re_offer_counts[cat_id] = re_offer_counts.get(cat_id, 0) + entry.quantity
            # Notify user their offer expired
            notif = models.Notification(
                user_id=entry.user_id,
                message="⏰ Your seat hold has expired and been released to other waitlist members."
            )
            db.add(notif)
        db.commit()

        # Re-offer to next in line
        for cat_id, qty in re_offer_counts.items():
            await cls.offer_seats(
                {"ticket_category_id": cat_id, "quantity": qty},
                conv_id, db
            )

        return make_msg(cls.NAME, "Scheduler", "INFORM",
                      {"expired": len(expired), "re_offered": sum(re_offer_counts.values())}, conv_id)

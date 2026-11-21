"""
NotificationAgent — Goal: Tell the right person what affects them.
Decisions:
  - Turn events from other agents into user notifications.
  - Acts as listener for all agents (reactive to broadcast INFORM events).
"""
import uuid
from sqlalchemy.orm import Session
from app import models
from app.agents.message_bus import MessageBus, make_msg

class NotificationAgent:
    NAME = "NotificationAgent"

    @classmethod
    def register(cls):
        MessageBus.subscribe(cls.NAME, cls.handle)

    @classmethod
    async def handle(cls, msg: dict, db: Session) -> dict:
        content = msg["content"]
        conv_id = msg.get("conversation_id", str(uuid.uuid4()))
        action = content.get("action", "")
        performative = msg["performative"]

        message_text = None
        user_id = content.get("user_id")

        if action == "booking_confirmed":
            message_text = (
                f"✅ Booking confirmed! {content.get('quantity')} ticket(s) for "
                f"'{content.get('event_title')}'. Ref: {content.get('payment_ref')}. "
                f"Total: ${content.get('total', 0):.2f}"
            )
        elif action == "bulk_refund_done":
            return make_msg(cls.NAME, msg["sender"], "INFORM",
                          {"status": "bulk_notification_sent"}, conv_id)
        elif performative == "AGREE" and content.get("hire_request_id"):
            hr_id = content.get("hire_request_id")
            req = db.query(models.HireRequest).filter(models.HireRequest.id == hr_id).first()
            if req:
                user_id = req.user_id
                message_text = (
                    f"✅ Venue hire confirmed for '{req.venue.name}'! Total: ${content.get('total_price', 0):.2f} "
                    f"({'Weekend rate (1.5x)' if content.get('is_weekend') else 'Standard rate'})."
                )
        elif performative == "PROPOSE" and content.get("hire_request_id"):
            hr_id = content.get("hire_request_id")
            req = db.query(models.HireRequest).filter(models.HireRequest.id == hr_id).first()
            if req:
                user_id = req.user_id
                alts = content.get("alternatives", [])
                if alts:
                    alt_text = "; ".join([f"{a['start_time'].replace('T', ' ')}" for a in alts[:2]])
                    message_text = (
                        f"ℹ️ Hire slot clashed. VenueAgent proposed alternative dates: {alt_text}. "
                        f"Escalated to admin for review."
                    )
                else:
                    message_text = (
                        f"⚠️ Hire request escalated to admin for review (guest count: {req.guest_count}, "
                        f"exceeds 90% capacity)."
                    )
        elif performative == "REFUSE" and content.get("hire_request_id"):
            hr_id = content.get("hire_request_id")
            req = db.query(models.HireRequest).filter(models.HireRequest.id == hr_id).first()
            if req:
                user_id = req.user_id
            reason = content.get("reason", "Hire request could not be processed.")
            message_text = f"❌ Venue hire request refused: {reason}"
        elif performative == "REFUSE":
            reason = content.get("reason", "Request refused")
            if user_id:
                message_text = f"❌ Request refused: {reason}"
        elif action == "event_cancelled_notify":
            user_id = content.get("user_id")
            message_text = (
                f"⚠️ Event '{content.get('event_title')}' has been cancelled. "
                f"Full refund of ${content.get('refund', 0):.2f} issued."
            )

        if message_text and user_id:
            notif = models.Notification(user_id=user_id, message=message_text)
            db.add(notif)
            db.commit()

        return make_msg(cls.NAME, msg["sender"], "INFORM",
                      {"status": "notification_sent"}, conv_id)

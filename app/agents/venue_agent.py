"""
VenueAgent — Goal: Keep every venue's calendar free of clashes.
Decisions:
  - Accept or refuse an event time slot (with 30-min turnaround buffer).
  - Confirm, escalate or counter-propose a private hire.
  - Price a hire (hourly rate; 1.5x weekend/peak surcharge for advanced feature).
  - Guest count <= venue capacity → auto-confirm; else escalate.
"""
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app import models
from app.agents.message_bus import MessageBus, make_msg

TURNAROUND_BUFFER = timedelta(minutes=30)
MAX_AUTO_GUEST_RATIO = 0.9  # auto-confirm if guests <= 90% of capacity

class VenueAgent:
    NAME = "VenueAgent"

    @classmethod
    def register(cls):
        MessageBus.subscribe(cls.NAME, cls.handle)

    @classmethod
    async def handle(cls, msg: dict, db: Session) -> dict:
        performative = msg["performative"]
        content = msg["content"]
        conv_id = msg.get("conversation_id", str(uuid.uuid4()))

        if performative == "REQUEST" and content.get("action") == "check_slot":
            return await cls.check_slot(content, conv_id, db)
        elif performative == "REQUEST" and content.get("action") == "hire_request":
            return await cls.handle_hire(content, conv_id, db)
        elif performative == "REQUEST" and content.get("action") == "get_alternatives":
            return await cls.get_alternatives(content, conv_id, db)
        return make_msg(cls.NAME, msg["sender"], "FAILURE", {"error": "Unknown action"}, conv_id)

    @classmethod
    async def check_slot(cls, content: dict, conv_id: str, db: Session) -> dict:
        venue_id = content["venue_id"]
        start = datetime.fromisoformat(content["start_time"])
        end = datetime.fromisoformat(content["end_time"])
        exclude_event_id = content.get("exclude_event_id")

        venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
        if not venue:
            return make_msg(cls.NAME, "BookingAgent", "REFUSE",
                          {"reason": "Venue not found"}, conv_id)

        # Check for clashes with buffer
        buffered_start = start - TURNAROUND_BUFFER
        buffered_end = end + TURNAROUND_BUFFER

        query = db.query(models.Event).filter(
            models.Event.venue_id == venue_id,
            models.Event.status != models.EventStatus.cancelled,
            models.Event.start_time < buffered_end,
            models.Event.end_time > buffered_start
        )
        if exclude_event_id:
            query = query.filter(models.Event.id != exclude_event_id)

        clash = query.first()
        if clash:
            return make_msg(cls.NAME, "BookingAgent", "REFUSE", {
                "reason": f"Venue clash with event '{clash.title}' "
                          f"({clash.start_time.isoformat()} - {clash.end_time.isoformat()}). "
                          f"30-minute turnaround buffer required."
            }, conv_id)

        return make_msg(cls.NAME, "BookingAgent", "AGREE",
                      {"venue_id": venue_id, "slot": "available"}, conv_id)

    @classmethod
    async def handle_hire(cls, content: dict, conv_id: str, db: Session) -> dict:
        venue_id = content["venue_id"]
        start = datetime.fromisoformat(content["start_time"])
        end = datetime.fromisoformat(content["end_time"])
        guest_count = content["guest_count"]
        hire_request_id = content.get("hire_request_id")

        venue = db.query(models.Venue).filter(models.Venue.id == venue_id).first()
        if not venue:
            return make_msg(cls.NAME, "NotificationAgent", "REFUSE",
                          {"reason": "Venue not found"}, conv_id)

        if not venue.is_hireable:
            if hire_request_id:
                req = db.query(models.HireRequest).filter(models.HireRequest.id == hire_request_id).first()
                if req:
                    req.status = models.HireStatus.rejected
                    req.admin_note = f"Venue '{venue.name}' is not open for private hire."
                    db.commit()
            return make_msg(cls.NAME, "NotificationAgent", "REFUSE", {
                "hire_request_id": hire_request_id,
                "reason": f"Venue '{venue.name}' is not available for private hire."
            }, conv_id)

        # Check capacity
        if guest_count > venue.capacity:
            if hire_request_id:
                req = db.query(models.HireRequest).filter(models.HireRequest.id == hire_request_id).first()
                if req:
                    req.status = models.HireStatus.rejected
                    req.admin_note = f"Guest count ({guest_count}) exceeds venue capacity ({venue.capacity})."
                    db.commit()
            return make_msg(cls.NAME, "NotificationAgent", "REFUSE", {
                "hire_request_id": hire_request_id,
                "reason": f"Guest count {guest_count} exceeds venue capacity {venue.capacity}."
            }, conv_id)

        # Check slot availability (with buffer)
        buffered_start = start - TURNAROUND_BUFFER
        buffered_end = end + TURNAROUND_BUFFER

        event_clash = db.query(models.Event).filter(
            models.Event.venue_id == venue_id,
            models.Event.status != models.EventStatus.cancelled,
            models.Event.start_time < buffered_end,
            models.Event.end_time > buffered_start
        ).first()

        hire_clash = db.query(models.HireRequest).filter(
            models.HireRequest.venue_id == venue_id,
            models.HireRequest.status.in_([models.HireStatus.confirmed, models.HireStatus.pending]),
            models.HireRequest.start_time < buffered_end,
            models.HireRequest.end_time > buffered_start
        )
        if hire_request_id:
            hire_clash = hire_clash.filter(models.HireRequest.id != hire_request_id)
        hire_clash = hire_clash.first()

        if event_clash or hire_clash:
            # Get alternatives
            alternatives = await cls._find_alternatives(venue_id, start, end, db)
            if hire_request_id:
                req = db.query(models.HireRequest).filter(models.HireRequest.id == hire_request_id).first()
                if req:
                    req.status = models.HireStatus.escalated
                    req.alternatives = json.dumps(alternatives)
                    req.admin_note = "Slot clashed with an existing schedule (30m buffer enforced). Alternatives proposed."
                    db.commit()
            return make_msg(cls.NAME, "NotificationAgent", "PROPOSE", {
                "hire_request_id": hire_request_id,
                "reason": "Requested slot is not available. Turnaround buffer or event clash.",
                "alternatives": alternatives
            }, conv_id)

        # Calculate price (weekend surcharge = advanced feature)
        hours = (end - start).total_seconds() / 3600
        is_weekend = start.weekday() >= 5
        rate = venue.hourly_hire_rate * (1.5 if is_weekend else 1.0)
        total_price = round(hours * rate, 2)

        # Auto-confirm if guest ratio is acceptable
        if guest_count <= venue.capacity * MAX_AUTO_GUEST_RATIO:
            status = models.HireStatus.confirmed
            performative = "AGREE"
            admin_note = None
        else:
            status = models.HireStatus.escalated
            performative = "PROPOSE"
            admin_note = "Escalated for admin review (guest count exceeds 90% capacity)."

        if hire_request_id:
            req = db.query(models.HireRequest).filter(models.HireRequest.id == hire_request_id).first()
            if req:
                req.status = status
                req.total_price = total_price
                if admin_note:
                    req.admin_note = admin_note
                db.commit()

        return make_msg(cls.NAME, "NotificationAgent", performative, {
            "hire_request_id": hire_request_id,
            "total_price": total_price,
            "status": status.value,
            "hours": hours,
            "rate": rate,
            "is_weekend": is_weekend
        }, conv_id)

    @classmethod
    async def _find_alternatives(cls, venue_id: int, start: datetime, end: datetime, db: Session) -> list:
        duration = end - start
        alternatives = []
        # Try next 3 available slots in next 7 days
        candidate = start + timedelta(days=1)
        for _ in range(7):
            test_end = candidate + duration
            clash_e = db.query(models.Event).filter(
                models.Event.venue_id == venue_id,
                models.Event.status != models.EventStatus.cancelled,
                models.Event.start_time < test_end + TURNAROUND_BUFFER,
                models.Event.end_time > candidate - TURNAROUND_BUFFER
            ).first()
            clash_h = db.query(models.HireRequest).filter(
                models.HireRequest.venue_id == venue_id,
                models.HireRequest.status.in_([models.HireStatus.confirmed, models.HireStatus.pending]),
                models.HireRequest.start_time < test_end + TURNAROUND_BUFFER,
                models.HireRequest.end_time > candidate - TURNAROUND_BUFFER
            ).first()
            if not clash_e and not clash_h:
                alternatives.append({
                    "start_time": candidate.isoformat(),
                    "end_time": test_end.isoformat()
                })
                if len(alternatives) >= 3:
                    break
            candidate += timedelta(days=1)
        return alternatives

    @classmethod
    async def get_alternatives(cls, content: dict, conv_id: str, db: Session) -> dict:
        alts = await cls._find_alternatives(
            content["venue_id"],
            datetime.fromisoformat(content["start_time"]),
            datetime.fromisoformat(content["end_time"]),
            db
        )
        return make_msg(cls.NAME, "NotificationAgent", "INFORM", {"alternatives": alts}, conv_id)

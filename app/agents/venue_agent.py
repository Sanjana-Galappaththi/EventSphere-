from app.agents.base import BaseAgent
from app.agents.bus import bus
from app.models.event import Event
from app.models.venue import Venue
from app.models.hire import HireRequest
from datetime import datetime, timedelta

class VenueAgent(BaseAgent):
    def __init__(self):
        super().__init__("VenueAgent")

    def receive_message(self, db, sender, performative, content, conversation_id):
        action = content.get("action")

        if action == "check_availability":
            venue_id = content.get("venue_id")
            start_time = datetime.fromisoformat(content.get("start_time"))
            end_time = datetime.fromisoformat(content.get("end_time"))
            
            buffer = timedelta(hours=2)
            existing_events = db.query(Event).filter(Event.venue_id == venue_id).all()
            
            for event in existing_events:
                if start_time < (event.end_time + buffer) and end_time > (event.start_time - buffer):
                    return {
                        "status": "REFUSE", 
                        "reason": f"Clashes with event '{event.title}' (including 2h buffer)."
                    }
            return {"status": "AGREE", "reason": "Venue is free."}

        if action == "request_hire":
            venue_id = content.get("venue_id")
            start_time = datetime.fromisoformat(content.get("start_time"))
            end_time = datetime.fromisoformat(content.get("end_time"))
            guest_count = content.get("guest_count")
            
            venue = db.query(Venue).filter(Venue.id == venue_id).first()
            if not venue:
                return {"status": "REFUSE", "reason": "Venue does not exist."}
                
            if guest_count > venue.capacity:
                return {"status": "REFUSE", "reason": f"Guest count exceeds capacity ({venue.capacity})."}

            # Calculate hours and price
            duration_hours = (end_time - start_time).total_seconds() / 3600
            price = duration_hours * venue.hourly_rate
            
            # Check for clashes with events
            buffer = timedelta(hours=2)
            events = db.query(Event).filter(Event.venue_id == venue_id).all()
            for event in events:
                if start_time < (event.end_time + buffer) and end_time > (event.start_time - buffer):
                    # CLASH! Return alternatives
                    return self._propose_alternative(db, venue, start_time, end_time)

            # Check for other hire requests
            hires = db.query(HireRequest).filter(
                HireRequest.venue_id == venue_id, 
                HireRequest.status.in_(["approved", "pending"])
            ).all()
            for hire in hires:
                if start_time < hire.end_time and end_time > hire.start_time:
                    return self._propose_alternative(db, venue, start_time, end_time)

            return {
                "status": "AGREE", 
                "reason": "Hire request accepted.", 
                "price": price
            }

        return {"status": "REFUSE", "reason": "Unknown request"}

    def _propose_alternative(self, db, venue, requested_start, requested_end):
        # Advanced requirement: Counter-propose an alternative time
        alternative_time = requested_end + timedelta(days=1)
        
        alternatives = [
            {
                "venue_name": venue.name,
                "start_time": alternative_time.replace(hour=9, minute=0).isoformat(),
                "end_time": alternative_time.replace(hour=17, minute=0).isoformat(),
                "estimated_price": venue.hourly_rate * 8
            }
        ]
        
        return {
            "status": "PROPOSE",
            "reason": "The venue is unavailable at your requested time.",
            "alternatives": alternatives
        }

venue_agent = VenueAgent()
bus.register_agent("VenueAgent", venue_agent)
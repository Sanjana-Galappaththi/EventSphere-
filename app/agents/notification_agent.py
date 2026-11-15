from app.agents.base import BaseAgent
from app.agents.bus import bus

class NotificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("NotificationAgent")

    def receive_message(self, db, sender, performative, content, conversation_id):
        # Reacts to INFORM messages (broadcasts)
        if performative == "INFORM":
            print(f"[Notification] {content.get('message')}")
            return {"status": "AGREE"}
            
        return {"status": "REFUSE"}

notification_agent = NotificationAgent()
bus.register_agent("NotificationAgent", notification_agent)
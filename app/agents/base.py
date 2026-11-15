class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def receive_message(self, db, sender: str, performative: str, content: dict, conversation_id: str):
        """This method is overridden by specific agents to handle incoming messages"""
        raise NotImplementedError("Agents must implement receive_message")
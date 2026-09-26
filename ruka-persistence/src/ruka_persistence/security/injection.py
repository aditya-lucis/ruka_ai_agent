class InjectionDefense:
    def __init__(self):
        self.banned_phrases = [
            "ignore all previous instructions",
            "system override",
            "bypass safety",
        ]
        
    def scan(self, text: str) -> bool:
        """Return True if safe, False if injection detected."""
        lower = text.lower()
        for phrase in self.banned_phrases:
            if phrase in lower:
                return False
        return True
        
    def wrap_for_prompt(self, data: str) -> str:
        # DATA != INSTRUCTION doctrine
        return f"```data\n{data}\n```"

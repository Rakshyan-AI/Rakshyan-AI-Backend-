import re
from typing import Dict, Any, List
from app.agents.base_agent import BaseSafetyAgent
from app.models.schemas import AgentScoreDetail

class BullyingAgent(BaseSafetyAgent):
    def __init__(self):
        super().__init__(name="Bullying & Harassment Agent")
        
        # High impact bullying cues
        self.severe_keywords = [
            "kill yourself", "die", "go die", "nobody likes you", "loser",
            "ugly", "worthless", "freak", "stupid idiot", "delete your account",
            "everyone hates you", "fat pig", "disgusting", "kill urself"
        ]
        
        # Moderate bullying & harassment patterns
        self.moderate_keywords = [
            "shut up", "idiot", "dumb", "clown", "fake", "get lost",
            "stop talking", "embarrassing", "annoying", "pathetic", "creep"
        ]

    def analyze(self, text: str, context: Dict[str, Any] = None) -> AgentScoreDetail:
        lower_text = text.lower()
        matched_indicators: List[str] = []
        score = 0.0
        
        # Check severe patterns
        for pattern in self.severe_keywords:
            if re.search(r"\b" + re.escape(pattern) + r"\b", lower_text):
                matched_indicators.append(f"Severe harassment cue: '{pattern}'")
                score += 45.0
                
        # Check moderate patterns
        for pattern in self.moderate_keywords:
            if re.search(r"\b" + re.escape(pattern) + r"\b", lower_text):
                matched_indicators.append(f"Degrading insult: '{pattern}'")
                score += 18.0

        # Check aggressive typography (ALL CAPS and exclamation flood)
        if len(text) > 8 and text.isupper():
            score += 15.0
            matched_indicators.append("Aggressive tone: ALL CAPS speech")
            
        if "!!!" in text or "????" in text:
            score += 10.0
            matched_indicators.append("Hostile punctuation repetition")

        final_score = min(100.0, score)
        confidence = 0.90 if matched_indicators else 0.40

        return AgentScoreDetail(
            agent_name=self.name,
            score=round(final_score, 1),
            confidence=confidence,
            indicators=matched_indicators
        )

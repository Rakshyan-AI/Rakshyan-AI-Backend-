from typing import Dict, Any, List
from app.agents.base_agent import BaseSafetyAgent
from app.models.schemas import AgentScoreDetail

class EmotionAgent(BaseSafetyAgent):
    def __init__(self):
        super().__init__(name="Emotional Distress & Sentiment Agent")
        
        self.distress_markers = [
            "please stop", "leave me alone", "i am so scared", "i'm terrified",
            "don't hurt me", "i can't take this anymore", "crying right now",
            "i feel helpless", "please don't share", "i am afraid", "shaking right now",
            "nobody helps me", "want to disappear"
        ]
        
        self.panic_markers = [
            "omg what do i do", "i messed up", "i don't know what to do",
            "please delete it", "i beg you", "stop threatening me"
        ]

    def analyze(self, text: str, context: Dict[str, Any] = None) -> AgentScoreDetail:
        lower_text = text.lower()
        matched_indicators: List[str] = []
        score = 0.0

        for m in self.distress_markers:
            if m in lower_text:
                matched_indicators.append(f"Severe distress indicator: '{m}'")
                score += 35.0

        for p in self.panic_markers:
            if p in lower_text:
                matched_indicators.append(f"Panic/Coercion reaction: '{p}'")
                score += 40.0

        final_score = min(100.0, score)
        confidence = 0.90 if matched_indicators else 0.40

        return AgentScoreDetail(
            agent_name=self.name,
            score=round(final_score, 1),
            confidence=confidence,
            indicators=matched_indicators
        )

from typing import Dict, Any, List
from app.agents.base_agent import BaseSafetyAgent
from app.models.schemas import AgentScoreDetail

class IndicAgent(BaseSafetyAgent):
    def __init__(self):
        super().__init__(name="Indic & Hinglish Vernacular Safety Agent")
        
        # Hinglish coercive / blackmailing cues
        self.coercion_cues = [
            "kisi ko bataya toh dekh lena", "photo viral kar dunga", "viral kar dunga",
            "teri photo upload kar dunga", "paise de varna", "chup chaap sun",
            "mummy papa ko mat bolna", "ghar pe bol dunga", "badnaam kar dunga",
            "tera number leak kar dunga"
        ]
        
        # Hinglish abusive slurs
        self.abusive_cues = [
            "kamina", "kameena", "kutte", "saale", "chup kar", "mar ja",
            "aukaat", "pagal hai kya", "feku", "gadha", "bevkoof", "bakwas band kar"
        ]

    def analyze(self, text: str, context: Dict[str, Any] = None) -> AgentScoreDetail:
        lower_text = text.lower()
        matched_indicators: List[str] = []
        score = 0.0

        for cue in self.coercion_cues:
            if cue in lower_text:
                matched_indicators.append(f"Hinglish extortion/blackmail cue: '{cue}'")
                score += 55.0

        for cue in self.abusive_cues:
            if cue in lower_text:
                matched_indicators.append(f"Vernacular slur/insult: '{cue}'")
                score += 25.0

        final_score = min(100.0, score)
        confidence = 0.92 if matched_indicators else 0.35

        return AgentScoreDetail(
            agent_name=self.name,
            score=round(final_score, 1),
            confidence=confidence,
            indicators=matched_indicators
        )

import re
from typing import Dict, Any, List
from app.agents.base_agent import BaseSafetyAgent
from app.models.schemas import AgentScoreDetail

class GroomingAgent(BaseSafetyAgent):
    def __init__(self):
        super().__init__(name="Grooming & Predatory Coercion Agent")
        
        # Inappropriate photo / intimacy requests (flexible regex patterns)
        self.intimacy_regexes = [
            r"send\s+(?:me\s+)?(?:a\s+)?(?:private\s+)?(?:photo|pic|picture|selfie|snap)",
            r"what\s+are\s+you\s+wearing",
            r"(?:alone|by\s+yourself)\s+in\s+your\s+room",
            r"(?:video\s*call|facetime)\s+(?:when\s+you(?:'re|\s+are)\s+)?alone",
            r"(?:without|no)\s+clothes",
            r"mature\s+for\s+(?:your|ur)\s+age",
            r"show\s+me\s+your(?:self)?"
        ]

        # Secrecy patterns (flexible regex patterns)
        self.secrecy_regexes = [
            r"don'?t\s+tell\s+(?:your|ur)?\s*(?:mom|dad|parents|anyone|family)",
            r"keep\s+this\s+(?:our\s+)?secret",
            r"(?:delete|erase)\s+this\s+(?:chat|message|convo|conversation)",
            r"never\s+tell\s+anyone",
            r"promise\s+not\s+to\s+tell",
            r"just\s+between\s+(?:us|you\s+and\s+me)"
        ]

        # Isolation patterns
        self.isolation_patterns = [
            "your parents don't understand", "nobody understands you like i do",
            "they don't care about you", "you can trust only me", "your friends are fake"
        ]

        # Luring / Incentives
        self.luring_patterns = [
            "i will buy you robux", "free v-bucks", "i will send you money",
            "gift card for you", "i bought you a present", "come meet me", "let me pick you up"
        ]
        
        # Platform migration to ephemeral messaging
        self.migration_patterns = [
            "switch to snapchat", "talk on telegram", "move to snap", "add me on discord secret",
            "disappearing messages"
        ]

    def analyze(self, text: str, context: Dict[str, Any] = None) -> AgentScoreDetail:
        lower_text = text.lower()
        matched_indicators: List[str] = []
        score = 0.0

        # Check Secrecy Regexes
        for rx in self.secrecy_regexes:
            match = re.search(rx, lower_text)
            if match:
                matched_indicators.append(f"Secrecy enforcement cue: '{match.group(0)}'")
                score += 45.0

        # Check Inappropriate requests Regexes
        for rx in self.intimacy_regexes:
            match = re.search(rx, lower_text)
            if match:
                matched_indicators.append(f"Inappropriate boundary/photo probe: '{match.group(0)}'")
                score += 50.0

        # Check Isolation
        for p in self.isolation_patterns:
            if p in lower_text:
                matched_indicators.append(f"Psychological isolation attempt: '{p}'")
                score += 35.0

        # Check Luring
        for p in self.luring_patterns:
            if p in lower_text:
                matched_indicators.append(f"Material incentive / meeting solicitation: '{p}'")
                score += 30.0

        # Check Platform Migration
        for p in self.migration_patterns:
            if p in lower_text:
                matched_indicators.append(f"Channel migration to unmonitored platform: '{p}'")
                score += 25.0

        final_score = min(100.0, score)
        confidence = 0.95 if matched_indicators else 0.35

        return AgentScoreDetail(
            agent_name=self.name,
            score=round(final_score, 1),
            confidence=confidence,
            indicators=matched_indicators
        )

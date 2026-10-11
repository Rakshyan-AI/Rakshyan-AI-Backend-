from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.schemas import AgentScoreDetail

class BaseSafetyAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, text: str, context: Dict[str, Any] = None) -> AgentScoreDetail:
        """
        Analyzes text and returns structured score (0-100), confidence (0.0-1.0),
        and detected threat indicators.
        """
        pass

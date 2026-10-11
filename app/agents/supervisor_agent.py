from typing import Dict, Any, List
from app.agents.bullying_agent import BullyingAgent
from app.agents.grooming_agent import GroomingAgent
from app.agents.emotion_agent import EmotionAgent
from app.agents.indic_agent import IndicAgent
from app.models.schemas import RiskAssessmentResult, AgentScoreDetail
from app.config import settings

class SupervisorAgent:
    def __init__(self):
        self.bullying_agent = BullyingAgent()
        self.grooming_agent = GroomingAgent()
        self.emotion_agent = EmotionAgent()
        self.indic_agent = IndicAgent()

    def evaluate(self, text: str, context: Dict[str, Any] = None) -> RiskAssessmentResult:
        """
        Executes parallel micro-agent evaluation, aggregates signals using supervisory logic,
        and produces an explainable 0-100 risk assessment.
        """
        # Run individual specialized agents
        res_bullying = self.bullying_agent.analyze(text, context)
        res_grooming = self.grooming_agent.analyze(text, context)
        res_emotion = self.emotion_agent.analyze(text, context)
        res_indic = self.indic_agent.analyze(text, context)

        agent_breakdown: Dict[str, AgentScoreDetail] = {
            "bullying": res_bullying,
            "grooming": res_grooming,
            "emotion": res_emotion,
            "indic": res_indic
        }

        # Weighted calculation
        # Grooming & Blackmail carry higher safety impact than general insults
        weighted_score = (
            (res_grooming.score * 0.40) +
            (res_indic.score * 0.25) +
            (res_bullying.score * 0.20) +
            (res_emotion.score * 0.15)
        )

        # Peak hazard escalation: If any individual agent flags >= 70, overall risk must NOT be diluted!
        max_single_score = max(res_bullying.score, res_grooming.score, res_emotion.score, res_indic.score)
        if max_single_score >= 70.0:
            final_risk_score = max(weighted_score, max_single_score)
        else:
            final_risk_score = weighted_score

        final_risk_score = min(100.0, max(0.0, round(final_risk_score, 1)))

        # Determine Severity
        if final_risk_score >= settings.RISK_THRESHOLD_CRITICAL:
            severity = "CRITICAL"
        elif final_risk_score >= settings.RISK_THRESHOLD_HIGH:
            severity = "HIGH"
        elif final_risk_score >= settings.RISK_THRESHOLD_MEDIUM:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Determine Primary Category
        scores_by_cat = {
            "Grooming & Coercion": res_grooming.score,
            "Vernacular Extortion": res_indic.score,
            "Cyberbullying": res_bullying.score,
            "Emotional Distress": res_emotion.score,
        }
        primary_category = max(scores_by_cat, key=scores_by_cat.get)
        if final_risk_score == 0:
            primary_category = "Benign Communication"

        # Collect All Explainable Reason Indicators
        all_indicators: List[str] = []
        for ag in agent_breakdown.values():
            all_indicators.extend(ag.indicators)

        if all_indicators:
            detected_reason = "; ".join(all_indicators[:4])
        else:
            detected_reason = "No harmful linguistic or behavioral indicators detected."

        # Recommended Action based on XAI
        if severity in ["CRITICAL", "HIGH"]:
            if primary_category == "Grooming & Coercion" or primary_category == "Vernacular Extortion":
                recommended_action = "Immediate Action: Check child's state gently. Do not delete messages—preserve digital evidence under POCSO/DPDP compliance."
            else:
                recommended_action = "Parent Review Advised: Have an empathetic talk with your child regarding online peer interactions."
        elif severity == "MEDIUM":
            recommended_action = "Monitor Trend: Mild risk indicators detected. Review activity logs in the dashboard."
        else:
            recommended_action = "Normal: Safe digital environment."

        alert_triggered = final_risk_score >= settings.RISK_THRESHOLD_HIGH

        return RiskAssessmentResult(
            overall_risk_score=final_risk_score,
            severity=severity,
            category=primary_category,
            detected_reason=detected_reason,
            recommended_action=recommended_action,
            agent_breakdown=agent_breakdown,
            alert_triggered=alert_triggered
        )

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AlertService:
    @staticmethod
    async def dispatch_parent_alert(
        parent_id: str,
        child_name: str,
        risk_score: float,
        category: str,
        reason: str,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Dispatches high-priority push notification / alert payload to Parent device.
        """
        alert_payload = {
            "title": f"🚨 High-Risk Cyber Alert: {child_name}",
            "body": f"Risk Score: {risk_score}/100 | {category}\n{reason[:100]}...",
            "data": {
                "incident_id": incident_id,
                "parent_id": parent_id,
                "category": category,
                "risk_score": str(risk_score),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "OPEN_INCIDENT_VIEW"
            }
        }
        
        # Log simulated push delivery
        logger.warning(
            f"[RAKSHAN-ALERT-DISPATCH] Sent alert for Child '{child_name}' (Parent: {parent_id}) -> "
            f"Score: {risk_score}/100, Cat: {category}"
        )
        return {
            "success": True,
            "channel": "FCM_PUSH_AND_IN_APP",
            "payload": alert_payload
        }

alert_service = AlertService()

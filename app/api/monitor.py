from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.db_models import ChildDevice, SafetyIncident, ActivityLog
from app.models.schemas import ActivityIngestRequest, RiskAssessmentResult
from app.agents.supervisor_agent import SupervisorAgent
from app.services.alert_service import alert_service
from app.services.compliance_service import compliance_service

router = APIRouter(prefix="/monitor", tags=["AI Safety Ingestion & Risk Analysis"])
supervisor = SupervisorAgent()

@router.post("/ingest", response_model=RiskAssessmentResult)
async def ingest_activity(
    req: ActivityIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests permitted text/notification from child device, runs Multi-Agent analysis,
    updates child risk status, logs incidents, and dispatches real-time alerts if necessary.
    """
    # Verify child device
    stmt = select(ChildDevice).where(ChildDevice.device_id == req.device_id)
    res = await db.execute(stmt)
    child = res.scalars().first()

    if not child or not child.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unregistered or deactivated child device."
        )

    # Multi-Agent Evaluation
    eval_result: RiskAssessmentResult = supervisor.evaluate(
        text=req.text_content,
        context={"app_name": req.app_name, "sender": req.sender}
    )

    # Update child risk metric
    child.current_risk_score = eval_result.overall_risk_score
    child.current_status = eval_result.severity.lower()
    child.last_sync_at = datetime.utcnow()

    # Log general activity
    activity = ActivityLog(
        child_id=child.id,
        app_name=req.app_name,
        sender_alias=req.sender,
        analyzed_risk=eval_result.overall_risk_score,
        sentiment_score=eval_result.overall_risk_score
    )
    db.add(activity)

    # If risk is medium or higher, record Safety Incident
    if eval_result.overall_risk_score >= 35.0:
        # Privacy Redaction: Truncate raw content for safety under DPDP
        snippet_preview = req.text_content[:150]
        
        # Convert agent breakdown to JSON serializable dict
        serializable_breakdown = {
            k: v.model_dump() for k, v in eval_result.agent_breakdown.items()
        }

        incident = SafetyIncident(
            child_id=child.id,
            category=eval_result.category,
            risk_score=eval_result.overall_risk_score,
            severity=eval_result.severity,
            detected_reason=eval_result.detected_reason,
            flagged_snippet=snippet_preview,
            app_source=req.app_name,
            agent_breakdown=serializable_breakdown,
            status="new"
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)

        # Log DPDP compliance record
        await compliance_service.log_compliance_event(
            db=db,
            event_type="INCIDENT_RECORDED",
            parent_id=child.parent_id,
            child_id=child.id,
            incident_id=incident.id,
            details={
                "category": eval_result.category,
                "score": eval_result.overall_risk_score,
                "app": req.app_name
            }
        )

        # Dispatch Real-Time Push Notification if High/Critical
        if eval_result.alert_triggered:
            await alert_service.dispatch_parent_alert(
                parent_id=child.parent_id,
                child_name=child.child_name,
                risk_score=eval_result.overall_risk_score,
                category=eval_result.category,
                reason=eval_result.detected_reason,
                incident_id=incident.id
            )
    else:
        await db.commit()

    return eval_result


@router.post("/simulate-test", response_model=RiskAssessmentResult)
async def simulate_test_sentence(text: str):
    """
    Direct playground endpoint to test the Multi-Agent Engine with any custom sentence.
    Useful for live demos and jury presentations!
    """
    return supervisor.evaluate(text=text)

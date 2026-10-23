from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.db_models import User, ChildDevice, SafetyIncident, ActivityLog
from app.models.schemas import DashboardOverviewResponse, IncidentResponse, ActivityLogResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["Dashboard Analytics"])

@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Aggregates high-level child safety telemetry and distribution metrics."""
    # Fetch children
    child_stmt = select(ChildDevice).where(ChildDevice.parent_id == current_user.id)
    child_res = await db.execute(child_stmt)
    children = child_res.scalars().all()
    child_ids = [c.id for c in children]
    child_dict = {c.id: c.child_name for c in children}

    total_devices = len(children)
    if total_devices == 0:
        return DashboardOverviewResponse(
            total_linked_devices=0,
            active_threats_count=0,
            overall_family_safety_score=100.0,
            recent_incidents=[],
            category_distribution={}
        )

    # Active threats (Severity in HIGH or CRITICAL with status 'new')
    threat_stmt = select(func.count(SafetyIncident.id)).where(
        SafetyIncident.child_id.in_(child_ids),
        SafetyIncident.severity.in_(["HIGH", "CRITICAL"]),
        SafetyIncident.status == "new"
    )
    threat_res = await db.execute(threat_stmt)
    active_threats_count = threat_res.scalar() or 0

    # Calculate overall family safety score (100 - average risk)
    avg_risk = sum(c.current_risk_score for c in children) / max(total_devices, 1)
    family_safety_score = round(max(0.0, 100.0 - avg_risk), 1)

    # Recent incidents
    inc_stmt = select(SafetyIncident).where(
        SafetyIncident.child_id.in_(child_ids)
    ).order_by(desc(SafetyIncident.created_at)).limit(5)
    inc_res = await db.execute(inc_stmt)
    recent_raw = inc_res.scalars().all()

    recent_incidents = [
        IncidentResponse(
            id=inc.id,
            child_id=inc.child_id,
            child_name=child_dict.get(inc.child_id, "Child"),
            category=inc.category,
            risk_score=inc.risk_score,
            severity=inc.severity,
            detected_reason=inc.detected_reason,
            flagged_snippet=inc.flagged_snippet,
            app_source=inc.app_source,
            agent_breakdown=inc.agent_breakdown,
            status=inc.status,
            created_at=inc.created_at,
            parent_acknowledged_at=inc.parent_acknowledged_at
        )
        for inc in recent_raw
    ]

    # Recent notifications across all apps
    act_stmt = select(ActivityLog).where(
        ActivityLog.child_id.in_(child_ids)
    ).order_by(desc(ActivityLog.processed_at)).limit(15)
    act_res = await db.execute(act_stmt)
    recent_acts = act_res.scalars().all()

    recent_notifications = [
        ActivityLogResponse(
            id=act.id,
            child_id=act.child_id,
            child_name=child_dict.get(act.child_id, "Child"),
            app_name=act.app_name,
            package_name=act.package_name,
            sender_alias=act.sender_alias or "Unknown Sender",
            text_content=act.text_content,
            analyzed_risk=act.analyzed_risk or 0.0,
            sentiment_score=act.sentiment_score or 0.0,
            category=act.category or "Safe",
            severity=act.severity or "SAFE",
            processed_at=act.processed_at
        )
        for act in recent_acts
    ]

    # Category distribution
    cat_dist: Dict[str, int] = {}
    cat_stmt = select(SafetyIncident.category, func.count(SafetyIncident.id)).where(
        SafetyIncident.child_id.in_(child_ids)
    ).group_by(SafetyIncident.category)
    cat_res = await db.execute(cat_stmt)
    for cat_name, cnt in cat_res.all():
        cat_dist[cat_name] = cnt

    return DashboardOverviewResponse(
        total_linked_devices=total_devices,
        active_threats_count=active_threats_count,
        overall_family_safety_score=family_safety_score,
        recent_incidents=recent_incidents,
        recent_notifications=recent_notifications,
        category_distribution=cat_dist
    )

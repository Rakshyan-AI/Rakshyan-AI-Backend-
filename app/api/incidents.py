from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.db_models import User, ChildDevice, SafetyIncident
from app.models.schemas import IncidentResponse, IncidentAcknowledgeRequest
from app.api.deps import get_current_user
from app.services.compliance_service import compliance_service

router = APIRouter(prefix="/incidents", tags=["Parent Incidents & Evidence Records"])

@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    child_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all safety incidents for the current parent's registered children."""
    # Find all children for parent
    child_stmt = select(ChildDevice).where(ChildDevice.parent_id == current_user.id)
    child_res = await db.execute(child_stmt)
    children = {c.id: c.child_name for c in child_res.scalars().all()}

    if not children:
        return []

    # Query incidents
    query = select(SafetyIncident).where(SafetyIncident.child_id.in_(list(children.keys())))
    if child_id and child_id in children:
        query = query.where(SafetyIncident.child_id == child_id)
    if severity:
        query = query.where(SafetyIncident.severity == severity.upper())

    query = query.order_by(desc(SafetyIncident.created_at)).limit(limit)
    res = await db.execute(query)
    incidents = res.scalars().all()

    # Enrich with child name
    out = []
    for inc in incidents:
        inc_dict = {
            "id": inc.id,
            "child_id": inc.child_id,
            "child_name": children.get(inc.child_id, "Protected Child"),
            "category": inc.category,
            "risk_score": inc.risk_score,
            "severity": inc.severity,
            "detected_reason": inc.detected_reason,
            "flagged_snippet": inc.flagged_snippet,
            "app_source": inc.app_source,
            "agent_breakdown": inc.agent_breakdown,
            "status": inc.status,
            "created_at": inc.created_at,
            "parent_acknowledged_at": inc.parent_acknowledged_at
        }
        out.append(IncidentResponse(**inc_dict))
    return out


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident_detail(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full incident record and explainable AI metrics."""
    stmt = select(SafetyIncident).where(SafetyIncident.id == incident_id)
    res = await db.execute(stmt)
    inc = res.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    # Check ownership
    child_stmt = select(ChildDevice).where(ChildDevice.id == inc.child_id, ChildDevice.parent_id == current_user.id)
    child_res = await db.execute(child_stmt)
    child = child_res.scalars().first()
    if not child:
        raise HTTPException(status_code=403, detail="Unauthorized access to this incident record.")

    return IncidentResponse(
        id=inc.id,
        child_id=inc.child_id,
        child_name=child.child_name,
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


@router.post("/{incident_id}/acknowledge")
async def acknowledge_incident(
    incident_id: str,
    req: IncidentAcknowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Parent acknowledges having reviewed the incident."""
    stmt = select(SafetyIncident).where(SafetyIncident.id == incident_id)
    res = await db.execute(stmt)
    inc = res.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    inc.status = "acknowledged"
    inc.parent_acknowledged_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Incident marked as acknowledged by parent."}


@router.get("/{incident_id}/export-pdf")
async def export_incident_pdf(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate and download a legal DPDP & POCSO compliance incident PDF report."""
    stmt = select(SafetyIncident).where(SafetyIncident.id == incident_id)
    res = await db.execute(stmt)
    inc = res.scalars().first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    child_stmt = select(ChildDevice).where(ChildDevice.id == inc.child_id, ChildDevice.parent_id == current_user.id)
    child_res = await db.execute(child_stmt)
    child = child_res.scalars().first()
    if not child:
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    pdf_bytes = compliance_service.generate_incident_pdf_bytes(
        incident=inc,
        child=child,
        parent=current_user
    )

    filename = f"Rakshan_Incident_{incident_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

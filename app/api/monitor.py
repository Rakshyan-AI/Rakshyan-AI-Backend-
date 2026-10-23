from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.db_models import ChildDevice, SafetyIncident, ActivityLog
from app.models.schemas import (
    ActivityIngestRequest,
    RiskAssessmentResult,
    ActivityLogResponse,
    DeviceControlCommandRequest,
    DeviceControlCommandResponse,
    DeviceStatusResponse,
    DeviceLocationInfo,
)
from app.agents.supervisor_agent import SupervisorAgent
from app.services.alert_service import alert_service
from app.services.compliance_service import compliance_service

router = APIRouter(prefix="/monitor", tags=["AI Safety Ingestion & Risk Analysis"])
supervisor = SupervisorAgent()

# Live Child Device State Store (Real-time telemetry and remote control state)
LIVE_DEVICE_STATE = {
    "device_id": "DEV-AARAV-SAMSUNG-S23",
    "child_name": "Aarav (Age 13)",
    "model": "Samsung Galaxy S23 5G",
    "os_version": "Android 14 (OneUI 6.1)",
    "battery_level": 84,
    "is_charging": False,
    "network": "Jio True 5G (VoLTE)",
    "active_app": "Instagram DM",
    "screen_time_used_hours": 1.8,
    "screen_time_limit_hours": 2.5,
    "location": {
        "latitude": 19.0600,
        "longitude": 72.8362,
        "address": "Linking Road, Bandra West, Mumbai",
        "safe_zone": "Home Safe Zone (500m)",
        "is_in_safe_zone": True,
    },
    "is_locked": False,
    "lock_message": None,
    "is_internet_paused": False,
    "is_bedtime_mode": False,
    "is_siren_ringing": False,
    "blocked_apps": {
        "Instagram": False,
        "Discord": False,
        "Snapchat": False,
        "Roblox": False,
        "YouTube": False,
        "WhatsApp": False,
        "Telegram": True,
        "Free Fire / BGMI": True,
    },
    "last_updated": datetime.utcnow(),
}


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
        package_name=req.package_name,
        sender_alias=req.sender,
        text_content=req.text_content,
        analyzed_risk=eval_result.overall_risk_score,
        sentiment_score=eval_result.overall_risk_score,
        category=eval_result.category,
        severity=eval_result.severity
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


@router.get("/notifications", response_model=List[ActivityLogResponse])
async def list_notifications(
    child_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all intercepted notifications from child devices across all apps (WhatsApp, Instagram, Discord, SMS, YouTube, etc.).
    """
    query = select(ActivityLog, ChildDevice.child_name).outerjoin(
        ChildDevice, ActivityLog.child_id == ChildDevice.id
    )
    if child_id:
        query = query.where(
            (ActivityLog.child_id == child_id) | 
            (ChildDevice.device_id == child_id)
        )
    query = query.order_by(desc(ActivityLog.processed_at)).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    out: List[ActivityLogResponse] = []
    for act, child_name in rows:
        out.append(
            ActivityLogResponse(
                id=act.id,
                child_id=act.child_id,
                child_name=child_name or "Child Device",
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
        )
    return out


@router.get("/device-status", response_model=DeviceStatusResponse)
async def get_device_status(device_id: Optional[str] = None):
    """
    Returns real-time hardware telemetry and remote control state of child device.
    """
    loc_data = LIVE_DEVICE_STATE["location"]
    return DeviceStatusResponse(
        device_id=LIVE_DEVICE_STATE["device_id"],
        child_name=LIVE_DEVICE_STATE["child_name"],
        model=LIVE_DEVICE_STATE["model"],
        os_version=LIVE_DEVICE_STATE["os_version"],
        battery_level=LIVE_DEVICE_STATE["battery_level"],
        is_charging=LIVE_DEVICE_STATE["is_charging"],
        network=LIVE_DEVICE_STATE["network"],
        active_app=LIVE_DEVICE_STATE["active_app"],
        screen_time_used_hours=LIVE_DEVICE_STATE["screen_time_used_hours"],
        screen_time_limit_hours=LIVE_DEVICE_STATE["screen_time_limit_hours"],
        location=DeviceLocationInfo(
            latitude=loc_data["latitude"],
            longitude=loc_data["longitude"],
            address=loc_data["address"],
            safe_zone=loc_data["safe_zone"],
            is_in_safe_zone=loc_data["is_in_safe_zone"],
        ),
        is_locked=LIVE_DEVICE_STATE["is_locked"],
        lock_message=LIVE_DEVICE_STATE["lock_message"],
        is_internet_paused=LIVE_DEVICE_STATE["is_internet_paused"],
        is_bedtime_mode=LIVE_DEVICE_STATE["is_bedtime_mode"],
        is_siren_ringing=LIVE_DEVICE_STATE["is_siren_ringing"],
        blocked_apps=LIVE_DEVICE_STATE["blocked_apps"],
        last_updated=LIVE_DEVICE_STATE["last_updated"],
    )


@router.post("/device-control", response_model=DeviceControlCommandResponse)
async def control_child_device(req: DeviceControlCommandRequest):
    """
    Parent executes remote enforcement commands on the child device.
    Commands:
      - LOCK_DEVICE / UNLOCK_DEVICE
      - PAUSE_INTERNET / RESUME_INTERNET
      - TRIGGER_SIREN / STOP_SIREN
      - SET_BEDTIME_MODE
      - SET_APP_BLOCK
      - SET_SCREEN_TIME_LIMIT
    """
    cmd = req.command.upper()
    payload = req.payload or {}
    msg = ""

    if cmd == "LOCK_DEVICE":
        LIVE_DEVICE_STATE["is_locked"] = True
        custom_msg = payload.get("message", "Parent has locked the screen remotely.")
        LIVE_DEVICE_STATE["lock_message"] = custom_msg
        msg = f"Screen locked remotely: {custom_msg}"

    elif cmd == "UNLOCK_DEVICE":
        LIVE_DEVICE_STATE["is_locked"] = False
        LIVE_DEVICE_STATE["lock_message"] = None
        msg = "Screen unlocked remotely."

    elif cmd == "PAUSE_INTERNET":
        LIVE_DEVICE_STATE["is_internet_paused"] = True
        msg = "Internet connectivity paused on child device."

    elif cmd == "RESUME_INTERNET":
        LIVE_DEVICE_STATE["is_internet_paused"] = False
        msg = "Internet connectivity resumed on child device."

    elif cmd == "TRIGGER_SIREN":
        LIVE_DEVICE_STATE["is_siren_ringing"] = True
        msg = "🚨 Remote emergency siren triggered on child device!"

    elif cmd == "STOP_SIREN":
        LIVE_DEVICE_STATE["is_siren_ringing"] = False
        msg = "Emergency siren silenced."

    elif cmd == "SET_BEDTIME_MODE":
        enabled = payload.get("enabled", not LIVE_DEVICE_STATE["is_bedtime_mode"])
        LIVE_DEVICE_STATE["is_bedtime_mode"] = enabled
        msg = f"Bedtime curfew {'activated' if enabled else 'disabled'}."

    elif cmd == "SET_APP_BLOCK":
        app_name = payload.get("app_name")
        if app_name:
            is_blocked = payload.get("is_blocked", True)
            LIVE_DEVICE_STATE["blocked_apps"][app_name] = is_blocked
            msg = f"{app_name} is now {'BLOCKED' if is_blocked else 'ALLOWED'} on child device."
        else:
            msg = "Missing app_name in payload."

    elif cmd == "SET_SCREEN_TIME_LIMIT":
        limit = float(payload.get("limit_hours", 2.5))
        LIVE_DEVICE_STATE["screen_time_limit_hours"] = limit
        msg = f"Daily screen time limit adjusted to {limit} hours."

    else:
        msg = f"Unknown command: {cmd}"

    LIVE_DEVICE_STATE["last_updated"] = datetime.utcnow()

    return DeviceControlCommandResponse(
        success=True,
        device_id=LIVE_DEVICE_STATE["device_id"],
        command=cmd,
        message=msg,
        updated_state={
            "is_locked": LIVE_DEVICE_STATE["is_locked"],
            "lock_message": LIVE_DEVICE_STATE["lock_message"],
            "is_internet_paused": LIVE_DEVICE_STATE["is_internet_paused"],
            "is_bedtime_mode": LIVE_DEVICE_STATE["is_bedtime_mode"],
            "is_siren_ringing": LIVE_DEVICE_STATE["is_siren_ringing"],
            "screen_time_limit_hours": LIVE_DEVICE_STATE["screen_time_limit_hours"],
            "blocked_apps": LIVE_DEVICE_STATE["blocked_apps"],
        },
    )


@router.post("/update-child-telemetry")
async def update_child_telemetry(payload: dict):
    """
    Child device reports its real hardware telemetry (battery, active app, location).
    """
    if "battery_level" in payload:
        LIVE_DEVICE_STATE["battery_level"] = int(payload["battery_level"])
    if "is_charging" in payload:
        LIVE_DEVICE_STATE["is_charging"] = bool(payload["is_charging"])
    if "active_app" in payload:
        LIVE_DEVICE_STATE["active_app"] = str(payload["active_app"])
    if "screen_time_used_hours" in payload:
        LIVE_DEVICE_STATE["screen_time_used_hours"] = float(payload["screen_time_used_hours"])
    if "location" in payload and isinstance(payload["location"], dict):
        LIVE_DEVICE_STATE["location"].update(payload["location"])

    LIVE_DEVICE_STATE["last_updated"] = datetime.utcnow()
    return {"success": True, "updated_at": LIVE_DEVICE_STATE["last_updated"]}



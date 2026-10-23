from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.db_models import User, ChildDevice
from app.models.schemas import (
    CreatePairingCodeRequest,
    PairingCodeResponse,
    VerifyPairingCodeRequest,
    VerifyPairingCodeResponse,
    ChildDeviceResponse
)
from app.services.pairing_service import create_pairing_code, verify_and_bind_device
from app.api.deps import get_current_user, create_access_token
from app.config import settings

router = APIRouter(prefix="/pairing", tags=["Parent-Child Device Pairing"])

@router.post("/generate", response_model=PairingCodeResponse)
async def generate_code(
    req: CreatePairingCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Parent generates a unique 6-digit one-time code to link a child device."""
    code_obj = await create_pairing_code(
        db=db,
        parent_id=current_user.id,
        child_nickname=req.child_nickname
    )
    return PairingCodeResponse(
        code=code_obj.code,
        child_nickname=code_obj.child_nickname,
        expires_at=code_obj.expires_at,
        validity_minutes=settings.PAIRING_CODE_EXPIRE_MINUTES
    )

@router.post("/verify", response_model=VerifyPairingCodeResponse)
async def verify_code(
    req: VerifyPairingCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Child application verifies the 6-digit pairing code and receives a secure device token."""
    success, msg, child_device, parent = await verify_and_bind_device(
        db=db,
        code=req.code,
        device_id=req.device_id,
        device_model=req.device_model or "Android Device",
        os_version=req.os_version or "Android 14",
        child_name=req.child_name
    )

    if not success or not child_device or not parent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # Issue device access token
    device_token = create_access_token({
        "sub": child_device.id,
        "device_id": child_device.device_id,
        "role": "child_device",
        "parent_id": parent.id
    })

    return VerifyPairingCodeResponse(
        success=True,
        message=msg,
        child_id=child_device.id,
        device_token=device_token,
        child_name=child_device.child_name,
        parent_name=parent.full_name
    )

@router.get("/devices", response_model=List[ChildDeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all child devices linked to the current parent account."""
    stmt = select(ChildDevice).where(ChildDevice.parent_id == current_user.id)
    res = await db.execute(stmt)
    devices = res.scalars().all()
    return devices

@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Parent revokes or disconnects a child device."""
    stmt = select(ChildDevice).where(
        ChildDevice.device_id == device_id,
        ChildDevice.parent_id == current_user.id
    )
    res = await db.execute(stmt)
    dev = res.scalars().first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found or not owned by you.")

    dev.is_active = False
    await db.commit()
    return {"success": True, "message": f"Device {device_id} successfully revoked."}

import random
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.models.db_models import PairingCode, ChildDevice, User
from app.config import settings

def generate_digit_code(length: int = 6) -> str:
    """Generates an unambiguous 6-digit numeric string."""
    return "".join(random.choices("0123456789", k=length))

async def create_pairing_code(db: AsyncSession, parent_id: str, child_nickname: str) -> PairingCode:
    """Creates a new one-time 6-digit pairing code with expiration."""
    code = generate_digit_code(settings.PAIRING_CODE_LENGTH)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.PAIRING_CODE_EXPIRE_MINUTES)
    
    pairing_entry = PairingCode(
        parent_id=parent_id,
        code=code,
        child_nickname=child_nickname,
        expires_at=expires_at,
        is_used=False
    )
    db.add(pairing_entry)
    await db.commit()
    await db.refresh(pairing_entry)
    return pairing_entry

async def verify_and_bind_device(
    db: AsyncSession,
    code: str,
    device_id: str,
    device_model: str = "Android Device",
    os_version: str = "Android 14"
) -> Tuple[bool, str, Optional[ChildDevice], Optional[User]]:
    """
    Validates the 6-digit pairing code and establishes parent-child device relationship.
    """
    stmt = select(PairingCode).where(
        and_(
            PairingCode.code == code.strip(),
            PairingCode.is_used == False,
            PairingCode.expires_at > datetime.utcnow()
        )
    )
    result = await db.execute(stmt)
    pairing_record = result.scalars().first()

    if not pairing_record:
        return False, "Invalid, expired, or already used pairing code.", None, None

    # Retrieve Parent
    parent_stmt = select(User).where(User.id == pairing_record.parent_id)
    parent_res = await db.execute(parent_stmt)
    parent = parent_res.scalars().first()
    if not parent:
        return False, "Parent account not found.", None, None

    # Check if this hardware device is already registered
    dev_stmt = select(ChildDevice).where(ChildDevice.device_id == device_id)
    dev_res = await db.execute(dev_stmt)
    existing_dev = dev_res.scalars().first()

    if existing_dev:
        # Re-link existing device to this parent
        existing_dev.parent_id = parent.id
        existing_dev.child_name = pairing_record.child_nickname
        existing_dev.device_model = device_model
        existing_dev.os_version = os_version
        existing_dev.is_active = True
        existing_dev.last_sync_at = datetime.utcnow()
        child_device = existing_dev
    else:
        # Create new ChildDevice record
        child_device = ChildDevice(
            parent_id=parent.id,
            device_id=device_id,
            child_name=pairing_record.child_nickname,
            device_model=device_model,
            os_version=os_version,
            is_active=True,
            current_risk_score=0.0,
            current_status="safe"
        )
        db.add(child_device)

    # Mark code as consumed
    pairing_record.is_used = True
    await db.commit()
    await db.refresh(child_device)

    return True, "Device paired successfully.", child_device, parent

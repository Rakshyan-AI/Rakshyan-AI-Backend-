import asyncio
import sys
from datetime import datetime, timedelta

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.database import init_db, AsyncSessionLocal
from app.models.db_models import User, ChildDevice, SafetyIncident, ActivityLog
from app.api.deps import get_password_hash
from app.services.compliance_service import compliance_service

async def seed():
    print("[*] Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Create Demo Parent User
        demo_email = "parent@rakshan.ai"
        from sqlalchemy import select
        existing = await db.execute(select(User).where(User.email == demo_email))
        if existing.scalars().first():
            print("⚠️ Demo data already exists. Skipping.")
            return

        print("[*] Creating Demo Parent User...")
        parent = User(
            email=demo_email,
            hashed_password=get_password_hash("password123"),
            full_name="Rajesh Sharma",
            phone_number="+91 98765 43210",
            role="parent"
        )
        db.add(parent)
        await db.commit()
        await db.refresh(parent)

        # Create 2 Connected Child Devices
        print("[*] Registering Linked Child Devices...")
        child1 = ChildDevice(
            parent_id=parent.id,
            device_id="DEV-AARAV-SAMSUNG-S23",
            child_name="Aarav (Age 13)",
            device_model="Samsung Galaxy S23",
            os_version="Android 14",
            is_active=True,
            current_risk_score=87.5,
            current_status="critical",
            last_sync_at=datetime.utcnow()
        )
        child2 = ChildDevice(
            parent_id=parent.id,
            device_id="DEV-ANANYA-PIXEL-7",
            child_name="Ananya (Age 10)",
            device_model="Google Pixel 7a",
            os_version="Android 14",
            is_active=True,
            current_risk_score=12.0,
            current_status="safe",
            last_sync_at=datetime.utcnow()
        )
        db.add_all([child1, child2])
        await db.commit()
        await db.refresh(child1)
        await db.refresh(child2)

        # Seed Realistic Safety Incidents
        print("[*] Seeding High-Risk and Moderate Incidents...")
        inc1 = SafetyIncident(
            child_id=child1.id,
            category="Grooming & Coercion",
            risk_score=87.5,
            severity="CRITICAL",
            detected_reason="Secrecy enforcement cue: 'don't tell your mom'; Psychological isolation attempt: 'your parents don't understand'; Inappropriate boundary/photo probe: 'send selfie'",
            flagged_snippet="Don't tell your mom about our chat. She doesn't understand you, send me a private selfie now.",
            app_source="Instagram DM",
            agent_breakdown={
                "grooming": {"score": 95.0, "confidence": 0.95, "indicators": ["Secrecy cue", "Isolation", "Photo request"]},
                "bullying": {"score": 10.0, "confidence": 0.40, "indicators": []},
                "indic": {"score": 0.0, "confidence": 0.35, "indicators": []},
                "emotion": {"score": 45.0, "confidence": 0.85, "indicators": ["Subtle anxiety markers"]}
            },
            status="new",
            created_at=datetime.utcnow() - timedelta(minutes=45)
        )

        inc2 = SafetyIncident(
            child_id=child1.id,
            category="Cyberbullying",
            risk_score=72.0,
            severity="HIGH",
            detected_reason="Severe harassment cue: 'nobody likes you'; Degrading insult: 'loser'",
            flagged_snippet="You are such a loser, nobody likes you in this school group. Stop texting here.",
            app_source="Discord Channel",
            agent_breakdown={
                "bullying": {"score": 75.0, "confidence": 0.92, "indicators": ["Degrading slur", "Exclusion"]},
                "grooming": {"score": 0.0, "confidence": 0.35, "indicators": []},
                "indic": {"score": 0.0, "confidence": 0.35, "indicators": []},
                "emotion": {"score": 50.0, "confidence": 0.90, "indicators": ["High negative peer impact"]}
            },
            status="acknowledged",
            parent_acknowledged_at=datetime.utcnow() - timedelta(hours=2),
            created_at=datetime.utcnow() - timedelta(hours=3)
        )

        db.add_all([inc1, inc2])
        await db.commit()

        # Log DPDP compliance record for demonstration
        await compliance_service.log_compliance_event(
            db=db,
            event_type="INCIDENT_RECORDED",
            parent_id=parent.id,
            child_id=child1.id,
            incident_id=inc1.id,
            details={"demo_flag": True, "category": "Grooming & Coercion"}
        )

        print("[+] Demo Data Seeding Complete!")
        print("================================================")
        print("Test Credentials:")
        print("   Email:    parent@rakshan.ai")
        print("   Password: password123")
        print("Devices: Aarav (Critical Risk 87.5), Ananya (Safe 12.0)")
        print("================================================")

if __name__ == "__main__":
    asyncio.run(seed())

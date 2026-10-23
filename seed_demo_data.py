import asyncio
import sys
from datetime import datetime, timedelta

try:
    if getattr(sys.stdout, "encoding", None) and sys.stdout.encoding.lower() != "utf-8":
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

        # Seed Multi-App Intercepted Notifications for Child Device
        print("[*] Seeding Multi-App Intercepted Notifications...")
        notif1 = ActivityLog(
            child_id=child1.id,
            app_name="WhatsApp",
            package_name="com.whatsapp",
            sender_alias="Rohan (Classmate)",
            text_content="Hey bro, are we playing football after tuition today at 5 PM?",
            analyzed_risk=5.0,
            sentiment_score=5.0,
            category="Safe Conversation",
            severity="SAFE",
            processed_at=datetime.utcnow() - timedelta(minutes=6)
        )
        notif2 = ActivityLog(
            child_id=child1.id,
            app_name="Instagram DM",
            package_name="com.instagram.android",
            sender_alias="unknown_shadow_99",
            text_content="Don't tell your mom about our chat. She doesn't understand you, send me a private selfie now.",
            analyzed_risk=87.5,
            sentiment_score=87.5,
            category="Grooming & Coercion",
            severity="CRITICAL",
            processed_at=datetime.utcnow() - timedelta(minutes=15)
        )
        notif3 = ActivityLog(
            child_id=child1.id,
            app_name="Discord",
            package_name="com.discord",
            sender_alias="GamerGroup_Bot",
            text_content="You are such a loser, nobody likes you in this school group. Stop texting here.",
            analyzed_risk=72.0,
            sentiment_score=72.0,
            category="Cyberbullying",
            severity="HIGH",
            processed_at=datetime.utcnow() - timedelta(hours=1, minutes=10)
        )
        notif4 = ActivityLog(
            child_id=child1.id,
            app_name="YouTube",
            package_name="com.google.android.youtube",
            sender_alias="Veritasium",
            text_content="New video upload: The Quantum Computing Revolution in 2026",
            analyzed_risk=2.0,
            sentiment_score=2.0,
            category="Educational",
            severity="SAFE",
            processed_at=datetime.utcnow() - timedelta(hours=2, minutes=20)
        )
        notif5 = ActivityLog(
            child_id=child1.id,
            app_name="SMS Messages",
            package_name="com.google.android.apps.messaging",
            sender_alias="School Alert / DPS",
            text_content="Dear Parent/Student, Annual Science Exhibition rehearsal begins tomorrow at 9 AM.",
            analyzed_risk=3.0,
            sentiment_score=3.0,
            category="Notice",
            severity="SAFE",
            processed_at=datetime.utcnow() - timedelta(hours=3, minutes=15)
        )
        notif6 = ActivityLog(
            child_id=child1.id,
            app_name="Snapchat",
            package_name="com.snapchat.android",
            sender_alias="Priya Sharma",
            text_content="Sent a new snap! 🔥 34 day streak",
            analyzed_risk=8.0,
            sentiment_score=8.0,
            category="Social / Casual",
            severity="SAFE",
            processed_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.add_all([notif1, notif2, notif3, notif4, notif5, notif6])
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

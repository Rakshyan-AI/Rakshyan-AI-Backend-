import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    role = Column(String, default="parent")  # parent, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    children = relationship("ChildDevice", back_populates="parent", cascade="all, delete-orphan")
    pairing_codes = relationship("PairingCode", back_populates="parent", cascade="all, delete-orphan")


class ChildDevice(Base):
    __tablename__ = "child_devices"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    parent_id = Column(String, ForeignKey("users.id"), nullable=False)
    device_id = Column(String, unique=True, index=True, nullable=False)  # Hardware/Install UUID
    child_name = Column(String, nullable=False)
    device_model = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    current_risk_score = Column(Float, default=0.0)
    current_status = Column(String, default="safe")  # safe, moderate, high, critical
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    parent = relationship("User", back_populates="children")
    incidents = relationship("SafetyIncident", back_populates="child", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="child", cascade="all, delete-orphan")


class PairingCode(Base):
    __tablename__ = "pairing_codes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    parent_id = Column(String, ForeignKey("users.id"), nullable=False)
    code = Column(String(8), unique=True, index=True, nullable=False)
    child_nickname = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    parent = relationship("User", back_populates="pairing_codes")


class SafetyIncident(Base):
    __tablename__ = "safety_incidents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    child_id = Column(String, ForeignKey("child_devices.id"), nullable=False)
    category = Column(String, nullable=False)  # grooming, bullying, distress, predator, scam
    risk_score = Column(Float, nullable=False)  # 0.0 - 100.0
    severity = Column(String, nullable=False)    # LOW, MEDIUM, HIGH, CRITICAL
    detected_reason = Column(Text, nullable=False)
    flagged_snippet = Column(Text, nullable=True)  # Redacted/anonymized snippet
    app_source = Column(String, nullable=True)    # WhatsApp, Instagram, Discord, SMS
    agent_breakdown = Column(JSON, nullable=True)  # Scores from individual micro-agents
    status = Column(String, default="new")        # new, acknowledged, reviewed, dismissed
    parent_acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    child = relationship("ChildDevice", back_populates="incidents")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    child_id = Column(String, ForeignKey("child_devices.id"), nullable=False)
    app_name = Column(String, nullable=False)
    sender_alias = Column(String, nullable=True)
    analyzed_risk = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    child = relationship("ChildDevice", back_populates="activity_logs")


class ComplianceAuditLog(Base):
    __tablename__ = "compliance_audit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String, nullable=False)  # INCIDENT_RECORDED, EVIDENCE_LOCKED, REPORT_GENERATED
    child_id = Column(String, nullable=True)
    parent_id = Column(String, nullable=True)
    incident_id = Column(String, nullable=True)
    legal_statute = Column(String, default="DPDP_ACT_2023_AND_POCSO")
    details = Column(JSON, nullable=True)
    hash_signature = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

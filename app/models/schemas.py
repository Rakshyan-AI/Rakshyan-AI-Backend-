from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str

# --- Pairing Schemas ---
class CreatePairingCodeRequest(BaseModel):
    child_nickname: str

class PairingCodeResponse(BaseModel):
    code: str
    child_nickname: str
    expires_at: datetime
    validity_minutes: int

class VerifyPairingCodeRequest(BaseModel):
    code: str
    device_id: str
    device_model: Optional[str] = "Android Device"
    os_version: Optional[str] = "Android 14"

class VerifyPairingCodeResponse(BaseModel):
    success: bool
    message: str
    child_id: str
    device_token: str
    child_name: str
    parent_name: str

class ChildDeviceResponse(BaseModel):
    id: str
    device_id: str
    child_name: str
    device_model: Optional[str]
    is_active: bool
    current_risk_score: float
    current_status: str
    last_sync_at: Optional[datetime]
    created_at: datetime

# --- Monitoring & Ingestion Schemas ---
class ActivityIngestRequest(BaseModel):
    device_id: str
    app_name: str  # WhatsApp, Instagram, Telegram, SMS, etc.
    package_name: Optional[str] = None
    sender: Optional[str] = "Anonymous"
    text_content: str
    context_type: Optional[str] = "incoming_message"  # incoming_message, notification

class ActivityLogResponse(BaseModel):
    id: str
    child_id: str
    child_name: Optional[str] = None
    app_name: str
    package_name: Optional[str] = None
    sender_alias: Optional[str] = None
    text_content: Optional[str] = None
    analyzed_risk: float = 0.0
    sentiment_score: float = 0.0
    category: Optional[str] = "Safe"
    severity: str = "SAFE"
    processed_at: datetime

class AgentScoreDetail(BaseModel):
    agent_name: str
    score: float
    confidence: float
    indicators: List[str]

class RiskAssessmentResult(BaseModel):
    overall_risk_score: float  # 0 to 100
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    category: str
    detected_reason: str
    recommended_action: str
    agent_breakdown: Dict[str, AgentScoreDetail]
    alert_triggered: bool

# --- Incident Schemas ---
class IncidentResponse(BaseModel):
    id: str
    child_id: str
    child_name: Optional[str] = None
    category: str
    risk_score: float
    severity: str
    detected_reason: str
    flagged_snippet: Optional[str]
    app_source: Optional[str]
    agent_breakdown: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    parent_acknowledged_at: Optional[datetime]

class IncidentAcknowledgeRequest(BaseModel):
    incident_id: str
    notes: Optional[str] = None

# --- Analytics Schemas ---
class DashboardOverviewResponse(BaseModel):
    total_linked_devices: int
    active_threats_count: int
    overall_family_safety_score: float
    recent_incidents: List[IncidentResponse]
    recent_notifications: List[ActivityLogResponse] = []
    category_distribution: Dict[str, int]

# --- Chat & Legal AI Schemas ---
class ChatHistoryItem(BaseModel):
    role: str  # user, assistant, system
    content: str

class ChatMessageRequest(BaseModel):
    message: str
    history: Optional[List[ChatHistoryItem]] = None
    child_context: Optional[Dict[str, Any]] = None

class HelplineInfo(BaseModel):
    name: str
    number: str
    purpose: str

class ChatMessageResponse(BaseModel):
    reply: str
    model: str
    provider: Optional[str] = "Groq LLaMA"
    relevant_laws: List[str] = []
    helplines: List[HelplineInfo] = []
    suggested_actions: List[str] = []
    action_command: Optional[str] = None
    child_telemetry: Optional[Dict[str, Any]] = None
    success: bool = True

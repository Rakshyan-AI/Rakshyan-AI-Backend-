import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Rakshan AI Core Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Secret Key for JWT & Hashes
    SECRET_KEY: str = os.getenv("SECRET_KEY", "rakshan_cyber_safety_super_secret_key_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./rakshan_dev.db")
    
    # Pairing Code
    PAIRING_CODE_LENGTH: int = 6
    PAIRING_CODE_EXPIRE_MINUTES: int = 15
    
    # Risk Thresholds (0 - 100)
    RISK_THRESHOLD_LOW: int = 25
    RISK_THRESHOLD_MEDIUM: int = 50
    RISK_THRESHOLD_HIGH: int = 70
    RISK_THRESHOLD_CRITICAL: int = 85

settings = Settings()

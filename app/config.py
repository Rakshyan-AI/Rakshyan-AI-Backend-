import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from backend/.env or cwd
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
load_dotenv()

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
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    
    # Pairing Code
    PAIRING_CODE_LENGTH: int = 6
    PAIRING_CODE_EXPIRE_MINUTES: int = 15
    
    # Risk Thresholds (0 - 100)
    RISK_THRESHOLD_LOW: int = 25
    RISK_THRESHOLD_MEDIUM: int = 50
    RISK_THRESHOLD_HIGH: int = 70
    RISK_THRESHOLD_CRITICAL: int = 85

    # Groq LLaMA AI Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

settings = Settings()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.api.auth import router as auth_router
from app.api.pairing import router as pairing_router
from app.api.monitor import router as monitor_router
from app.api.incidents import router as incidents_router
from app.api.analytics import router as analytics_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Multi-Agent AI Child Cyber-Safety, Risk Management & Legal Compliance Platform (Avishkar 2026)",
    lifespan=lifespan
)

# Enable permissive CORS for mobile and web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers under /api/v1
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(pairing_router, prefix=settings.API_PREFIX)
app.include_router(monitor_router, prefix=settings.API_PREFIX)
app.include_router(incidents_router, prefix=settings.API_PREFIX)
app.include_router(analytics_router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "compliance": ["DPDP Act 2023", "POCSO Act 2012", "IT Rules 2021"]
    }

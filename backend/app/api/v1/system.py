"""
System API endpoints.

Provides system status and configuration information.
"""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.database import is_database_encrypted

router = APIRouter()


class SystemStatusResponse(BaseModel):
    """System status response."""

    app_name: str
    version: str
    environment: str
    database_encrypted: bool
    ai_configured: bool
    appstore_configured: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    database: str
    services: dict


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get system status and configuration.

    Returns information about the current system configuration.
    """
    return SystemStatusResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment="development" if settings.debug else "production",
        database_encrypted=is_database_encrypted(),
        ai_configured=bool(settings.anthropic_api_key),
        appstore_configured=bool(
            settings.appstore_key_id and
            settings.appstore_issuer_id and
            settings.appstore_private_key_path
        ),
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns system health status for monitoring.
    """
    from app.database import SessionLocal

    # Check database
    db_status = "healthy"
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check services
    services = {
        "ai": "configured" if settings.anthropic_api_key else "not_configured",
        "appstore": "configured" if (
            settings.appstore_key_id and
            settings.appstore_issuer_id and
            settings.appstore_private_key_path
        ) else "not_configured",
        "encryption": "enabled" if is_database_encrypted() else "disabled",
    }

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.now(),
        database=db_status,
        services=services,
    )


@router.get("/config")
async def get_config():
    """
    Get non-sensitive configuration values.

    Returns public configuration for client apps.
    """
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "api_prefix": settings.api_prefix,
        "features": {
            "ai_enabled": bool(settings.anthropic_api_key),
            "appstore_enabled": bool(settings.appstore_key_id),
            "encryption_enabled": is_database_encrypted(),
        },
        "limits": {
            "max_file_upload_mb": 10,
            "claude_max_tokens": settings.claude_max_tokens,
        },
    }

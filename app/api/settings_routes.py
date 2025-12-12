"""FastAPI routes for settings management."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings, is_configured
from app.services.settings_persistence import (
    get_settings_persistence,
    CONFIGURABLE_SETTINGS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingValue(BaseModel):
    """A single setting value."""
    value: Optional[Any] = None
    has_value: bool = False
    label: str
    type: str
    sensitive: bool = False
    required: bool = False
    default: Optional[Any] = None
    min: Optional[float] = None
    max: Optional[float] = None
    description: str = ""


class SettingsResponse(BaseModel):
    """Response containing all settings."""
    settings: Dict[str, SettingValue]
    is_configured: bool
    missing_required: list[str]


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""
    settings: Dict[str, Any] = Field(
        ...,
        description="Dictionary of setting keys to values"
    )


class SettingsUpdateResponse(BaseModel):
    """Response from settings update."""
    success: bool
    updated: list[str]
    errors: Dict[str, str]


class ConfigStatusResponse(BaseModel):
    """Response for configuration status check."""
    is_configured: bool
    missing_required: list[str]
    message: str


@router.get("", response_model=SettingsResponse)
async def get_all_settings():
    """Get all configurable settings with their current values and metadata.

    Sensitive values (like API keys) are masked in the response.
    """
    persistence = get_settings_persistence()
    settings_data = persistence.get_all_with_metadata()

    # Check which required settings are missing
    missing = []
    for key, config in CONFIGURABLE_SETTINGS.items():
        if config["required"]:
            stored = persistence.get(key)
            if not stored:
                # Also check if set via env var
                current_settings = get_settings()
                env_value = getattr(current_settings, key, None)
                if not env_value:
                    missing.append(key)

    return SettingsResponse(
        settings={k: SettingValue(**v) for k, v in settings_data.items()},
        is_configured=is_configured(),
        missing_required=missing,
    )


@router.put("", response_model=SettingsUpdateResponse)
async def update_settings(request: SettingsUpdateRequest):
    """Update one or more settings.

    Settings are persisted to disk and will survive container restarts.
    """
    persistence = get_settings_persistence()
    updated = []
    errors = {}

    for key, value in request.settings.items():
        if key not in CONFIGURABLE_SETTINGS:
            errors[key] = f"Unknown setting: {key}"
            continue

        config = CONFIGURABLE_SETTINGS[key]

        # Validate value
        if value is None or value == "":
            # Allow clearing non-required settings
            if config["required"]:
                errors[key] = f"{key} is required and cannot be empty"
                continue
            # Delete the setting to revert to default
            persistence.delete(key)
            updated.append(key)
            continue

        # Type validation
        if config["type"] == "integer":
            try:
                int_value = int(value)
                if "min" in config and int_value < config["min"]:
                    errors[key] = f"{key} must be at least {config['min']}"
                    continue
                if "max" in config and int_value > config["max"]:
                    errors[key] = f"{key} must be at most {config['max']}"
                    continue
            except (ValueError, TypeError):
                errors[key] = f"{key} must be an integer"
                continue
        elif config["type"] == "float":
            try:
                float_value = float(value)
                if "min" in config and float_value < config["min"]:
                    errors[key] = f"{key} must be at least {config['min']}"
                    continue
                if "max" in config and float_value > config["max"]:
                    errors[key] = f"{key} must be at most {config['max']}"
                    continue
            except (ValueError, TypeError):
                errors[key] = f"{key} must be a number"
                continue

        # Store the value
        persistence.set(key, value)
        updated.append(key)

    return SettingsUpdateResponse(
        success=len(errors) == 0,
        updated=updated,
        errors=errors,
    )


@router.get("/status", response_model=ConfigStatusResponse)
async def get_config_status():
    """Check if the application is fully configured.

    Returns which required settings are missing.
    """
    persistence = get_settings_persistence()
    missing = []

    for key, config in CONFIGURABLE_SETTINGS.items():
        if config["required"]:
            # Check persisted value
            stored = persistence.get(key)
            if stored:
                continue

            # Check env var
            try:
                current_settings = get_settings()
                env_value = getattr(current_settings, key, None)
                if not env_value:
                    missing.append(key)
            except Exception:
                missing.append(key)

    configured = len(missing) == 0

    if configured:
        message = "All required settings are configured"
    else:
        message = f"Missing required settings: {', '.join(missing)}"

    return ConfigStatusResponse(
        is_configured=configured,
        missing_required=missing,
        message=message,
    )


@router.delete("/{key}")
async def delete_setting(key: str):
    """Delete a setting to revert to its default value.

    Args:
        key: The setting key to delete
    """
    if key not in CONFIGURABLE_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")

    config = CONFIGURABLE_SETTINGS[key]
    if config["required"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete required setting: {key}"
        )

    persistence = get_settings_persistence()
    persistence.delete(key)

    return {"success": True, "key": key, "message": f"Setting '{key}' reverted to default"}


@router.post("/restart")
async def restart_backend():
    """Restart the backend service to apply settings changes.

    This triggers a graceful restart of the FastAPI service, which will:
    1. Reload runtime settings from disk
    2. Regenerate GraphRAG settings.yaml
    3. Apply model and search configuration changes

    Returns immediately with success status; restart happens asynchronously.
    """
    import os
    import signal
    import asyncio

    async def delayed_restart():
        """Delay restart slightly to allow response to be sent."""
        await asyncio.sleep(0.5)
        # Send SIGHUP to trigger supervisor restart
        os.kill(os.getpid(), signal.SIGHUP)

    # Schedule the restart
    asyncio.create_task(delayed_restart())

    return {
        "success": True,
        "message": "Restart initiated. Service will reload in a moment."
    }


@router.post("/test-connection")
async def test_connections():
    """Test connections to Paperless and LiteLLM with current settings."""
    if not is_configured():
        raise HTTPException(
            status_code=400,
            detail="Application is not fully configured. Please set all required settings first."
        )

    settings = get_settings()
    results = {
        "paperless": {"success": False, "message": ""},
        "litellm": {"success": False, "message": ""},
    }

    # Test Paperless connection
    try:
        from app.clients.paperless import PaperlessClient
        async with PaperlessClient(settings) as client:
            ok = await client.health_check()
            results["paperless"]["success"] = ok
            results["paperless"]["message"] = "Connected successfully" if ok else "Health check failed"
    except Exception as e:
        results["paperless"]["message"] = str(e)

    # Test LiteLLM connection (simple request)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.litellm_base_url}/health",
                timeout=10.0,
            )
            if response.status_code == 200:
                results["litellm"]["success"] = True
                results["litellm"]["message"] = "Connected successfully"
            else:
                results["litellm"]["message"] = f"HTTP {response.status_code}"
    except Exception as e:
        results["litellm"]["message"] = str(e)

    return results

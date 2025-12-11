"""Settings persistence service for runtime configuration."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Settings that can be configured at runtime (sensitive ones marked)
CONFIGURABLE_SETTINGS = {
    # Connection settings
    "paperless_url": {"type": "string", "sensitive": False, "required": True, "label": "Paperless URL"},
    "paperless_token": {"type": "string", "sensitive": True, "required": True, "label": "Paperless API Token"},
    "litellm_base_url": {"type": "string", "sensitive": False, "required": True, "label": "LiteLLM Base URL"},
    "litellm_api_key": {"type": "string", "sensitive": True, "required": True, "label": "LiteLLM API Key"},

    # Model settings
    "indexing_model": {"type": "string", "sensitive": False, "required": False, "label": "Indexing Model", "default": "gpt-5-mini"},
    "query_model": {"type": "string", "sensitive": False, "required": False, "label": "Query Model", "default": "gpt-5-mini"},
    "embedding_model": {"type": "string", "sensitive": False, "required": False, "label": "Embedding Model", "default": "text-embedding-3-small"},

    # GraphRAG settings
    "chunk_size": {"type": "integer", "sensitive": False, "required": False, "label": "Chunk Size", "default": 1200, "min": 100, "max": 4000},
    "chunk_overlap": {"type": "integer", "sensitive": False, "required": False, "label": "Chunk Overlap", "default": 100, "min": 0, "max": 500},
    "community_level": {"type": "integer", "sensitive": False, "required": False, "label": "Community Level", "default": 2, "min": 0, "max": 10},

    # Rate limiting
    "concurrent_requests": {"type": "integer", "sensitive": False, "required": False, "label": "Concurrent Requests", "default": 100, "min": 1, "max": 1000},
    "requests_per_minute": {"type": "integer", "sensitive": False, "required": False, "label": "Requests per Minute", "default": 500, "min": 1, "max": 10000},
    "tokens_per_minute": {"type": "integer", "sensitive": False, "required": False, "label": "Tokens per Minute", "default": 2000000, "min": 1000, "max": 10000000},
}


class SettingsPersistence:
    """Service for persisting and loading runtime settings."""

    def __init__(self, settings_path: str = "/app/data/runtime_settings.json"):
        """Initialize settings persistence.

        Args:
            settings_path: Path to the settings JSON file
        """
        self.settings_path = Path(settings_path)
        self._cache: Optional[Dict[str, Any]] = None

    def _ensure_directory(self) -> None:
        """Ensure the settings directory exists."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load settings from disk.

        Returns:
            Dictionary of persisted settings
        """
        if self._cache is not None:
            return self._cache

        if self.settings_path.exists():
            try:
                with open(self.settings_path) as f:
                    self._cache = json.load(f)
                logger.info("Loaded runtime settings from %s", self.settings_path)
            except Exception as e:
                logger.warning("Failed to load runtime settings: %s", e)
                self._cache = {}
        else:
            self._cache = {}

        return self._cache

    def save(self, settings: Dict[str, Any]) -> None:
        """Save settings to disk.

        Args:
            settings: Settings dictionary to save
        """
        self._ensure_directory()

        # Validate settings before saving
        validated = {}
        for key, value in settings.items():
            if key in CONFIGURABLE_SETTINGS:
                config = CONFIGURABLE_SETTINGS[key]

                # Type conversion and validation
                if config["type"] == "integer" and value is not None:
                    try:
                        value = int(value)
                        if "min" in config and value < config["min"]:
                            value = config["min"]
                        if "max" in config and value > config["max"]:
                            value = config["max"]
                    except (ValueError, TypeError):
                        continue
                elif config["type"] == "string" and value is not None:
                    value = str(value).strip()
                    if not value:
                        continue

                validated[key] = value

        with open(self.settings_path, "w") as f:
            json.dump(validated, f, indent=2)

        self._cache = validated
        logger.info("Saved runtime settings to %s", self.settings_path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a single setting value.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        settings = self.load()
        return settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a single setting value.

        Args:
            key: Setting key
            value: Setting value
        """
        settings = self.load()
        settings[key] = value
        self.save(settings)

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple settings.

        Args:
            updates: Dictionary of settings to update
        """
        settings = self.load()
        settings.update(updates)
        self.save(settings)

    def delete(self, key: str) -> None:
        """Delete a setting (revert to default/env).

        Args:
            key: Setting key to delete
        """
        settings = self.load()
        if key in settings:
            del settings[key]
            self.save(settings)

    def get_all_with_metadata(self) -> Dict[str, Any]:
        """Get all settings with their metadata for the frontend.

        Returns:
            Dictionary with settings values and metadata
        """
        settings = self.load()
        result = {}

        for key, config in CONFIGURABLE_SETTINGS.items():
            value = settings.get(key)

            # Mask sensitive values
            if config["sensitive"] and value:
                masked_value = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "****"
            else:
                masked_value = value

            result[key] = {
                "value": masked_value,
                "has_value": value is not None and value != "",
                "label": config["label"],
                "type": config["type"],
                "sensitive": config["sensitive"],
                "required": config["required"],
                "default": config.get("default"),
                "min": config.get("min"),
                "max": config.get("max"),
            }

        return result

    def clear_cache(self) -> None:
        """Clear the settings cache to force reload from disk."""
        self._cache = None


# Global instance
_settings_persistence: Optional[SettingsPersistence] = None


def get_settings_persistence() -> SettingsPersistence:
    """Get the global settings persistence instance."""
    global _settings_persistence
    if _settings_persistence is None:
        _settings_persistence = SettingsPersistence()
    return _settings_persistence

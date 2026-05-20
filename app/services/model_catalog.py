"""LiteLLM model catalog helpers."""

import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.config import Settings

logger = logging.getLogger(__name__)


class AvailableModel(BaseModel):
    """A model exposed by LiteLLM for UI selection."""

    id: str
    display_name: str
    provider: Optional[str] = None
    provider_display_name: Optional[str] = None
    mode: str = "chat"
    upstream_model: Optional[str] = None


class AvailableModelsResponse(BaseModel):
    """Available models returned from LiteLLM."""

    models: List[AvailableModel]
    source: str


PROVIDER_LABELS = {
    "anthropic": "Anthropic",
    "bedrock": "Bedrock",
    "bedrock_converse": "Bedrock",
    "gemini": "Gemini",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
    "xai": "xAI",
}

WORD_LABELS = {
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "gpt": "GPT",
    "oauth": "OAuth",
    "openrouter": "OpenRouter",
    "pdf": "PDF",
    "rapidroute": "RapidRoute",
    "ui": "UI",
    "url": "URL",
    "xai": "xAI",
}


def _title_token(token: str) -> str:
    """Title-case one model name token without breaking common acronyms."""
    if token.lower() in WORD_LABELS:
        return WORD_LABELS[token.lower()]
    if token.isupper():
        return token
    return token[:1].upper() + token[1:]


def _merge_version_tokens(words: List[str]) -> List[str]:
    """Merge single-digit version fragments split by route-name hyphens."""
    merged = []
    index = 0
    while index < len(words):
        if (
            index + 1 < len(words)
            and words[index].isdigit()
            and words[index + 1].isdigit()
            and len(words[index]) == 1
            and len(words[index + 1]) == 1
        ):
            merged.append(f"{words[index]}.{words[index + 1]}")
            index += 2
        else:
            merged.append(words[index])
            index += 1
    return merged


def format_model_display_name(model_id: str, provider: Optional[str] = None) -> str:
    """Format a LiteLLM route name for display while preserving the raw ID elsewhere."""
    # Keep provider namespaces visible, but make them readable.
    segments = [segment for segment in model_id.split("/") if segment]
    if provider and segments and segments[0].lower() == provider.lower():
        segments = segments[1:]
    formatted_segments = []

    for segment in segments:
        words = _merge_version_tokens(re.split(r"[-_\s]+", segment))
        formatted_segments.append(" ".join(_title_token(word) for word in words if word))

    return " / ".join(formatted_segments) if formatted_segments else model_id


def _infer_mode(model_id: str, model_info: Dict[str, Any]) -> str:
    """Infer LiteLLM model mode when /model/info omits it."""
    mode = model_info.get("mode")
    if mode:
        return str(mode)

    lowered = model_id.lower()
    if "embedding" in lowered or "embed" in lowered:
        return "embedding"
    return "chat"


def _normalize_provider(provider: Optional[str]) -> Optional[str]:
    if not provider:
        return None
    return provider.replace("_converse", "")


def _model_from_info(item: Dict[str, Any]) -> Optional[AvailableModel]:
    """Build a UI-safe model option from LiteLLM /model/info data."""
    model_name = item.get("model_name")
    if not model_name:
        return None

    model_info = item.get("model_info") or {}
    litellm_params = item.get("litellm_params") or {}
    provider = _normalize_provider(
        model_info.get("litellm_provider") or litellm_params.get("custom_llm_provider")
    )

    return AvailableModel(
        id=str(model_name),
        display_name=format_model_display_name(str(model_name), provider=provider),
        provider=provider,
        provider_display_name=PROVIDER_LABELS.get(provider or ""),
        mode=_infer_mode(str(model_name), model_info),
        upstream_model=litellm_params.get("model") or model_info.get("key"),
    )


def _model_from_models_endpoint(item: Dict[str, Any]) -> Optional[AvailableModel]:
    """Build a model option from OpenAI-compatible /models data."""
    model_id = item.get("id")
    if not model_id:
        return None

    return AvailableModel(
        id=str(model_id),
        display_name=format_model_display_name(str(model_id)),
        mode=_infer_mode(str(model_id), {}),
    )


async def fetch_available_models(
    settings: Settings,
    mode: Optional[str] = None,
) -> AvailableModelsResponse:
    """Fetch available models from LiteLLM.

    Prefer /model/info because it includes the LiteLLM route name and model mode.
    Fall back to /models for keys that cannot read the richer endpoint.
    """
    if not settings.litellm_base_url:
        raise ValueError("LiteLLM base URL is not configured")

    headers = {}
    if settings.litellm_api_key:
        headers["Authorization"] = f"Bearer {settings.litellm_api_key}"

    base_url = settings.litellm_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{base_url}/model/info", headers=headers)
            response.raise_for_status()
            data = response.json()
            source = "model/info"
            models = [
                model
                for item in data.get("data", [])
                if isinstance(item, dict)
                for model in [_model_from_info(item)]
                if model is not None
            ]
        except Exception as exc:
            logger.info("Falling back to LiteLLM /models catalog: %s", exc)
            response = await client.get(f"{base_url}/models", headers=headers)
            response.raise_for_status()
            data = response.json()
            source = "models"
            models = [
                model
                for item in data.get("data", [])
                if isinstance(item, dict)
                for model in [_model_from_models_endpoint(item)]
                if model is not None
            ]

    if mode:
        models = [model for model in models if model.mode == mode]

    models.sort(key=lambda model: ((model.provider_display_name or model.provider or ""), model.display_name))
    return AvailableModelsResponse(models=models, source=source)

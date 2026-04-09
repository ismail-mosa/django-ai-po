import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.conf import settings


SETTINGS_KEY = "DJANGO_AI_PO"

_DEFAULTS = {
    "MODEL": None,
    "API_KEY": None,
    "API_BASE": None,
    "TEMPERATURE": 0.2,
    "BATCH_SIZE": 5,
    "WORKERS": 2,
    "MAX_RETRIES": 3,
    "TIMEOUT": 60,
    "MAX_TOKENS": 2000,
    "PROGRESS_BAR": True,
    "AUTO_SAVE_INTERVAL": 3,
    "LANGUAGES": {},
}


def _resolve_api_key(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, str) and raw.startswith("env:"):
        return os.environ.get(raw[4:])
    return raw


@dataclass
class LanguageConfig:
    validators: List[str] = field(default_factory=list)
    prompt_extra: str = ""
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None


class Conf:
    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    def _raw(cls) -> Dict[str, Any]:
        return getattr(settings, SETTINGS_KEY, {}) or {}

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        raw = cls._raw()
        if key in raw:
            return raw[key]
        return _DEFAULTS.get(key, default)

    @classmethod
    def model(cls) -> str:
        return cls.get("MODEL") or os.environ.get("LITELLM_MODEL", "openrouter/google/gemini-2.5-flash-lite")

    @classmethod
    def api_key(cls) -> Optional[str]:
        raw = cls.get("API_KEY")
        if raw:
            return _resolve_api_key(raw)
        for env_var in ("LITELLM_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
            val = os.environ.get(env_var)
            if val:
                return val
        return None

    @classmethod
    def api_base(cls) -> Optional[str]:
        raw = cls.get("API_BASE")
        if raw:
            return _resolve_api_key(raw) if raw.startswith("env:") else raw
        return os.environ.get("LITELLM_API_BASE")

    @classmethod
    def temperature(cls) -> float:
        return float(cls.get("TEMPERATURE", 0.2))

    @classmethod
    def batch_size(cls) -> int:
        return int(cls.get("BATCH_SIZE", 5))

    @classmethod
    def workers(cls) -> int:
        return int(cls.get("WORKERS", 2))

    @classmethod
    def max_retries(cls) -> int:
        return int(cls.get("MAX_RETRIES", 3))

    @classmethod
    def timeout(cls) -> int:
        return int(cls.get("TIMEOUT", 60))

    @classmethod
    def max_tokens(cls) -> int:
        return int(cls.get("MAX_TOKENS", 2000))

    @classmethod
    def progress_bar(cls) -> bool:
        return bool(cls.get("PROGRESS_BAR", True))

    @classmethod
    def auto_save_interval(cls) -> int:
        return int(cls.get("AUTO_SAVE_INTERVAL", 3))

    @classmethod
    def language_config(cls, lang_code: str) -> LanguageConfig:
        languages = cls.get("LANGUAGES", {})
        lang_data = languages.get(lang_code, languages.get(lang_code.lower(), {}))
        if not lang_data:
            for key, val in languages.items():
                if key.lower() == lang_code.lower():
                    lang_data = val
                    break
        return LanguageConfig(
            validators=lang_data.get("validators", []),
            prompt_extra=lang_data.get("prompt_extra", ""),
            system_prompt=lang_data.get("system_prompt"),
            user_prompt_template=lang_data.get("user_prompt_template"),
        )

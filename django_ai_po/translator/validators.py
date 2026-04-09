import re
from abc import ABC, abstractmethod
from importlib import import_module
from typing import Dict, List, Optional, Type

from django.core.exceptions import ImproperlyConfigured


class BaseValidator(ABC):
    name: str = ""

    @abstractmethod
    def validate(self, text: str, original: str) -> str: ...

    def warn(self, text: str, message: str) -> None:
        pass


class ArabicValidator(BaseValidator):
    name = "arabic"
    _ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

    def validate(self, text: str, original: str) -> str:
        if not text:
            return text

        has_arabic = bool(self._ARABIC_RE.search(text))
        if not has_arabic and self._ARABIC_RE.search(original) is None:
            self.warn(text, "Translation may not contain Arabic characters")

        text = re.sub(r"\s+", " ", text).strip()
        return text


class NoopValidator(BaseValidator):
    name = "noop"

    def validate(self, text: str, original: str) -> str:
        return text


class PlaceholderValidator(BaseValidator):
    name = "placeholder"
    _PLACEHOLDER_PATTERNS = [
        re.compile(r"%\(\w+\)[sd]"),
        re.compile(r"%[sd]"),
        re.compile(r"\{\{\w+\}\}"),
        re.compile(r"\{\w+\}"),
    ]

    def validate(self, text: str, original: str) -> str:
        for pattern in self._PLACEHOLDER_PATTERNS:
            original_placeholders = sorted(pattern.findall(original))
            translated_placeholders = sorted(pattern.findall(text))
            if original_placeholders != translated_placeholders:
                self.warn(
                    text,
                    f"Placeholder mismatch: original has {original_placeholders}, "
                    f"translation has {translated_placeholders}",
                )
        return text


class ValidatorRegistry:
    _registry: Dict[str, Type[BaseValidator]] = {
        "arabic": ArabicValidator,
        "ar": ArabicValidator,
        "placeholder": PlaceholderValidator,
        "noop": NoopValidator,
    }

    @classmethod
    def register(cls, name: str, validator_class: Type[BaseValidator]) -> None:
        cls._registry[name] = validator_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseValidator]]:
        return cls._registry.get(name)

    @classmethod
    def get_by_dotted_path(cls, dotted_path: str) -> BaseValidator:
        if "." in dotted_path:
            try:
                module_path, class_name = dotted_path.rsplit(".", 1)
                module = import_module(module_path)
                validator_class = getattr(module, class_name)
                if not issubclass(validator_class, BaseValidator):
                    raise ImproperlyConfigured(f"{dotted_path} is not a subclass of BaseValidator")
                return validator_class()
            except (ImportError, AttributeError) as e:
                raise ImproperlyConfigured(f"Could not import validator {dotted_path}: {e}")

        validator_class = cls.get(dotted_path)
        if validator_class is None:
            raise ImproperlyConfigured(f"Unknown validator: {dotted_path}")
        return validator_class()

    @classmethod
    def build_chain(cls, validator_specs: List[str]) -> List[BaseValidator]:
        validators = []
        for spec in validator_specs:
            validators.append(cls.get_by_dotted_path(spec))
        return validators


def validate_translation(text: str, original: str, validators: List[BaseValidator]) -> str:
    for v in validators:
        text = v.validate(text, original)
    return text

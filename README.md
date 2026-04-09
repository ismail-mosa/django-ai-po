# django-ai-po

AI-powered `.po` file translator for Django using LiteLLM.

## Features

- Translate Django `.po` files using any LLM supported by [LiteLLM](https://github.com/BerriAI/litellm) (OpenAI, Anthropic, OpenRouter, Ollama, etc.)
- Plural form support (msgid_plural with msgstr[0], msgstr[1], ...)
- Auto-discover `.po` files in locale directories
- Customizable prompt templates per language
- Extensible validation system (built-in Arabic validator, placeholder validator)
- Progress bar via [Rich](https://github.com/Textualize/rich)
- Auto-save progress during translation
- Dry-run mode for previewing
- JSON output for CI/CD

## Installation

```bash
pip install django-ai-po
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "django_ai_po",
]
```

## Configuration

Add to your Django settings:

```python
DJANGO_AI_PO = {
    "MODEL": "openrouter/google/gemini-2.5-flash-lite",
    "API_KEY": "env:OPENROUTER_API_KEY",  # or a literal string
    "TEMPERATURE": 0.2,
    "BATCH_SIZE": 5,
    "WORKERS": 2,
    "LANGUAGES": {
        "ar": {
            "validators": ["arabic"],
            "prompt_extra": "Use Saudi Arabian healthcare terminology...",
        },
    },
}
```

## Usage

```bash
# Translate a single file
python manage.py translate_po locale/ar/LC_MESSAGES/django.po --lang Arabic

# Auto-discover all .po files for a language
python manage.py translate_po --discover --lang Arabic

# Use a specific model
python manage.py translate_po locale/ar/LC_MESSAGES/django.po --lang Arabic --model anthropic/claude-sonnet-4-20250514

# Dry run (preview without saving)
python manage.py translate_po locale/ar/LC_MESSAGES/django.po --lang Arabic --dry-run

# JSON output for CI/CD
python manage.py translate_po locale/ar/LC_MESSAGES/django.po --lang Arabic --output-format json
```

## Custom Validators

```python
from django_ai_po.translator.validators import BaseValidator

class MyValidator(BaseValidator):
    name = "my_validator"

    def validate(self, text: str, original: str) -> str:
        # Your validation logic
        return text
```

Register it:

```python
from django_ai_po.translator.validators import ValidatorRegistry

ValidatorRegistry.register("my_validator", MyValidator)
```

Then use in settings:

```python
DJANGO_AI_PO = {
    "LANGUAGES": {
        "ar": {
            "validators": ["arabic", "myapp.validators.MyValidator"],
        },
    },
}
```

## License

MIT

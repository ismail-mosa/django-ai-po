SECRET_KEY = "test-secret-key-for-django-ai-po"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_ai_po",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
LOCALE_PATHS = []
USE_I18N = True
DJANGO_AI_PO = {
    "MODEL": "test/fake-model",
    "API_KEY": "test-key",
    "TEMPERATURE": 0.2,
    "BATCH_SIZE": 5,
    "WORKERS": 1,
}

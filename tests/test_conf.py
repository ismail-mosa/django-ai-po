import os

from django_ai_po.conf import Conf, _resolve_api_key


class TestResolveApiKey:
    def test_literal_string(self):
        assert _resolve_api_key("sk-test123") == "sk-test123"

    def test_env_variable(self):
        os.environ["MY_TEST_KEY"] = "sk-from-env"
        assert _resolve_api_key("env:MY_TEST_KEY") == "sk-from-env"
        del os.environ["MY_TEST_KEY"]

    def test_none(self):
        assert _resolve_api_key(None) is None

    def test_env_not_set(self):
        assert _resolve_api_key("env:NONEXISTENT_VAR_XYZ") is None


class TestConf:
    def test_model_default(self):
        assert Conf.model() is not None

    def test_api_key_from_settings(self):
        assert Conf.api_key() == "test-key"

    def test_temperature(self):
        assert Conf.temperature() == 0.2

    def test_batch_size(self):
        assert Conf.batch_size() == 5

    def test_workers(self):
        assert Conf.workers() == 1

    def test_language_config_default(self):
        config = Conf.language_config("ar")
        assert config.validators == []
        assert config.prompt_extra == ""

    def test_language_config_with_settings(self):
        from django.conf import settings

        original = getattr(settings, "DJANGO_AI_PO", {})
        settings.DJANGO_AI_PO = {
            **original,
            "LANGUAGES": {
                "ar": {
                    "validators": ["arabic"],
                    "prompt_extra": "Use Saudi dialect",
                }
            },
        }
        config = Conf.language_config("ar")
        assert config.validators == ["arabic"]
        assert config.prompt_extra == "Use Saudi dialect"
        settings.DJANGO_AI_PO = original

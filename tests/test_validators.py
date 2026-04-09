from django_ai_po.translator.validators import (
    ArabicValidator,
    BaseValidator,
    NoopValidator,
    PlaceholderValidator,
    ValidatorRegistry,
    validate_translation,
)


class TestArabicValidator:
    def test_passes_arabic_text(self):
        v = ArabicValidator()
        result = v.validate("مرحبا بالعالم", "Hello world")
        assert result == "مرحبا بالعالم"

    def test_cleans_whitespace(self):
        v = ArabicValidator()
        result = v.validate("مرحبا   بالعالم", "Hello world")
        assert result == "مرحبا بالعالم"

    def test_empty_string(self):
        v = ArabicValidator()
        assert v.validate("", "Hello") == ""


class TestPlaceholderValidator:
    def test_matching_placeholders(self):
        v = PlaceholderValidator()
        result = v.validate("مرحبا %(name)s", "Hello %(name)s")
        assert result == "مرحبا %(name)s"

    def test_curly_brace_placeholders(self):
        v = PlaceholderValidator()
        result = v.validate("مرحبا {name}", "Hello {name}")
        assert result == "مرحبا {name}"


class TestValidatorRegistry:
    def test_get_known_validator(self):
        cls = ValidatorRegistry.get("arabic")
        assert cls is ArabicValidator

    def test_get_by_lang_code(self):
        cls = ValidatorRegistry.get("ar")
        assert cls is ArabicValidator

    def test_get_unknown(self):
        assert ValidatorRegistry.get("nonexistent") is None

    def test_register_custom(self):
        class MyValidator(BaseValidator):
            name = "custom_test"

            def validate(self, text, original):
                return text.upper()

        ValidatorRegistry.register("custom_test", MyValidator)
        assert ValidatorRegistry.get("custom_test") is MyValidator

    def test_build_chain(self):
        chain = ValidatorRegistry.build_chain(["noop", "placeholder"])
        assert len(chain) == 2
        assert isinstance(chain[0], NoopValidator)
        assert isinstance(chain[1], PlaceholderValidator)


class TestValidateTranslation:
    def test_applies_chain(self):
        noop = NoopValidator()
        result = validate_translation("hello", "Hello", [noop])
        assert result == "hello"

    def test_empty_chain(self):
        result = validate_translation("hello", "Hello", [])
        assert result == "hello"

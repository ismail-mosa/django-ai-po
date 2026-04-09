from django_ai_po.translator.prompts import PromptBuilder


class TestPromptBuilder:
    def test_default_system_prompt(self):
        builder = PromptBuilder(target_lang="Arabic", context="healthcare")
        prompt = builder.system_prompt()
        assert "Arabic" in prompt
        assert "healthcare" in prompt
        assert "JSON array" in prompt

    def test_arabic_specific_instructions(self):
        builder = PromptBuilder(target_lang="Arabic")
        prompt = builder.system_prompt()
        assert "Modern Standard Arabic" in prompt

    def test_custom_system_prompt(self):
        builder = PromptBuilder(
            target_lang="Arabic",
            custom_system_prompt="Custom prompt for {lang}",
        )
        assert builder.system_prompt() == "Custom prompt for {lang}"

    def test_prompt_extra(self):
        builder = PromptBuilder(
            target_lang="Arabic",
            lang_prompt_extra="Use Saudi dialect",
        )
        prompt = builder.system_prompt()
        assert "Use Saudi dialect" in prompt

    def test_singular_user_prompt(self):
        builder = PromptBuilder(target_lang="French")
        texts = [{"text": "Hello", "context": "greeting"}]
        prompt = builder.user_prompt(texts, is_plural=False)
        assert "French" in prompt
        assert "Hello" in prompt

    def test_plural_user_prompt(self):
        builder = PromptBuilder(target_lang="French")
        texts = [{"singular": "cat", "plural": "cats", "num_forms": 2}]
        prompt = builder.user_prompt(texts, is_plural=True)
        assert "plural" in prompt.lower()

    def test_french_instructions(self):
        builder = PromptBuilder(target_lang="French")
        prompt = builder.system_prompt()
        assert "French" in prompt

    def test_unknown_lang_no_extra(self):
        builder = PromptBuilder(target_lang="Swahili")
        prompt = builder.system_prompt()
        assert "Swahili" in prompt

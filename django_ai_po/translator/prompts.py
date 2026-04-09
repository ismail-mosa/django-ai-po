from typing import Dict, List, Optional


class PromptBuilder:
    def __init__(
        self,
        target_lang: str,
        context: str = "software",
        lang_prompt_extra: str = "",
        custom_system_prompt: Optional[str] = None,
        custom_user_template: Optional[str] = None,
    ):
        self.target_lang = target_lang
        self.context = context
        self.lang_prompt_extra = lang_prompt_extra
        self.custom_system_prompt = custom_system_prompt
        self.custom_user_template = custom_user_template

    def system_prompt(self) -> str:
        if self.custom_system_prompt:
            return self.custom_system_prompt

        prompt = f"""You are a professional translator specializing in {self.context} software localization.

CRITICAL RULES:
1. Translate from English to {self.target_lang}
2. Return ONLY a JSON array of translated strings
3. Preserve ALL variables exactly: %(name)s, {{variable}}, %s, {{placeholder}}, etc.
4. Preserve HTML tags (<strong>, <a>, <em>, etc.) - translate only the text inside them
5. Preserve newlines (\\n) and formatting characters
6. Maintain the same array length and order as input
7. If a string should NOT be translated (brand names, technical IDs), return it unchanged"""

        lang_specific = self._lang_specific_instructions()
        if lang_specific:
            prompt += "\n\n" + lang_specific

        if self.lang_prompt_extra:
            prompt += "\n\n" + self.lang_prompt_extra

        return prompt

    def user_prompt(self, texts: List[Dict], is_plural: bool = False) -> str:
        if self.custom_user_template:
            return self.custom_user_template.format(
                target_lang=self.target_lang,
                texts=texts,
            )

        if is_plural:
            return self._plural_user_prompt(texts)

        return self._singular_user_prompt(texts)

    def _singular_user_prompt(self, texts: List[Dict]) -> str:
        import json

        return f"""Translate these texts to {self.target_lang}.

Input format: JSON array with text and optional context
Output format: JSON array of translated strings only

Texts to translate:
{json.dumps(texts, ensure_ascii=False, indent=2)}

Return ONLY the JSON array of translations."""

    def _plural_user_prompt(self, texts: List[Dict]) -> str:
        import json

        return f"""Translate these plural form texts to {self.target_lang}.

Input format: JSON array of objects, each with "singular", "plural", "context", and "num_forms" (number of plural forms needed)
Output format: JSON array of arrays, where each inner array contains the plural form translations in order (form 0, form 1, ...)

Texts to translate:
{json.dumps(texts, ensure_ascii=False, indent=2)}

Return ONLY the JSON array of arrays of translations."""

    def _lang_specific_instructions(self) -> str:
        instructions = {
            "arabic": """
ARABIC TRANSLATION REQUIREMENTS:
- Use Modern Standard Arabic - formal, professional
- Maintain professional, respectful tone
- Ensure grammatical correctness and natural flow
- Do not use colloquial Arabic
- Numbers and dates should follow Arabic conventions where appropriate
- Keep English technical terms if no standard Arabic equivalent exists (e.g., API, URL)""",
            "french": """
FRENCH TRANSLATION REQUIREMENTS:
- Use standard French (not regional variants unless specified)
- Maintain formal tone (vous form)
- Respect French punctuation spacing rules""",
            "spanish": """
SPANISH TRANSLATION REQUIREMENTS:
- Use neutral/international Spanish where possible
- Maintain formal tone (usted form)
- Be consistent with terminology""",
            "german": """
GERMAN TRANSLATION REQUIREMENTS:
- Use standard German (Hochdeutsch)
- Maintain formal tone (Sie form)
- Compound words should follow German conventions""",
            "japanese": """
JAPANESE TRANSLATION REQUIREMENTS:
- Use polite form (desu/masu) for UI text
- Technical terms may use katakana
- Maintain appropriate formality level""",
            "chinese": """
CHINESE TRANSLATION REQUIREMENTS:
- Use Simplified Chinese by default
- Technical terms should follow industry standards
- Maintain concise, professional tone""",
        }

        lang_lower = self.target_lang.lower()
        for key, instruction in instructions.items():
            if key in lang_lower:
                return instruction

        return ""

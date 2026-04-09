import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

import polib
from litellm import completion
from litellm.exceptions import APIConnectionError, RateLimitError, Timeout

from django_ai_po.conf import Conf
from django_ai_po.plural import (
    apply_plural_translations,
    get_plural_count,
    separate_entries,
)
from django_ai_po.translator.prompts import PromptBuilder
from django_ai_po.translator.validators import (
    BaseValidator,
    ValidatorRegistry,
    validate_translation,
)

logger = logging.getLogger("django_ai_po")

LANG_CODE_MAP = {
    "arabic": "ar",
    "french": "fr",
    "spanish": "es",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "japanese": "ja",
    "chinese": "zh",
    "korean": "ko",
    "russian": "ru",
    "turkish": "tr",
    "dutch": "nl",
    "polish": "pl",
    "czech": "cs",
    "swedish": "sv",
    "norwegian": "no",
    "danish": "da",
    "finnish": "fi",
    "hebrew": "he",
    "hindi": "hi",
    "thai": "th",
    "vietnamese": "vi",
    "indonesian": "id",
    "malay": "ms",
    "ukrainian": "uk",
    "romanian": "ro",
    "hungarian": "hu",
    "greek": "el",
}


def resolve_lang_code(lang: str) -> str:
    return LANG_CODE_MAP.get(lang.lower(), lang.lower())


class TranslationResult:
    def __init__(self):
        self.total: int = 0
        self.success: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: List[str] = []

    @property
    def success_rate(self) -> float:
        return (self.success / self.total * 100) if self.total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": round(self.success_rate, 1),
            "errors": self.errors,
        }


class POTranslator:
    def __init__(
        self,
        target_lang: str,
        context: str = "software",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: Optional[float] = None,
        batch_size: Optional[int] = None,
        workers: Optional[int] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        max_tokens: Optional[int] = None,
        auto_save_interval: Optional[int] = None,
        custom_validators: Optional[List[BaseValidator]] = None,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None,
    ):
        self.target_lang = target_lang
        self.lang_code = resolve_lang_code(target_lang)
        self.context = context
        self.model = model or Conf.model()
        self.api_key = api_key or Conf.api_key()
        self.api_base = api_base or Conf.api_base()
        self.temperature = temperature if temperature is not None else Conf.temperature()
        self.batch_size = batch_size or Conf.batch_size()
        self.workers = workers or Conf.workers()
        self.max_retries = max_retries or Conf.max_retries()
        self.timeout = timeout or Conf.timeout()
        self.max_tokens = max_tokens or Conf.max_tokens()
        self.auto_save_interval = auto_save_interval or Conf.auto_save_interval()
        self.progress_callback = progress_callback
        self.log_callback = log_callback or logger.info

        lang_config = Conf.language_config(self.lang_code)
        self.validators = custom_validators or self._build_validators(lang_config.validators)
        self.prompt_builder = PromptBuilder(
            target_lang=target_lang,
            context=context,
            lang_prompt_extra=lang_config.prompt_extra,
            custom_system_prompt=lang_config.system_prompt,
            custom_user_template=lang_config.user_prompt_template,
        )

    def _build_validators(self, specs: List[str]) -> List[BaseValidator]:
        if not specs:
            return []
        return ValidatorRegistry.build_chain(specs)

    def _log(self, message: str) -> None:
        self.log_callback(message)

    def translate_file(
        self,
        po_file_path: str,
        fix_fuzzy: bool = False,
        dry_run: bool = False,
        force: bool = False,
    ) -> TranslationResult:
        result = TranslationResult()

        po = self._load_po(po_file_path)
        if po is None:
            result.errors.append(f"Could not load {po_file_path}")
            return result

        entries = self._filter_entries(po, fix_fuzzy, force)
        result.total = len(entries)

        if result.total == 0:
            self._log("No entries to translate.")
            return result

        num_plural_forms = get_plural_count(po)
        singular_entries, plural_entries, singular_payloads, plural_payloads = separate_entries(
            entries, num_plural_forms
        )

        success = 0
        batches_saved = 0

        if singular_payloads:
            s_success = self._process_singular(singular_entries, singular_payloads, po, dry_run, result)
            success += s_success
            batches_saved += len(s_singular_entries := singular_entries) // self.batch_size

        if plural_payloads:
            p_success = self._process_plural(plural_entries, plural_payloads, po, dry_run, num_plural_forms, result)
            success += p_success

        result.success = success
        result.failed = result.total - success

        if not dry_run and result.success > 0:
            po.save()
            self._log(f"Saved {po_file_path}")

        return result

    def _process_singular(
        self,
        entries: List[polib.POEntry],
        payloads: List[Dict],
        po: polib.POFile,
        dry_run: bool,
        result: TranslationResult,
    ) -> int:
        batches = list(self._chunked(entries, self.batch_size))
        payload_batches = list(self._chunked(payloads, self.batch_size))
        total_batches = len(batches)
        success = 0
        batches_since_save = 0

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._translate_singular_batch, payload_batches[i], i + 1, total_batches): (
                    batches[i],
                    i,
                )
                for i in range(total_batches)
            }
            for future in as_completed(futures):
                batch_entries, idx = futures[future]
                try:
                    translations = future.result()
                    if translations is not None:
                        for entry, trans in zip(batch_entries, translations):
                            if self.validators:
                                trans = validate_translation(trans, entry.msgid, self.validators)
                            if not dry_run:
                                entry.msgstr = trans
                                if "fuzzy" in entry.flags:
                                    entry.flags.remove("fuzzy")
                        success += len(batch_entries)
                        batches_since_save += 1
                        if not dry_run and batches_since_save >= self.auto_save_interval:
                            po.save()
                            batches_since_save = 0
                            self._log("Auto-saved progress")
                    else:
                        result.errors.append(f"Singular batch {idx + 1} failed")
                except Exception as e:
                    result.errors.append(f"Singular batch {idx + 1} error: {e}")

                if self.progress_callback:
                    self.progress_callback(success, len(entries))

        return success

    def _process_plural(
        self,
        entries: List[polib.POEntry],
        payloads: List[Dict],
        po: polib.POFile,
        dry_run: bool,
        num_forms: int,
        result: TranslationResult,
    ) -> int:
        batches = list(self._chunked(entries, self.batch_size))
        payload_batches = list(self._chunked(payloads, self.batch_size))
        total_batches = len(batches)
        success = 0

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._translate_plural_batch, payload_batches[i], num_forms, i + 1, total_batches): (
                    batches[i],
                    i,
                )
                for i in range(total_batches)
            }
            for future in as_completed(futures):
                batch_entries, idx = futures[future]
                try:
                    translations_list = future.result()
                    if translations_list is not None:
                        for entry, form_translations in zip(batch_entries, translations_list):
                            if self.validators:
                                form_translations = [
                                    validate_translation(t, entry.msgid, self.validators) for t in form_translations
                                ]
                            if not dry_run:
                                apply_plural_translations(entry, form_translations)
                        success += len(batch_entries)
                    else:
                        result.errors.append(f"Plural batch {idx + 1} failed")
                except Exception as e:
                    result.errors.append(f"Plural batch {idx + 1} error: {e}")

                if self.progress_callback:
                    self.progress_callback(success, len(entries))

        return success

    def _translate_singular_batch(
        self, payloads: List[Dict], batch_num: int, total_batches: int
    ) -> Optional[List[str]]:
        system_prompt = self.prompt_builder.system_prompt()
        user_prompt = self.prompt_builder.user_prompt(payloads, is_plural=False)
        content = self._call_llm(system_prompt, user_prompt, batch_num, total_batches)
        if content is None:
            return None
        return self._parse_singular_response(content, len(payloads))

    def _translate_plural_batch(
        self,
        payloads: List[Dict],
        num_forms: int,
        batch_num: int,
        total_batches: int,
    ) -> Optional[List[List[str]]]:
        system_prompt = self.prompt_builder.system_prompt()
        user_prompt = self.prompt_builder.user_prompt(payloads, is_plural=True)
        content = self._call_llm(system_prompt, user_prompt, batch_num, total_batches)
        if content is None:
            return None
        return self._parse_plural_response(content, len(payloads), num_forms)

    def _call_llm(self, system_prompt: str, user_prompt: str, batch_num: int, total_batches: int) -> Optional[str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        for attempt in range(self.max_retries):
            try:
                response = completion(**kwargs)
                return response.choices[0].message.content
            except (RateLimitError, APIConnectionError, Timeout) as e:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "Batch %d/%d: retry %d/%d after %ds: %s",
                    batch_num,
                    total_batches,
                    attempt + 1,
                    self.max_retries,
                    wait,
                    e,
                )
                time.sleep(wait)
            except Exception as e:
                logger.error("Batch %d/%d: unexpected error: %s", batch_num, total_batches, e)
                return None

        logger.error("Batch %d/%d: max retries exceeded", batch_num, total_batches)
        return None

    def _parse_singular_response(self, content: str, expected: int) -> Optional[List[str]]:
        parsed = self._extract_json(content)
        if parsed is None:
            return None
        if not isinstance(parsed, list):
            logger.error("Response is not a JSON array")
            return None
        if len(parsed) != expected:
            logger.error("Count mismatch: expected %d, got %d", expected, len(parsed))
            return None
        return parsed

    def _parse_plural_response(self, content: str, expected_entries: int, num_forms: int) -> Optional[List[List[str]]]:
        parsed = self._extract_json(content)
        if parsed is None:
            return None
        if not isinstance(parsed, list):
            logger.error("Plural response is not a JSON array")
            return None
        if len(parsed) != expected_entries:
            logger.error(
                "Plural count mismatch: expected %d entries, got %d",
                expected_entries,
                len(parsed),
            )
            return None
        for i, item in enumerate(parsed):
            if not isinstance(item, list):
                logger.error("Plural form %d is not an array", i)
                return None
            if len(item) != num_forms:
                logger.warning("Plural form %d: expected %d forms, got %d", i, num_forms, len(item))
        return parsed

    @staticmethod
    def _extract_json(content: str) -> Optional[Any]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.error("Could not parse JSON from response")
            return None

    def _load_po(self, path: str) -> Optional[polib.POFile]:
        try:
            return polib.pofile(path)
        except Exception as e:
            logger.error("Could not load %s: %s", path, e)
            return None

    @staticmethod
    def _filter_entries(po: polib.POFile, fix_fuzzy: bool, force: bool) -> List[polib.POEntry]:
        entries = []
        for entry in po:
            if entry.obsolete:
                continue
            if force:
                entries.append(entry)
            elif not entry.msgstr.strip():
                entries.append(entry)
            elif fix_fuzzy and "fuzzy" in entry.flags:
                entries.append(entry)
        return entries

    @staticmethod
    def _chunked(lst: List, size: int):
        for i in range(0, len(lst), size):
            yield lst[i : i + size]

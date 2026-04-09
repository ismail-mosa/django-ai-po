import json

from django_ai_po.translator.base import POTranslator


class TestExtractJson:
    def test_plain_json_array(self):
        result = POTranslator._extract_json('["hello", "world"]')
        assert result == ["hello", "world"]

    def test_json_with_markdown_block(self):
        content = '```json\n["hello", "world"]\n```'
        result = POTranslator._extract_json(content)
        assert result == ["hello", "world"]

    def test_json_with_generic_code_block(self):
        content = '```\n["hello"]\n```'
        result = POTranslator._extract_json(content)
        assert result == ["hello"]

    def test_json_embedded_in_text(self):
        content = 'Here are the translations:\n["hello", "world"]\nDone.'
        result = POTranslator._extract_json(content)
        assert result == ["hello", "world"]

    def test_invalid_json(self):
        result = POTranslator._extract_json("not json at all")
        assert result is None

    def test_nested_json(self):
        content = '[["a", "b"], ["c", "d"]]'
        result = POTranslator._extract_json(content)
        assert result == [["a", "b"], ["c", "d"]]

    def test_unicode_json(self):
        content = '["مرحبا", "عالم"]'
        result = POTranslator._extract_json(content)
        assert result == ["مرحبا", "عالم"]


class TestParseSingularResponse:
    def setup_method(self):
        self.translator = _make_translator()

    def test_valid_response(self):
        content = '["translation1", "translation2"]'
        result = self.translator._parse_singular_response(content, 2)
        assert result == ["translation1", "translation2"]

    def test_count_mismatch(self):
        content = '["only_one"]'
        result = self.translator._parse_singular_response(content, 2)
        assert result is None

    def test_not_array(self):
        content = '{"key": "value"}'
        result = self.translator._parse_singular_response(content, 1)
        assert result is None


class TestParsePluralResponse:
    def setup_method(self):
        self.translator = _make_translator()

    def test_valid_plural_response(self):
        content = '[["zero a", "plural a"], ["zero b", "plural b"]]'
        result = self.translator._parse_plural_response(content, 2, 2)
        assert result == [["zero a", "plural a"], ["zero b", "plural b"]]

    def test_count_mismatch(self):
        content = '[["zero"]]'
        result = self.translator._parse_plural_response(content, 2, 1)
        assert result is None

    def test_inner_not_array(self):
        content = '["not an array"]'
        result = self.translator._parse_plural_response(content, 1, 2)
        assert result is None


class TestFilterEntries:
    def test_filters_obsolete(self):
        import polib

        po = polib.POFile()
        e1 = polib.POEntry(msgid="hello", msgstr="")
        e2 = polib.POEntry(msgid="obsolete", msgstr="", obsolete=True)
        po.append(e1)
        po.append(e2)
        result = POTranslator._filter_entries(po, fix_fuzzy=False, force=False)
        assert len(result) == 1
        assert result[0].msgid == "hello"

    def test_empty_msgstr(self):
        import polib

        po = polib.POFile()
        e = polib.POEntry(msgid="hello", msgstr="")
        po.append(e)
        result = POTranslator._filter_entries(po, fix_fuzzy=False, force=False)
        assert len(result) == 1

    def test_already_translated_skipped(self):
        import polib

        po = polib.POFile()
        e = polib.POEntry(msgid="hello", msgstr="مرحبا")
        po.append(e)
        result = POTranslator._filter_entries(po, fix_fuzzy=False, force=False)
        assert len(result) == 0

    def test_force_includes_all(self):
        import polib

        po = polib.POFile()
        e = polib.POEntry(msgid="hello", msgstr="already done")
        po.append(e)
        result = POTranslator._filter_entries(po, fix_fuzzy=False, force=True)
        assert len(result) == 1

    def test_fix_fuzzy(self):
        import polib

        po = polib.POFile()
        e = polib.POEntry(msgid="hello", msgstr="old translation", flags=["fuzzy"])
        po.append(e)
        result = POTranslator._filter_entries(po, fix_fuzzy=True, force=False)
        assert len(result) == 1

    def test_fix_fuzzy_false_skips_fuzzy(self):
        import polib

        po = polib.POFile()
        e = polib.POEntry(msgid="hello", msgstr="old", flags=["fuzzy"])
        po.append(e)
        result = POTranslator._filter_entries(po, fix_fuzzy=False, force=False)
        assert len(result) == 0


class TestChunked:
    def test_even_split(self):
        result = list(POTranslator._chunked([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_remainder(self):
        result = list(POTranslator._chunked([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_empty(self):
        result = list(POTranslator._chunked([], 3))
        assert result == []


class TestResolveLangCode:
    def test_full_name(self):
        from django_ai_po.translator.base import resolve_lang_code

        assert resolve_lang_code("Arabic") == "ar"

    def test_already_code(self):
        from django_ai_po.translator.base import resolve_lang_code

        assert resolve_lang_code("ar") == "ar"

    def test_unknown(self):
        from django_ai_po.translator.base import resolve_lang_code

        assert resolve_lang_code("Klingon") == "klingon"


def _make_translator(**kwargs):
    defaults = {
        "target_lang": "Arabic",
        "api_key": "test-key",
        "model": "test/model",
    }
    defaults.update(kwargs)
    return POTranslator(**defaults)

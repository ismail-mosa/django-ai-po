import polib

from django_ai_po.plural import (
    _match_msgid_whitespace,
    apply_plural_translations,
    build_plural_payload,
    get_plural_count,
    is_plural_entry,
    separate_entries,
)


class TestGetPluralCount:
    def test_from_metadata(self):
        po = polib.POFile()
        po.metadata["Plural-Forms"] = "nplurals=3; plural=(n==0 ? 0 : n==1 ? 1 : 2)"
        assert get_plural_count(po) == 3

    def test_default(self):
        po = polib.POFile()
        assert get_plural_count(po) == 2

    def test_no_header(self):
        po = polib.POFile()
        po.metadata = {}
        assert get_plural_count(po) == 2


class TestIsPluralEntry:
    def test_plural(self):
        e = polib.POEntry(msgid="cat", msgid_plural="cats")
        assert is_plural_entry(e) is True

    def test_singular(self):
        e = polib.POEntry(msgid="cat")
        assert is_plural_entry(e) is False


class TestBuildPluralPayload:
    def test_builds_correctly(self):
        e = polib.POEntry(msgid="cat", msgid_plural="cats", msgctxt="animals")
        payload = build_plural_payload(e, 2)
        assert payload == {
            "singular": "cat",
            "plural": "cats",
            "context": "animals",
            "num_forms": 2,
        }

    def test_no_context(self):
        e = polib.POEntry(msgid="cat", msgid_plural="cats")
        payload = build_plural_payload(e, 3)
        assert payload["context"] == ""
        assert payload["num_forms"] == 3


class TestApplyPluralTranslations:
    def test_applies_forms(self):
        e = polib.POEntry(msgid="cat", msgid_plural="cats", flags=["fuzzy"])
        apply_plural_translations(e, ["قطة", "قطط"])
        assert e.msgstr_plural[0] == "قطة"
        assert e.msgstr_plural[1] == "قطط"
        assert "fuzzy" not in e.flags

    def test_preserves_newline_prefix(self):
        e = polib.POEntry(msgid="\ncat", msgid_plural="\ncats")
        apply_plural_translations(e, ["قطة", "قطط"])
        assert e.msgstr_plural[0] == "\nقطة"
        assert e.msgstr_plural[1] == "\nقطط"


class TestMatchMsgidWhitespace:
    def test_leading_newline_added(self):
        result = _match_msgid_whitespace("\nHello", "مرحبا")
        assert result == "\nمرحبا"

    def test_leading_newline_already_present(self):
        result = _match_msgid_whitespace("\nHello", "\nمرحبا")
        assert result == "\nمرحبا"

    def test_trailing_whitespace_added(self):
        result = _match_msgid_whitespace("Hello  ", "مرحبا")
        assert result == "مرحبا  "

    def test_both_leading_and_trailing(self):
        result = _match_msgid_whitespace("\nHello  ", "مرحبا")
        assert result == "\nمرحبا  "

    def test_no_special_whitespace(self):
        result = _match_msgid_whitespace("Hello", "مرحبا")
        assert result == "مرحبا"

    def test_empty_msgstr(self):
        result = _match_msgid_whitespace("\nHello", "")
        assert result == ""


class TestSeparateEntries:
    def test_separates(self):
        po = polib.POFile()
        s1 = polib.POEntry(msgid="hello")
        p1 = polib.POEntry(msgid="cat", msgid_plural="cats")
        entries = [s1, p1]
        singular, plural, s_payloads, p_payloads = separate_entries(entries, 2)
        assert len(singular) == 1
        assert len(plural) == 1
        assert s_payloads[0]["text"] == "hello"
        assert p_payloads[0]["singular"] == "cat"

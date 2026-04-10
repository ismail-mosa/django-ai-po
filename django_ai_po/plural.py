import re
from typing import Dict, List, Optional, Tuple

import polib

PLURAL_FORM_HEADER_RE = re.compile(r"nplurals\s*=\s*(\d+)", re.IGNORECASE)


def get_plural_count(po: polib.POFile) -> int:
    if po.metadata and "Plural-Forms" in po.metadata:
        match = PLURAL_FORM_HEADER_RE.search(po.metadata["Plural-Forms"])
        if match:
            return int(match.group(1))
    return 2


def is_plural_entry(entry: polib.POEntry) -> bool:
    return bool(entry.msgid_plural)


def build_plural_payload(entry: polib.POEntry, num_forms: int) -> Dict:
    return {
        "singular": entry.msgid,
        "plural": entry.msgid_plural,
        "context": entry.msgctxt or "",
        "num_forms": num_forms,
    }


def apply_plural_translations(entry: polib.POEntry, translations: List[str]) -> None:
    for i, trans in enumerate(translations):
        ref = entry.msgid if i == 0 else entry.msgid_plural
        entry.msgstr_plural[i] = _match_msgid_whitespace(ref, trans)
    if "fuzzy" in entry.flags:
        entry.flags.remove("fuzzy")


def _match_msgid_whitespace(msgid: str, msgstr: str) -> str:
    if not msgid or not msgstr:
        return msgstr
    starts_newline = msgid[0] == "\n"
    ends_whitespace = msgid[-1] in (" ", "\t") and msgid.strip() != msgid
    if starts_newline and not msgstr.startswith("\n"):
        msgstr = "\n" + msgstr
    if ends_whitespace and not msgstr[-1] in (" ", "\t"):
        trailing = msgid[len(msgid.rstrip(" \t")) :]
        msgstr = msgstr + trailing
    return msgstr


def separate_entries(
    entries: List[polib.POEntry], num_plural_forms: int
) -> Tuple[List[polib.POEntry], List[polib.POEntry], List[Dict], List[Dict]]:
    singular_entries = []
    plural_entries = []
    singular_payloads = []
    plural_payloads = []

    for entry in entries:
        if is_plural_entry(entry):
            plural_entries.append(entry)
            plural_payloads.append(build_plural_payload(entry, num_plural_forms))
        else:
            singular_entries.append(entry)
            singular_payloads.append({"text": entry.msgid, "context": entry.msgctxt or ""})

    return singular_entries, plural_entries, singular_payloads, plural_payloads

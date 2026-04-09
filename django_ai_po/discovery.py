import os
from pathlib import Path
from typing import List, Optional, Tuple

from django.conf import settings


def get_locale_dirs() -> List[Path]:
    locale_paths = getattr(settings, "LOCALE_PATHS", [])
    if locale_paths:
        return [Path(p) for p in locale_paths]

    base = Path(settings.BASE_DIR)
    candidates = [base / "locale", base / "locales"]
    for c in candidates:
        if c.is_dir():
            return [c]
    return []


def discover_po_files(
    language: Optional[str] = None,
    domain: Optional[str] = None,
) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    for locale_dir in get_locale_dirs():
        results.extend(_scan_dir(locale_dir, language, domain))
    return sorted(results)


def _scan_dir(
    locale_dir: Path,
    language: Optional[str] = None,
    domain: Optional[str] = None,
) -> List[Tuple[str, str]]:
    results = []
    if not locale_dir.is_dir():
        return results

    for lang_dir in sorted(locale_dir.iterdir()):
        if not lang_dir.is_dir():
            continue
        if language and lang_dir.name != language:
            continue

        lc_messages = lang_dir / "LC_MESSAGES"
        if not lc_messages.is_dir():
            continue

        for po_file in sorted(lc_messages.glob("*.po")):
            if domain and po_file.stem != domain:
                continue
            results.append((str(po_file), lang_dir.name))

    return results

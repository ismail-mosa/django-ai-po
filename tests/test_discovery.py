import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django_ai_po.discovery import _scan_dir, discover_po_files, get_locale_dirs


class TestGetLocaleDirs:
    @patch("django_ai_po.discovery.settings")
    def test_from_settings(self, mock_settings):
        mock_settings.LOCALE_PATHS = ["/tmp/locale"]
        mock_settings.BASE_DIR = "/tmp"
        dirs = get_locale_dirs()
        assert len(dirs) == 1
        assert str(dirs[0]) == "/tmp/locale"

    @patch("django_ai_po.discovery.settings")
    def test_fallback_to_base_dir(self, mock_settings):
        mock_settings.LOCALE_PATHS = []
        with tempfile.TemporaryDirectory() as tmp:
            locale_dir = Path(tmp) / "locale"
            locale_dir.mkdir()
            mock_settings.BASE_DIR = tmp
            dirs = get_locale_dirs()
            assert len(dirs) == 1


class TestScanDir:
    def test_finds_po_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            locale = Path(tmp)
            ar_dir = locale / "ar" / "LC_MESSAGES"
            ar_dir.mkdir(parents=True)
            (ar_dir / "django.po").write_text("# PO file")
            (ar_dir / "djangojs.po").write_text("# PO file")

            results = _scan_dir(locale, language="ar")
            assert len(results) == 2

    def test_filters_by_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            locale = Path(tmp)
            for lang in ["ar", "fr"]:
                d = locale / lang / "LC_MESSAGES"
                d.mkdir(parents=True)
                (d / "django.po").write_text("# PO file")

            results = _scan_dir(locale, language="ar")
            assert len(results) == 1
            assert results[0][1] == "ar"

    def test_filters_by_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            locale = Path(tmp)
            ar_dir = locale / "ar" / "LC_MESSAGES"
            ar_dir.mkdir(parents=True)
            (ar_dir / "django.po").write_text("# PO")
            (ar_dir / "djangojs.po").write_text("# PO")

            results = _scan_dir(locale, language="ar", domain="django")
            assert len(results) == 1
            assert "django.po" in results[0][0]

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = _scan_dir(Path(tmp))
            assert results == []


class TestDiscoverPoFiles:
    @patch("django_ai_po.discovery.get_locale_dirs")
    def test_discovers_all(self, mock_get_dirs):
        with tempfile.TemporaryDirectory() as tmp:
            locale = Path(tmp)
            ar_dir = locale / "ar" / "LC_MESSAGES"
            ar_dir.mkdir(parents=True)
            (ar_dir / "django.po").write_text("# PO")
            mock_get_dirs.return_value = [locale]

            results = discover_po_files(language="ar")
            assert len(results) == 1

import json
import sys

from django.core.management.base import BaseCommand, CommandError

from django_ai_po.conf import Conf
from django_ai_po.discovery import discover_po_files
from django_ai_po.translator.base import POTranslator, resolve_lang_code


class Command(BaseCommand):
    help = "Translate .po file entries using AI via LiteLLM"

    def add_arguments(self, parser):
        parser.add_argument(
            "po_file_path",
            nargs="?",
            type=str,
            help="Path to the .po file (optional if --discover is used)",
        )
        parser.add_argument("--lang", type=str, default="Arabic", help="Target language (default: Arabic)")
        parser.add_argument("--model", type=str, default=None, help="LLM model override")
        parser.add_argument("--api-key", type=str, default=None, help="API key override")
        parser.add_argument("--api-base", type=str, default=None, help="API base URL override")
        parser.add_argument("--batch-size", type=int, default=None, help="Entries per API call")
        parser.add_argument("--workers", type=int, default=None, help="Concurrent threads")
        parser.add_argument("--temperature", type=float, default=None, help="LLM temperature")
        parser.add_argument("--max-tokens", type=int, default=None, help="Max tokens per request")
        parser.add_argument("--timeout", type=int, default=None, help="Request timeout in seconds")
        parser.add_argument("--max-retries", type=int, default=None, help="Max retries per batch")
        parser.add_argument("--fix-fuzzy", action="store_true", help="Include fuzzy entries")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-translate all entries (including already translated)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
        parser.add_argument(
            "--context",
            type=str,
            default="software",
            help="Translation context (default: software)",
        )
        parser.add_argument("--no-progress", action="store_true", help="Disable progress bar")
        parser.add_argument(
            "--discover",
            action="store_true",
            help="Auto-discover all .po files for the given --lang",
        )
        parser.add_argument(
            "--domain",
            type=str,
            default=None,
            help="PO domain filter when using --discover (e.g. django, djangojs)",
        )
        parser.add_argument(
            "--output-format",
            type=str,
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )

    def handle(self, *args, **options):
        self.output_format = options["output_format"]
        use_progress = Conf.progress_bar() and not options["no_progress"] and self.output_format == "text"

        if options["discover"]:
            self._handle_discover(options, use_progress)
        else:
            if not options["po_file_path"]:
                raise CommandError("po_file_path is required unless --discover is used")
            self._handle_single(options["po_file_path"], options, use_progress)

    def _handle_single(self, po_path: str, options: dict, use_progress: bool):
        translator = self._build_translator(options)
        result = translator.translate_file(
            po_path,
            fix_fuzzy=options["fix_fuzzy"],
            dry_run=options["dry_run"],
            force=options["force"],
        )
        self._output_result(po_path, result, options["dry_run"])

    def _handle_discover(self, options: dict, use_progress: bool):
        lang_code = resolve_lang_code(options["lang"])
        po_files = discover_po_files(language=lang_code, domain=options["domain"])

        if not po_files:
            raise CommandError(f"No .po files found for language '{options['lang']}'")

        self._log(f"Discovered {len(po_files)} .po file(s) for {options['lang']}")

        all_results = {}
        for po_path, lang in po_files:
            self._log(f"\nProcessing {po_path}")
            translator = self._build_translator(options)
            result = translator.translate_file(
                po_path,
                fix_fuzzy=options["fix_fuzzy"],
                dry_run=options["dry_run"],
                force=options["force"],
            )
            all_results[po_path] = result
            self._output_result(po_path, result, options["dry_run"])

        if self.output_format == "json":
            self.stdout.write(json.dumps({k: v.to_dict() for k, v in all_results.items()}, indent=2))

    def _build_translator(self, options: dict) -> POTranslator:
        progress = None
        if Conf.progress_bar() and not options["no_progress"] and self.output_format == "text":
            progress = self._create_progress_callback(options)

        return POTranslator(
            target_lang=options["lang"],
            context=options["context"],
            model=options.get("model"),
            api_key=options.get("api_key"),
            api_base=options.get("api_base"),
            temperature=options.get("temperature"),
            batch_size=options.get("batch_size"),
            workers=options.get("workers"),
            max_retries=options.get("max_retries"),
            timeout=options.get("timeout"),
            max_tokens=options.get("max_tokens"),
            progress_callback=progress,
            log_callback=self._log,
        )

    def _create_progress_callback(self, options: dict):
        try:
            from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

            progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeRemainingColumn(),
                console=self._get_rich_console(),
                transient=True,
            )
            task_id = progress.add_task("Translating", total=None)
            progress.start()

            def callback(done: int, total: int):
                progress.update(task_id, total=total, completed=done)
                if done >= total:
                    progress.stop()

            return callback
        except ImportError:
            return None

    def _get_rich_console(self):
        from rich.console import Console

        return Console(file=self.stdout)

    def _log(self, message: str):
        if self.output_format == "text":
            self.stdout.write(message)

    def _output_result(self, path: str, result, dry_run: bool):
        if self.output_format == "json":
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN] No changes saved"))

        self.stdout.write(
            self.style.SUCCESS(f"{path}: {result.success}/{result.total} translated ({result.success_rate:.0f}%)")
        )

        if result.errors:
            for err in result.errors:
                self.stderr.write(self.style.WARNING(f"  {err}"))

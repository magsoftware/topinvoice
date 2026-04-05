from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from textwrap import dedent

from topinvoice.models import CliOptions, Period


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured argument parser for the `topinvoice` command.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Log in to GuestSage, export the monthly report CSV, analyze totals and generate a PDF invoice."
        ),
        epilog=dedent(
            """\
            Examples:
              topinvoice 2026-03
              topinvoice --year 2026 --month 3
              python -m topinvoice 2026-03 --headless
              topinvoice 2026-03 --pdf-output invoices/2026-03.pdf
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("period", nargs="?", help="Target month in YYYY-MM format, for example 2026-03.")
    parser.add_argument("--year", type=int, help="Target year, for example 2026.")
    parser.add_argument("--month", type=int, help="Target month number, 1-12.")
    parser.add_argument(
        "--downloads-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="Directory where the exported CSV will be saved. Default: ~/Downloads",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to the .env file with GUESTSAGE_LOGIN and GUESTSAGE_PASSWORD.",
    )
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode.")
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30000,
        help="Playwright timeout in milliseconds. Default: 30000.",
    )
    parser.add_argument(
        "--pdf-output",
        type=Path,
        help="Path to the generated PDF invoice. Default: ./YYYY-MM-1.pdf",
    )
    return parser


def resolve_period(namespace: argparse.Namespace, parser: argparse.ArgumentParser) -> Period:
    """Resolve the target billing period from parsed CLI arguments.

    Args:
        namespace: Parsed argument namespace returned by `argparse`.
        parser: Parser used to raise user-facing validation errors.

    Returns:
        Normalized billing period.

    Raises:
        SystemExit: Raised indirectly through `parser.error()` when the user
            passes invalid or incomplete period arguments.
    """
    if namespace.period and (namespace.year is not None or namespace.month is not None):
        parser.error("Use either YYYY-MM or --year/--month, not both.")

    if namespace.period:
        token_parts = namespace.period.split("-")
        if len(token_parts) != 2 or len(token_parts[0]) != 4 or len(token_parts[1]) != 2:
            parser.error("Positional period must use YYYY-MM format, for example 2026-03.")
        try:
            year = int(token_parts[0])
            month = int(token_parts[1])
        except ValueError:
            parser.error("Positional period must use YYYY-MM format, for example 2026-03.")
    else:
        if namespace.year is None or namespace.month is None:
            parser.error("Provide either YYYY-MM or both --year and --month.")
        year = namespace.year
        month = namespace.month

    try:
        return Period(year=year, month=month)
    except ValueError as error:
        parser.error(str(error))


def parse_arguments(argv: Sequence[str] | None = None) -> CliOptions:
    """Parse command-line arguments into application options.

    Args:
        argv: Optional command-line arguments. When omitted, arguments are read
            from the process command line.

    Returns:
        Parsed CLI options ready for pipeline execution.
    """
    parser = build_parser()
    namespace = parser.parse_args(list(argv) if argv is not None else None)
    return CliOptions(
        period=resolve_period(namespace, parser),
        downloads_dir=namespace.downloads_dir.expanduser(),
        env_file=namespace.env_file.expanduser(),
        headless=namespace.headless,
        timeout_ms=namespace.timeout_ms,
        pdf_output=namespace.pdf_output.expanduser() if namespace.pdf_output is not None else None,
    )

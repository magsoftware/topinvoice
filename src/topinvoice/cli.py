from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from textwrap import dedent

from topinvoice.commands import InvoiceCommand, ManualInvoiceCommand, MonthlyInvoiceCommand
from topinvoice.models import CliOptions, ManualCliOptions, Period


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured argument parser for the `topinvoice` command.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Generate an invoice PDF from a GuestSage report or a manually supplied amount."
        ),
        epilog=dedent(
            """\
            Monthly report:
              topinvoice 2026-03
              topinvoice --year 2026 --month 3
              python -m topinvoice 2026-03 --headless
              topinvoice 2026-03 --pdf-output invoices/2026-03.pdf

            Manual invoice (no GuestSage or CSV):
              topinvoice manual --amount 2615.31
              topinvoice manual --amount 2615.31 --period 2026-03
              topinvoice manual --help
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


def build_manual_parser() -> argparse.ArgumentParser:
    """Build the parser for invoice generation from a supplied amount."""
    parser = argparse.ArgumentParser(
        prog="topinvoice manual",
        description="Generate an invoice PDF from a PLN amount, without GuestSage, CSV, or credentials.",
        epilog=dedent(
            """\
            The issue and sale dates are the last day of the billing month.
            Payment is due 14 days later. The default PDF path is ./YYYY-MM-1.pdf.

            Examples:
              topinvoice manual --amount 2615.31
              topinvoice manual --amount 2615.31 --period 2026-03 --pdf-output invoices/2026-03.pdf
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--amount", required=True, help="Positive invoice amount in PLN, for example 2615.31.")
    parser.add_argument("--period", help="Billing month in YYYY-MM format. Default: previous calendar month.")
    parser.add_argument("--pdf-output", type=Path, help="PDF output path. Default: ./YYYY-MM-1.pdf.")
    return parser


def previous_month(today: date) -> Period:
    """Return the calendar month preceding the supplied date."""
    if today.month == 1:
        return Period(year=today.year - 1, month=12)
    return Period(year=today.year, month=today.month - 1)


def parse_period_token(token: str, parser: argparse.ArgumentParser) -> Period:
    """Validate and parse a billing month in YYYY-MM format."""
    token_parts = token.split("-")
    if len(token_parts) != 2 or len(token_parts[0]) != 4 or len(token_parts[1]) != 2:
        parser.error("Period must use YYYY-MM format, for example 2026-03.")
    if not all(part.isascii() and part.isdigit() for part in token_parts):
        parser.error("Period must use YYYY-MM format, for example 2026-03.")
    try:
        period = Period(year=int(token_parts[0]), month=int(token_parts[1]))
    except ValueError as error:
        parser.error(str(error))
    if period.year < 1:
        parser.error("Year must be between 1 and 9999.")
    return period


def parse_amount(token: str, parser: argparse.ArgumentParser) -> Decimal:
    """Validate a manually supplied invoice amount."""
    try:
        amount = Decimal(token)
    except InvalidOperation:
        parser.error("Amount must be a decimal number, for example 2615.31.")
    if not amount.is_finite() or amount <= 0 or amount >= Decimal("1000000000000"):
        parser.error("Amount must be positive and below 1000000000000 PLN.")
    return amount


def parse_manual_arguments(argv: Sequence[str]) -> ManualCliOptions:
    """Parse options for manual PDF generation."""
    parser = build_manual_parser()
    namespace = parser.parse_args(list(argv))
    period = parse_period_token(namespace.period, parser) if namespace.period else previous_month(date.today())
    return ManualCliOptions(
        period=period,
        amount=parse_amount(namespace.amount, parser),
        pdf_output=namespace.pdf_output.expanduser() if namespace.pdf_output is not None else None,
    )


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
        return parse_period_token(namespace.period, parser)
    else:
        if namespace.year is None or namespace.month is None:
            parser.error("Provide either YYYY-MM or both --year and --month.")
        year = namespace.year
        month = namespace.month

    try:
        return Period(year=year, month=month)
    except ValueError as error:
        parser.error(str(error))


def parse_monthly_arguments(argv: Sequence[str]) -> CliOptions:
    """Parse options for the existing GuestSage report pipeline."""
    parser = build_parser()
    namespace = parser.parse_args(list(argv))
    return CliOptions(
        period=resolve_period(namespace, parser),
        downloads_dir=namespace.downloads_dir.expanduser(),
        env_file=namespace.env_file.expanduser(),
        headless=namespace.headless,
        timeout_ms=namespace.timeout_ms,
        pdf_output=namespace.pdf_output.expanduser() if namespace.pdf_output is not None else None,
    )


def parse_arguments(argv: Sequence[str] | None = None) -> CliOptions | ManualCliOptions:
    """Parse command-line arguments into mode-specific options.

    Args:
        argv: Optional command-line arguments. When omitted, arguments are read
            from the process command line.

    Returns:
        Parsed CLI options ready for pipeline execution.
    """
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] == "manual":
        return parse_manual_arguments(arguments[1:])
    return parse_monthly_arguments(arguments)


def parse_command(argv: Sequence[str] | None = None) -> InvoiceCommand:
    """Parse the CLI and return the selected invoice operation."""
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] == "manual":
        return ManualInvoiceCommand(parse_manual_arguments(arguments[1:]))
    return MonthlyInvoiceCommand(parse_monthly_arguments(arguments))

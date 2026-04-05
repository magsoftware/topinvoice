from __future__ import annotations

import csv
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from topinvoice.errors import CsvAnalysisError
from topinvoice.models import ReportTotals


def detect_csv_dialect(sample: str) -> type[csv.Dialect]:
    """Detect the CSV dialect used by a report sample.

    Args:
        sample: Initial text sample read from the CSV file.

    Returns:
        Detected CSV dialect. Falls back to `csv.excel` when detection fails.
    """
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        return csv.excel


def parse_decimal(value: str) -> Decimal:
    """Parse a localized currency-like value into a decimal number.

    Args:
        value: Raw string value from the CSV report.

    Returns:
        Parsed decimal number.

    Raises:
        InvalidOperation: If the value does not contain a parseable number.
    """
    cleaned = re.sub(r"[^\d,.\-]", "", value)
    if not cleaned:
        raise InvalidOperation(f"Could not parse number from: {value!r}")

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        decimal_part = cleaned.rsplit(",", 1)[-1]
        cleaned = cleaned.replace(",", ".") if len(decimal_part) <= 2 else cleaned.replace(",", "")
    elif "." in cleaned:
        decimal_part = cleaned.rsplit(".", 1)[-1]
        if len(decimal_part) > 2:
            cleaned = cleaned.replace(".", "")

    return Decimal(cleaned)


def analyze_report_csv(csv_path: Path) -> ReportTotals:
    """Extract totals from the downloaded CSV report.

    Args:
        csv_path: Path to the report CSV file.

    Returns:
        Totals containing the last row amount and the sum of preceding data rows.

    Raises:
        CsvAnalysisError: If the file cannot be read or does not contain enough
            numeric rows.
    """
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            reader = csv.reader(handle, detect_csv_dialect(sample))
            amounts: list[Decimal] = []

            for row in reader:
                if len(row) < 4:
                    continue
                try:
                    amounts.append(parse_decimal(row[3]))
                except InvalidOperation:
                    continue
    except OSError as error:
        raise CsvAnalysisError(f"Could not read CSV file: {csv_path}") from error

    if len(amounts) < 2:
        raise CsvAnalysisError(f"Expected at least two numeric rows in column 4 of {csv_path}, got {len(amounts)}.")

    return ReportTotals(last_row_total=amounts[-1], data_rows_total=sum(amounts[:-1], Decimal("0")))


def format_decimal_output(value: Decimal) -> str:
    """Format a decimal value without insignificant trailing zeros.

    Args:
        value: Decimal value to format.

    Returns:
        Human-readable decimal string.
    """
    normalized = format(value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")

    return normalized


def quantize_money(value: Decimal) -> Decimal:
    """Round a money value to two decimal places.

    Args:
        value: Decimal value to quantize.

    Returns:
        Decimal rounded using half-up monetary rounding.
    """
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

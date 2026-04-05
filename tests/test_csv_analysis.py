from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest

from topinvoice.csv_analysis import analyze_report_csv, detect_csv_dialect, format_decimal_output, parse_decimal
from topinvoice.errors import CsvAnalysisError


def test_detect_csv_dialect_uses_fallback_when_sniffer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenSniffer:
        def sniff(self, sample: str, delimiters: str) -> csv.Dialect:
            raise csv.Error("broken")

    monkeypatch.setattr(csv, "Sniffer", lambda: BrokenSniffer())

    assert detect_csv_dialect("value") is csv.excel


def test_parse_decimal_handles_common_formats() -> None:
    assert parse_decimal("PLN 1,232.65") == Decimal("1232.65")
    assert parse_decimal("PLN 1.232,65") == Decimal("1232.65")
    assert parse_decimal("PLN 2,615") == Decimal("2615")
    assert parse_decimal("PLN 2.615") == Decimal("2615")


def test_parse_decimal_rejects_empty_value() -> None:
    with pytest.raises(InvalidOperation):
        parse_decimal("PLN")


def test_analyze_report_csv_returns_totals(tmp_path: Path) -> None:
    csv_path = tmp_path / "report.csv"
    csv_path.write_text(
        "\n".join(
            (
                "Arrival date,Departure date,Length of stay,Total net amount for the owner",
                "short,row",
                "6 Mar 2026,9 Mar 2026,3 days,PLN 720.01",
                "12 Mar 2026,15 Mar 2026,3 days,PLN 766.02",
                "21 Mar 2026,23 Mar 2026,2 days,PLN 501.28",
                "28 Mar 2026,31 Mar 2026,3 days,PLN 628.00",
                ',,,"PLN 2,615.31"',
            ),
        ),
        encoding="utf-8",
    )

    totals = analyze_report_csv(csv_path)

    assert totals.last_row_total == Decimal("2615.31")
    assert totals.data_rows_total == Decimal("2615.31")


def test_analyze_report_csv_rejects_too_few_numeric_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "report.csv"
    csv_path.write_text("header1,header2,header3,header4\nrow1,row2,row3,text\n", encoding="utf-8")

    with pytest.raises(CsvAnalysisError, match="Expected at least two numeric rows"):
        analyze_report_csv(csv_path)


def test_analyze_report_csv_wraps_os_errors(tmp_path: Path) -> None:
    with pytest.raises(CsvAnalysisError, match="Could not read CSV file"):
        analyze_report_csv(tmp_path / "missing.csv")


def test_format_decimal_output_trims_trailing_zeros() -> None:
    assert format_decimal_output(Decimal("2615.30")) == "2615.3"
    assert format_decimal_output(Decimal("2615")) == "2615"

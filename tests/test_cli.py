from __future__ import annotations

import pytest

from topinvoice.cli import parse_arguments


def test_parse_arguments_with_positional_period() -> None:
    options = parse_arguments(["2026-03"])

    assert options.period.year == 2026
    assert options.period.month == 3
    assert options.pdf_output is None


def test_parse_arguments_with_year_and_month() -> None:
    options = parse_arguments(["--year", "2026", "--month", "3", "--pdf-output", "~/invoice.pdf"])

    assert options.period.token == "2026-03"
    assert str(options.pdf_output).endswith("invoice.pdf")


def test_parse_arguments_rejects_mixed_period_inputs() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["2026-03", "--year", "2026", "--month", "3"])


def test_parse_arguments_rejects_invalid_period_format() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["2026/03"])


def test_parse_arguments_rejects_non_numeric_period_parts() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["2026-AA"])


def test_parse_arguments_requires_full_year_month_pair() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["--year", "2026"])


def test_parse_arguments_rejects_invalid_month_value() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["--year", "2026", "--month", "13"])

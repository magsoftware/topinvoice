from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from topinvoice.config import Config
from topinvoice.models import CliOptions, Period, ReportTotals


@pytest.fixture
def sample_period() -> Period:
    return Period(year=2026, month=3)


@pytest.fixture
def sample_config() -> Config:
    return Config(login="marek@example.com", password="secret")


@pytest.fixture
def sample_cli_options(tmp_path: Path, sample_period: Period) -> CliOptions:
    return CliOptions(
        period=sample_period,
        downloads_dir=tmp_path / "downloads",
        env_file=tmp_path / ".env",
        headless=True,
        timeout_ms=30000,
        pdf_output=tmp_path / "invoice.pdf",
    )


@pytest.fixture
def sample_report_totals() -> ReportTotals:
    return ReportTotals(last_row_total=Decimal("2615.31"), data_rows_total=Decimal("2615.31"))

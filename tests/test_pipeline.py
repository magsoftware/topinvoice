from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from topinvoice.config import Config
from topinvoice.models import CliOptions, InvoiceData, Period, ReportTotals
from topinvoice.pipeline import resolve_pdf_output_path, run_pipeline


class FakeScraper:
    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path
        self.calls: list[tuple[Period, Path, Config, bool, int]] = []

    def export_monthly_report(
        self,
        period: Period,
        downloads_dir: Path,
        config: Config,
        headless: bool,
        timeout_ms: int,
    ) -> Path:
        self.calls.append((period, downloads_dir, config, headless, timeout_ms))
        return self.csv_path


def test_resolve_pdf_output_path_uses_default_when_missing(sample_period: Period, tmp_path: Path) -> None:
    options = CliOptions(
        period=sample_period,
        downloads_dir=tmp_path / "downloads",
        env_file=tmp_path / ".env",
        headless=False,
        timeout_ms=1000,
        pdf_output=None,
    )

    assert resolve_pdf_output_path(options) == Path("2026-03-1.pdf")


def test_run_pipeline_orchestrates_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    sample_cli_options: CliOptions,
    sample_report_totals: ReportTotals,
) -> None:
    csv_path = sample_cli_options.downloads_dir / "report.csv"
    pdf_path = sample_cli_options.pdf_output
    assert pdf_path is not None
    scraper = FakeScraper(csv_path)
    invoice = InvoiceData(
        number="FVS/2026/03/01",
        issue_date="2026-03-31",
        sale_date="2026-03-31",
        due_date="2026-04-14",
        amount=Decimal("2615.31"),
        amount_words="dwa tysiące sześćset piętnaście zł 31/100",
    )

    monkeypatch.setattr("topinvoice.pipeline.load_config", lambda path: Config("login", "password"))
    monkeypatch.setattr("topinvoice.pipeline.analyze_report_csv", lambda path: sample_report_totals)
    monkeypatch.setattr("topinvoice.pipeline.build_invoice_data", lambda period, amount: invoice)
    monkeypatch.setattr("topinvoice.pipeline.generate_invoice_pdf", lambda invoice_data, path: path)

    result = run_pipeline(sample_cli_options, scraper=scraper)

    assert result.csv_path == csv_path
    assert result.pdf_path == pdf_path
    assert result.report_totals == sample_report_totals
    assert scraper.calls == [
        (
            sample_cli_options.period,
            sample_cli_options.downloads_dir,
            Config("login", "password"),
            True,
            30000,
        ),
    ]

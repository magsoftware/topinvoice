from __future__ import annotations

from pathlib import Path
from typing import Protocol

from topinvoice.config import Config, load_config
from topinvoice.csv_analysis import analyze_report_csv
from topinvoice.invoice_pdf import build_invoice_data, generate_invoice_pdf
from topinvoice.models import CliOptions, Period, PipelineResult
from topinvoice.scraping import GuestSageScraper


class MonthlyReportScraper(Protocol):
    def export_monthly_report(
        self,
        period: Period,
        downloads_dir: Path,
        config: Config,
        headless: bool,
        timeout_ms: int,
    ) -> Path:
        ...


def resolve_pdf_output_path(options: CliOptions) -> Path:
    return options.pdf_output if options.pdf_output is not None else options.period.default_invoice_path


def run_pipeline(options: CliOptions, scraper: MonthlyReportScraper | None = None) -> PipelineResult:
    config = load_config(options.env_file)
    active_scraper = scraper or GuestSageScraper()
    csv_path = active_scraper.export_monthly_report(
        period=options.period,
        downloads_dir=options.downloads_dir,
        config=config,
        headless=options.headless,
        timeout_ms=options.timeout_ms,
    )
    report_totals = analyze_report_csv(csv_path)
    invoice = build_invoice_data(options.period, report_totals.last_row_total)
    pdf_path = generate_invoice_pdf(invoice, resolve_pdf_output_path(options))

    return PipelineResult(csv_path=csv_path, pdf_path=pdf_path, report_totals=report_totals)

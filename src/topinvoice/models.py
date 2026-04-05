from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


@dataclass(frozen=True)
class Period:
    year: int
    month: int

    def __post_init__(self) -> None:
        if self.month < 1 or self.month > 12:
            raise ValueError("Month must be between 1 and 12.")

    @property
    def month_label(self) -> str:
        return MONTH_LABELS[self.month]

    @property
    def token(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def invoice_number(self) -> str:
        return f"FVS/{self.year:04d}/{self.month:02d}/01"

    @property
    def default_invoice_path(self) -> Path:
        return Path(f"{self.token}-1.pdf")


@dataclass(frozen=True)
class CliOptions:
    period: Period
    downloads_dir: Path
    env_file: Path
    headless: bool
    timeout_ms: int
    pdf_output: Path | None


@dataclass(frozen=True)
class ReportTotals:
    last_row_total: Decimal
    data_rows_total: Decimal


@dataclass(frozen=True)
class InvoiceData:
    number: str
    issue_date: str
    sale_date: str
    due_date: str
    amount: Decimal
    amount_words: str


@dataclass(frozen=True)
class PipelineResult:
    csv_path: Path
    pdf_path: Path
    report_totals: ReportTotals

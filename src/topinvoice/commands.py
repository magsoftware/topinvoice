from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from topinvoice.models import CliOptions, ManualCliOptions
from topinvoice.pipeline import run_manual_invoice, run_pipeline


class InvoiceCommand(Protocol):
    """An invoice operation selected by the command-line parser."""

    def run(self) -> None: ...


@dataclass(frozen=True)
class MonthlyInvoiceCommand:
    """Generate an invoice from a GuestSage monthly report."""

    options: CliOptions

    def run(self) -> None:
        """Run the existing report pipeline."""
        run_pipeline(self.options)


@dataclass(frozen=True)
class ManualInvoiceCommand:
    """Generate an invoice from a manually supplied amount."""

    options: ManualCliOptions

    def run(self) -> None:
        """Generate the PDF without downloading a report."""
        run_manual_invoice(self.options)

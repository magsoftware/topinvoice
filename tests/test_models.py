from __future__ import annotations

from pathlib import Path

import pytest

from topinvoice.models import Period


def test_period_properties() -> None:
    period = Period(year=2026, month=3)

    assert period.month_label == "Mar"
    assert period.token == "2026-03"
    assert period.invoice_number == "FVS/2026/03/01"
    assert period.default_invoice_path == Path("2026-03-1.pdf")


def test_period_rejects_invalid_month() -> None:
    with pytest.raises(ValueError, match="Month must be between 1 and 12."):
        Period(year=2026, month=13)

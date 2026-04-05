from __future__ import annotations

import builtins
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from topinvoice.errors import PdfGenerationError
from topinvoice.invoice_pdf import (
    amount_to_words,
    build_invoice_data,
    choose_plural_form,
    ensure_reportlab_available,
    format_currency_pln,
    generate_invoice_pdf,
    integer_to_polish_words,
    last_day_of_month,
    number_under_thousand_to_words,
    register_invoice_fonts,
)
from topinvoice.models import Period


def test_ensure_reportlab_available_raises_when_dependency_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("reportlab"):
            raise ModuleNotFoundError(name)
        importer = cast(Callable[..., object], original_import)
        return importer(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(PdfGenerationError, match="ReportLab is not installed"):
        ensure_reportlab_available()


def test_invoice_helpers() -> None:
    assert format_currency_pln(Decimal("2615.31")) == "2 615,31 zł"
    assert choose_plural_form(1, ("a", "b", "c")) == "a"
    assert choose_plural_form(2, ("a", "b", "c")) == "b"
    assert choose_plural_form(5, ("a", "b", "c")) == "c"
    assert number_under_thousand_to_words(215) == "dwieście piętnaście"
    assert number_under_thousand_to_words(120) == "sto dwadzieścia"
    assert integer_to_polish_words(0) == "zero"
    assert integer_to_polish_words(2615) == "dwa tysiące sześćset piętnaście"
    assert integer_to_polish_words(1000000) == "jeden milion"
    assert amount_to_words(Decimal("2615.31")) == "dwa tysiące sześćset piętnaście zł 31/100"


def test_build_invoice_data_uses_last_day_of_month() -> None:
    period = Period(year=2026, month=2)

    assert last_day_of_month(period).isoformat() == "2026-02-28"
    invoice = build_invoice_data(period, Decimal("123.45"))
    assert invoice.number == "FVS/2026/02/01"
    assert invoice.issue_date == "2026-02-28"
    assert invoice.sale_date == "2026-02-28"
    assert invoice.due_date == "2026-03-14"


def test_generate_invoice_pdf_creates_file_and_registers_fonts_twice(tmp_path: Path) -> None:
    invoice = build_invoice_data(Period(year=2026, month=3), Decimal("2615.31"))
    output_path = tmp_path / "invoice.pdf"

    generated_path = generate_invoice_pdf(invoice, output_path)
    assert generated_path.exists()
    assert generated_path.read_bytes().startswith(b"%PDF")

    _, _, _, pdfmetrics, tt_font = ensure_reportlab_available()
    register_invoice_fonts(pdfmetrics, tt_font)
    register_invoice_fonts(pdfmetrics, tt_font)

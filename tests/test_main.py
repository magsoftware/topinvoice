from __future__ import annotations

import importlib
import runpy
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest

from topinvoice.errors import TopinvoiceError
from topinvoice.main import main
from topinvoice.models import PipelineResult, ReportTotals


def test_main_prints_two_totals(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("topinvoice.main.parse_arguments", lambda argv: object())
    monkeypatch.setattr(
        "topinvoice.main.run_pipeline",
        lambda options: PipelineResult(
            csv_path=Path("report.csv"),
            pdf_path=Path("invoice.pdf"),
            report_totals=ReportTotals(
                last_row_total=Decimal("2615.31"),
                data_rows_total=Decimal("2615.31"),
            ),
        ),
    )

    exit_code = main([])

    assert exit_code == 0
    assert capsys.readouterr().out == "2615.31\n2615.31\n"


def test_main_returns_error_code_for_application_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr("topinvoice.main.parse_arguments", lambda argv: object())
    monkeypatch.setattr(
        "topinvoice.main.run_pipeline",
        lambda options: (_ for _ in ()).throw(TopinvoiceError("boom")),
    )

    exit_code = main([])

    assert exit_code == 1
    assert "boom" in caplog.text


def test_package_main_module_executes_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("topinvoice.main")

    def fake_main() -> int:
        return 0

    fake_module.__dict__["main"] = fake_main
    monkeypatch.setitem(sys.modules, "topinvoice.main", fake_module)

    with pytest.raises(SystemExit) as result:
        runpy.run_module("topinvoice.__main__", run_name="__main__")

    assert result.value.code == 0


def test_package_main_module_imports_without_running_entrypoint() -> None:
    module = importlib.import_module("topinvoice.__main__")

    assert module is not None

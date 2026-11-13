from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from topinvoice.cli import parse_arguments, parse_command, parse_manual_arguments, previous_month
from topinvoice.commands import ManualInvoiceCommand, MonthlyInvoiceCommand
from topinvoice.main import main
from topinvoice.models import InvoiceData, ManualCliOptions, Period
from topinvoice.pipeline import run_manual_invoice


def test_previous_month_handles_year_boundary() -> None:
    assert previous_month(date(2026, 11, 13)) == Period(2026, 10)
    assert previous_month(date(2026, 1, 1)) == Period(2025, 12)


def test_manual_arguments_use_previous_month_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDate:
        @staticmethod
        def today() -> date:
            return date(2026, 11, 13)

    monkeypatch.setattr("topinvoice.cli.date", FakeDate)

    options = parse_arguments(["manual", "--amount", "2615.31"])

    assert options == ManualCliOptions(Period(2026, 10), Decimal("2615.31"), None)


def test_manual_arguments_accept_explicit_period_and_output() -> None:
    options = parse_manual_arguments(["--amount", "2615.31", "--period", "2026-03", "--pdf-output", "~/bill.pdf"])

    assert options.period == Period(2026, 3)
    assert options.amount == Decimal("2615.31")
    assert options.pdf_output == Path.home() / "bill.pdf"


def test_help_explains_manual_mode(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as result:
        parse_arguments(["--help"])

    assert result.value.code == 0
    assert "topinvoice manual --help" in capsys.readouterr().out

    with pytest.raises(SystemExit) as result:
        parse_arguments(["manual", "--help"])

    assert result.value.code == 0
    manual_help = capsys.readouterr().out
    assert "Default: previous" in manual_help
    assert "calendar month" in manual_help
    assert "Payment is due 14 days later" in manual_help
    assert "Default: ./YYYY-MM-1.pdf" in manual_help


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--amount", "abc"],
        ["--amount", "NaN"],
        ["--amount", "0"],
        ["--amount", "-1"],
        ["--amount", "1000000000000"],
        ["--amount", "1", "--period", "2026/03"],
        ["--amount", "1", "--period", "2026-AA"],
        ["--amount", "1", "--period", "2026-13"],
        ["--amount", "1", "--period", "0000-01"],
    ],
)
def test_manual_arguments_reject_invalid_input(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as result:
        parse_manual_arguments(arguments)

    assert result.value.code == 2


def test_manual_invoice_uses_existing_invoice_rules_and_default_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[InvoiceData, Path]] = []

    def fake_generate(invoice: InvoiceData, path: Path) -> Path:
        calls.append((invoice, path))
        return path

    monkeypatch.setattr("topinvoice.pipeline.generate_invoice_pdf", fake_generate)
    options = ManualCliOptions(Period(2026, 3), Decimal("2615.31"), None)

    assert run_manual_invoice(options) == Path("2026-03-1.pdf")
    invoice, path = calls[0]
    assert path == Path("2026-03-1.pdf")
    assert invoice.number == "FVS/2026/03/01"
    assert invoice.issue_date == "2026-03-31"
    assert invoice.sale_date == "2026-03-31"
    assert invoice.due_date == "2026-04-14"
    assert invoice.amount == Decimal("2615.31")


def test_manual_invoice_uses_explicit_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "bill.pdf"
    monkeypatch.setattr("topinvoice.pipeline.generate_invoice_pdf", lambda invoice, path: path)

    assert run_manual_invoice(ManualCliOptions(Period(2026, 3), Decimal("1"), output)) == output


def test_main_runs_manual_mode_without_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    options = ManualCliOptions(Period(2026, 3), Decimal("1"), None)
    calls: list[ManualCliOptions] = []
    monkeypatch.setattr("topinvoice.main.parse_command", lambda argv: ManualInvoiceCommand(options))
    monkeypatch.setattr("topinvoice.commands.run_manual_invoice", lambda value: calls.append(value))
    monkeypatch.setattr("topinvoice.commands.run_pipeline", lambda value: pytest.fail("Monthly pipeline was called"))

    assert main([]) == 0
    assert calls == [options]


def test_parse_command_selects_monthly_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Period] = []
    monkeypatch.setattr("topinvoice.commands.run_pipeline", lambda options: calls.append(options.period))

    command = parse_command(["2026-03"])

    assert isinstance(command, MonthlyInvoiceCommand)
    command.run()
    assert calls == [Period(2026, 3)]


def test_parse_command_selects_manual_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[ManualCliOptions] = []
    monkeypatch.setattr("topinvoice.commands.run_manual_invoice", lambda options: calls.append(options))

    command = parse_command(["manual", "--amount", "123.45", "--period", "2026-03"])

    assert isinstance(command, ManualInvoiceCommand)
    command.run()
    assert calls == [ManualCliOptions(Period(2026, 3), Decimal("123.45"), None)]


def test_manual_invoice_creates_pdf_without_credentials(tmp_path: Path) -> None:
    output = tmp_path / "bill.pdf"

    assert main(["manual", "--amount", "2615.31", "--period", "2026-03", "--pdf-output", str(output)]) == 0
    assert output.read_bytes().startswith(b"%PDF")

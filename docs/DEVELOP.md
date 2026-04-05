# DEVELOP

## Project Goal

The project automates a simple billing pipeline for the `Topolowa 15` apartment:

1. download the monthly report from GuestSage,
2. save the CSV,
3. analyze the amounts,
4. generate the invoice PDF.

## Architecture

The project is split into small modules by responsibility:

- `cli.py` - command-line entrypoint and argument validation,
- `config.py` - read `.env` and prepare credentials,
- `scraping.py` - GuestSage integration and CSV export,
- `csv_analysis.py` - CSV parsing and analysis,
- `invoice_pdf.py` - invoice model and PDF generator,
- `pipeline.py` - orchestration of the full flow,
- `main.py` - CLI application entrypoint.

## Tests

The tests are unit-level and deterministic. Playwright and ReportLab integrations are tested with fakes or by generating temporary files.

Target standard:

- `pytest` with `100%` coverage,
- `ruff` for linting,
- `mypy --strict`.

## Conventions

The code must follow the rules from `.ai/coding-style.md`:

- explicit types,
- no `print`,
- small functions,
- absolute imports,
- no unused code.

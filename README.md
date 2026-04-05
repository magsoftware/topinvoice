# TopInvoice

CLI for downloading a monthly report from GuestSage, analyzing the CSV, and generating an invoice PDF.

## Pipeline

1. `scrape` - log in to GuestSage and set the report filters
2. `download csv` - export the CSV file to the selected directory
3. `analyze csv` - read the final value and the sum of all data rows
4. `generate pdf` - generate an invoice PDF for the selected month

## Project Structure

```text
src/topinvoice/
  cli.py
  config.py
  csv_analysis.py
  invoice_pdf.py
  main.py
  models.py
  pipeline.py
  scraping.py

docs/
  DEVELOP.md

tests/
  conftest.py
  test_cli.py
  test_config.py
  test_csv_analysis.py
  test_invoice_pdf.py
  test_main.py
  test_models.py
  test_pipeline.py
  test_scraping.py
```

## Setup

```bash
git clone git@github.com:magsoftware/topinvoice.git
cd topinvoice
uv python install 3.14
uv sync --extra dev
cp .env.example .env
```

Alternatively, via HTTPS:

```bash
git clone https://github.com/magsoftware/topinvoice.git
cd topinvoice
uv python install 3.14
uv sync --extra dev
cp .env.example .env
```

Fill in `.env`:

```dotenv
GUESTSAGE_LOGIN=your-login
GUESTSAGE_PASSWORD=your-password
```

Install Playwright browsers:

```bash
uv run playwright install chromium
```

Verify the installation:

```bash
uv run topinvoice --help
uv run pytest
uv run ruff check .
uv run mypy
```

## Setup In An Existing Directory

```bash
uv python install 3.14
uv sync --extra dev
cp .env.example .env
```

## Running

```bash
uv run topinvoice 2026-03
uv run topinvoice --year 2026 --month 3
uv run python -m topinvoice 2026-03 --headless
uv run topinvoice 2026-03 --pdf-output invoices/2026-03.pdf
```

Help:

```bash
uv run topinvoice --help
```

## Developer workflow

```bash
uv run pytest
uv run ruff check .
uv run mypy
```

## Output

The invoice PDF is saved by default as `./YYYY-MM-1.pdf`.

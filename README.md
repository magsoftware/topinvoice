# TopInvoice

CLI do pobrania raportu miesięcznego z GuestSage, analizy CSV i wygenerowania PDF faktury.

## Pipeline

1. `scrape` - logowanie do GuestSage i ustawienie filtrów raportu
2. `download csv` - eksport pliku CSV do wybranego katalogu
3. `analyze csv` - odczyt wartości końcowej i sumy wierszy danych
4. `generate pdf` - wygenerowanie faktury PDF dla wskazanego miesiąca

## Struktura projektu

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

Przykład dla repozytorium hostowanego pod `github.com/magsoftware`.
Jeśli nazwa repo jest inna, podmień `topinvoice` w komendzie `git clone`.

```bash
git clone git@github.com:magsoftware/topinvoice.git
cd topinvoice
uv python install 3.14
uv python pin 3.14
uv sync --extra dev
cp .env.example .env
```

Alternatywnie przez HTTPS:

```bash
git clone https://github.com/magsoftware/topinvoice.git
cd topinvoice
```

Uzupełnij `.env`:

```dotenv
GUESTSAGE_LOGIN=twoj-login
GUESTSAGE_PASSWORD=twoje-haslo
```

Zainstaluj przeglądarki Playwright:

```bash
uv run playwright install chromium
```

Sprawdzenie instalacji:

```bash
uv run topinvoice --help
uv run pytest
uv run ruff check .
uv run mypy
```

Projekt nie używa `requirements.txt`.
Źródłem zależności jest [pyproject.toml](/Users/marek/repos/magsoftware/topolowa-invoice/pyproject.toml), a stan środowiska jest zamknięty w [uv.lock](/Users/marek/repos/magsoftware/topolowa-invoice/uv.lock).

## Setup W Istniejącym Katalogu

```bash
uv python install 3.14
uv python pin 3.14
uv sync --extra dev
cp .env.example .env
```

## Uruchomienie

```bash
uv run topinvoice 2026-03
uv run topinvoice --year 2026 --month 3
uv run python -m topinvoice 2026-03 --headless
uv run topinvoice 2026-03 --pdf-output invoices/2026-03.pdf
```

Pomoc:

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

CLI wypisuje dwie liczby:
1. wartość z ostatniego wiersza CSV
2. sumę wszystkich wierszy danych

PDF faktury zapisuje domyślnie jako `./YYYY-MM-1.pdf`.

# DEVELOP

## Cel projektu

Projekt automatyzuje prosty pipeline rozliczeniowy dla apartamentu `Topolowa 15`:

1. pobranie miesięcznego raportu z GuestSage,
2. zapis CSV,
3. analiza kwot,
4. wygenerowanie faktury PDF.

## Architektura

Projekt jest podzielony na małe moduły według odpowiedzialności:

- `cli.py` - wejście z linii poleceń i walidacja argumentów,
- `config.py` - odczyt `.env` i przygotowanie poświadczeń,
- `scraping.py` - integracja z GuestSage i eksport CSV,
- `csv_analysis.py` - parser i analiza pliku CSV,
- `invoice_pdf.py` - model faktury i generator PDF,
- `pipeline.py` - orkiestracja całego przepływu,
- `main.py` - uruchomienie aplikacji CLI.

## Testy

Testy są jednostkowe i deterministyczne. Integracje z Playwright i ReportLab są testowane przez fakes albo przez generację plików tymczasowych.

Docelowy standard:

- `pytest` z coverage `100%`,
- `ruff` dla lintingu,
- `mypy --strict`.

## Konwencje

Kod musi być zgodny z zasadami z `.ai/coding-style.md`:

- jawne typy,
- brak `print`,
- małe funkcje,
- importy absolutne,
- brak nieużywanego kodu.

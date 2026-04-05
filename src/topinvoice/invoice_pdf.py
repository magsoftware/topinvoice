from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from topinvoice.csv_analysis import quantize_money
from topinvoice.errors import PdfGenerationError
from topinvoice.models import InvoiceData, Period

INVOICE_PLACE = "Kraków"
PAYMENT_METHOD = "Przelew"
BANK_ACCOUNT = "Alior Bank 71 2490 0005 0000 4000 5221 5415"
SELLER_LINES = (
    "Sven Angerer",
    "Herzogstandstrasse 2",
    "82327 Tutzing",
    "NIP 6751608722",
)
BUYER_LINES = (
    "Uliana Zalewska Nearto.pl",
    "ul. Topolowa 49/19",
    "31-506 Kraków",
    "NIP 7010422829",
)
SERVICE_DESCRIPTION = "Najem lokalu przy ul. Topolowej 8/15 w Krakowie."
VAT_NOTE = "Sprzedawca podmiotowo zwolniony z podatku VAT"
FONT_REGULAR_NAME = "InvoiceArial"
FONT_BOLD_NAME = "InvoiceArialBold"
FONT_CANDIDATES = (
    (
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ),
    (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ),
)

ONES = (
    "zero",
    "jeden",
    "dwa",
    "trzy",
    "cztery",
    "pięć",
    "sześć",
    "siedem",
    "osiem",
    "dziewięć",
)
TEENS = (
    "dziesięć",
    "jedenaście",
    "dwanaście",
    "trzynaście",
    "czternaście",
    "piętnaście",
    "szesnaście",
    "siedemnaście",
    "osiemnaście",
    "dziewiętnaście",
)
TENS = (
    "",
    "",
    "dwadzieścia",
    "trzydzieści",
    "czterdzieści",
    "pięćdziesiąt",
    "sześćdziesiąt",
    "siedemdziesiąt",
    "osiemdziesiąt",
    "dziewięćdziesiąt",
)
HUNDREDS = (
    "",
    "sto",
    "dwieście",
    "trzysta",
    "czterysta",
    "pięćset",
    "sześćset",
    "siedemset",
    "osiemset",
    "dziewięćset",
)
SCALE_FORMS = (
    ("", "", ""),
    ("tysiąc", "tysiące", "tysięcy"),
    ("milion", "miliony", "milionów"),
    ("miliard", "miliardy", "miliardów"),
)


class CanvasLike(Protocol):
    """Protocol for the subset of canvas operations used by PDF rendering."""

    def setFont(self, psfontname: str, size: int) -> None: ...

    def drawString(self, x: float, y: float, text: str) -> None: ...

    def drawRightString(self, x: float, y: float, text: str) -> None: ...

    def drawCentredString(self, x: float, y: float, text: str) -> None: ...

    def setFillGray(self, gray: float) -> None: ...

    def rect(self, x: float, y: float, width: float, height: float, stroke: int, fill: int) -> None: ...

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None: ...

    def showPage(self) -> None: ...

    def save(self) -> None: ...


class CanvasFactory(Protocol):
    """Protocol for constructing ReportLab canvas instances."""

    def __call__(
        self,
        filename: str,
        pagesize: tuple[float, float],
        pageCompression: int = 0,
    ) -> CanvasLike: ...


class PdfMetricsLike(Protocol):
    """Protocol for ReportLab font registration APIs."""

    def getRegisteredFontNames(self) -> tuple[str, ...] | list[str]: ...

    def registerFont(self, font: object) -> None: ...


class TTFontFactory(Protocol):
    """Protocol for constructing TrueType font wrappers."""

    def __call__(self, name: str, filename: str) -> object: ...


def ensure_reportlab_available() -> tuple[CanvasFactory, tuple[float, float], float, PdfMetricsLike, TTFontFactory]:
    """Import and return the ReportLab objects used by PDF generation.

    Returns:
        Tuple containing the canvas factory, A4 page size, millimeter unit,
        font registry, and TTF font factory.

    Raises:
        PdfGenerationError: If ReportLab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen.canvas import Canvas
    except ModuleNotFoundError as error:
        message = "ReportLab is not installed. Install project dependencies from pyproject.toml."
        raise PdfGenerationError(message) from error

    return Canvas, A4, mm, pdfmetrics, TTFont


def format_currency_pln(value: Decimal) -> str:
    """Format a decimal amount as Polish currency text.

    Args:
        value: Monetary value to format.

    Returns:
        Currency string using Polish separators and `zł`.
    """
    quantized = quantize_money(value)
    integral, fractional = f"{quantized:.2f}".split(".")
    groups: list[str] = []
    while integral:
        groups.append(integral[-3:])
        integral = integral[:-3]

    return f"{' '.join(reversed(groups))},{fractional} zł"


def last_day_of_month(period: Period) -> date:
    """Return the last calendar day of a billing period.

    Args:
        period: Billing period to evaluate.

    Returns:
        Last day of the given month.
    """
    return date(period.year, period.month, calendar.monthrange(period.year, period.month)[1])


def choose_plural_form(value: int, forms: tuple[str, str, str]) -> str:
    """Choose the correct Polish plural form for a number.

    Args:
        value: Number that determines the plural form.
        forms: Singular, paucal, and plural word variants.

    Returns:
        Matching plural form for the provided number.
    """
    if value == 1:
        return forms[0]
    if value % 10 in {2, 3, 4} and value % 100 not in {12, 13, 14}:
        return forms[1]
    return forms[2]


def number_under_thousand_to_words(value: int) -> str:
    """Convert a number below one thousand into Polish words.

    Args:
        value: Integer in the range `0-999`.

    Returns:
        Textual representation of the number in Polish.
    """
    words: list[str] = []
    hundreds = value // 100
    remainder = value % 100
    tens = remainder // 10
    ones = remainder % 10

    if hundreds:
        words.append(HUNDREDS[hundreds])
    if 10 <= remainder <= 19:
        words.append(TEENS[remainder - 10])
    else:
        if tens >= 2:
            words.append(TENS[tens])
        if ones:
            words.append(ONES[ones])
    return " ".join(words)


def integer_to_polish_words(value: int) -> str:
    """Convert a non-negative integer into Polish words.

    Args:
        value: Integer value to convert.

    Returns:
        Textual representation of the number in Polish.
    """
    if value == 0:
        return ONES[0]

    words: list[str] = []
    scale_index = 0
    current_value = value
    while current_value:
        group = current_value % 1000
        current_value //= 1000
        if group:
            group_words = number_under_thousand_to_words(group)
            scale_form = choose_plural_form(group, SCALE_FORMS[scale_index])
            words.append(f"{group_words} {scale_form}".strip())
        scale_index += 1

    return " ".join(reversed(words))


def amount_to_words(value: Decimal) -> str:
    """Convert a decimal money value into Polish invoice wording.

    Args:
        value: Monetary value to convert.

    Returns:
        Textual amount with grosze formatted as `/100`.
    """
    quantized = quantize_money(value)
    integer_part = int(quantized)
    grosze = int((quantized - Decimal(integer_part)) * 100)

    return f"{integer_to_polish_words(integer_part)} zł {grosze:02d}/100"


def build_invoice_data(period: Period, amount: Decimal) -> InvoiceData:
    """Build invoice fields derived from the target period and amount.

    Args:
        period: Billing period for the invoice.
        amount: Invoice total amount.

    Returns:
        Prepared invoice data ready for PDF rendering.
    """
    issue_date = last_day_of_month(period)
    due_date = issue_date + timedelta(days=14)
    issue_date_text = issue_date.isoformat()
    return InvoiceData(
        number=period.invoice_number,
        issue_date=issue_date_text,
        sale_date=issue_date_text,
        due_date=due_date.isoformat(),
        amount=quantize_money(amount),
        amount_words=amount_to_words(amount),
    )


def resolve_invoice_font_paths() -> tuple[Path, Path]:
    """Resolve the first supported regular and bold TTF font pair.

    Returns:
        Tuple containing paths to regular and bold TTF fonts.

    Raises:
        PdfGenerationError: If none of the supported platform font pairs exist.
    """
    for regular_path, bold_path in FONT_CANDIDATES:
        if regular_path.exists() and bold_path.exists():
            return regular_path, bold_path

    raise PdfGenerationError("Could not find a supported TTF font pair for invoice PDF generation.")


def register_invoice_fonts(pdfmetrics: PdfMetricsLike, tt_font: TTFontFactory) -> None:
    """Register invoice fonts with ReportLab if needed.

    Args:
        pdfmetrics: ReportLab font registry.
        tt_font: Factory used to construct TTF font objects.
    """
    regular_path, bold_path = resolve_invoice_font_paths()
    if FONT_REGULAR_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(tt_font(FONT_REGULAR_NAME, str(regular_path)))
    if FONT_BOLD_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(tt_font(FONT_BOLD_NAME, str(bold_path)))


def draw_text(pdf_canvas: CanvasLike, x_position: float, y_position: float, text: str, font: str, size: int) -> None:
    """Draw left-aligned text on the PDF canvas.

    Args:
        pdf_canvas: Target PDF canvas.
        x_position: Horizontal position.
        y_position: Vertical position.
        text: Text to draw.
        font: Registered font name.
        size: Font size in points.
    """
    pdf_canvas.setFont(font, size)
    pdf_canvas.drawString(x_position, y_position, text)


def draw_right_text(
    pdf_canvas: CanvasLike,
    x_position: float,
    y_position: float,
    text: str,
    font: str,
    size: int,
) -> None:
    """Draw right-aligned text on the PDF canvas.

    Args:
        pdf_canvas: Target PDF canvas.
        x_position: Right edge position.
        y_position: Vertical position.
        text: Text to draw.
        font: Registered font name.
        size: Font size in points.
    """
    pdf_canvas.setFont(font, size)
    pdf_canvas.drawRightString(x_position, y_position, text)


def draw_header(
    pdf_canvas: CanvasLike,
    invoice: InvoiceData,
    left: float,
    right: float,
    top: float,
    label_value_x: float,
) -> float:
    """Draw the invoice header section.

    Args:
        pdf_canvas: Target PDF canvas.
        invoice: Prepared invoice data.
        left: Left content boundary.
        right: Right content boundary.
        top: Top content boundary.
        label_value_x: X coordinate used for header values.

    Returns:
        Y coordinate of the divider line below the header.
    """
    text_y = top
    draw_text(pdf_canvas, left, text_y, "Faktura", FONT_REGULAR_NAME, 10)
    draw_text(pdf_canvas, label_value_x, text_y, invoice.number, FONT_BOLD_NAME, 10)

    text_y -= 24
    draw_text(pdf_canvas, left, text_y, "Miejsce wystawienia", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, text_y, INVOICE_PLACE, FONT_BOLD_NAME, 8)
    text_y -= 12
    draw_text(pdf_canvas, left, text_y, "Data wystawienia", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, text_y, invoice.issue_date, FONT_BOLD_NAME, 8)
    text_y -= 12
    draw_text(pdf_canvas, left, text_y, "Data sprzedaży", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, text_y, invoice.sale_date, FONT_BOLD_NAME, 8)

    divider_y = text_y - 12
    pdf_canvas.line(left, divider_y, right, divider_y)

    return divider_y


def draw_parties_section(pdf_canvas: CanvasLike, left: float, divider_y: float, millimeters: float) -> float:
    """Draw seller and buyer details.

    Args:
        pdf_canvas: Target PDF canvas.
        left: Left content boundary.
        divider_y: Y coordinate below the header.
        millimeters: ReportLab millimeter unit.

    Returns:
        Top Y coordinate of the parties section.
    """
    section_top = divider_y - 22
    buyer_left = left + 95 * millimeters

    draw_text(pdf_canvas, left, section_top, "Sprzedawca", FONT_BOLD_NAME, 9)
    draw_text(pdf_canvas, buyer_left, section_top, "Nabywca", FONT_BOLD_NAME, 9)
    for index, line in enumerate(SELLER_LINES, start=1):
        draw_text(pdf_canvas, left, section_top - index * 11, line, FONT_REGULAR_NAME, 8)
    for index, line in enumerate(BUYER_LINES, start=1):
        draw_text(pdf_canvas, buyer_left, section_top - index * 11, line, FONT_REGULAR_NAME, 8)

    return section_top


def draw_invoice_table(
    pdf_canvas: CanvasLike,
    invoice: InvoiceData,
    left: float,
    right: float,
    section_top: float,
    millimeters: float,
    content_width: float,
) -> float:
    """Draw the invoice line-item table and totals.

    Args:
        pdf_canvas: Target PDF canvas.
        invoice: Prepared invoice data.
        left: Left content boundary.
        right: Right content boundary.
        section_top: Top Y coordinate of the parties section.
        millimeters: ReportLab millimeter unit.
        content_width: Width of the printable content area.

    Returns:
        Bottom Y coordinate of the totals row.
    """
    table_top = section_top - 66
    header_bottom = table_top - 16
    row_bottom = header_bottom - 16
    total_bottom = row_bottom - 11
    column_x = [
        left,
        left + 15 * millimeters,
        left + 95 * millimeters,
        left + 107 * millimeters,
        left + 123 * millimeters,
        left + 148 * millimeters,
        right,
    ]

    pdf_canvas.setFillGray(0.92)
    pdf_canvas.rect(left, header_bottom, content_width, 16, stroke=0, fill=1)
    pdf_canvas.setFillGray(0)

    pdf_canvas.rect(left, row_bottom, column_x[4] - left, table_top - row_bottom, stroke=1, fill=0)
    pdf_canvas.rect(column_x[4], total_bottom, right - column_x[4], table_top - total_bottom, stroke=1, fill=0)
    for x_position in column_x[1:4]:
        pdf_canvas.line(x_position, row_bottom, x_position, table_top)
    pdf_canvas.line(column_x[4], total_bottom, column_x[4], table_top)
    pdf_canvas.line(column_x[5], total_bottom, column_x[5], table_top)
    pdf_canvas.line(left, header_bottom, right, header_bottom)
    pdf_canvas.line(left, row_bottom, right, row_bottom)

    header_y = table_top - 11
    draw_text(pdf_canvas, left + 4, header_y, "Lp.", FONT_BOLD_NAME, 7)
    draw_text(pdf_canvas, column_x[1] + 4, header_y, "Nazwa towaru lub usługi", FONT_BOLD_NAME, 7)
    draw_text(pdf_canvas, column_x[2] + 4, header_y, "Jm.", FONT_BOLD_NAME, 7)
    draw_text(pdf_canvas, column_x[3] + 4, header_y, "Ilość", FONT_BOLD_NAME, 7)
    draw_right_text(pdf_canvas, column_x[5] - 6, header_y, "Cena", FONT_BOLD_NAME, 7)
    draw_right_text(pdf_canvas, right - 4, header_y, "Wartość", FONT_BOLD_NAME, 7)

    row_y = header_bottom - 11
    amount_text = format_currency_pln(invoice.amount)
    draw_text(pdf_canvas, left + 4, row_y, "1", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, column_x[1] + 4, row_y, SERVICE_DESCRIPTION, FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, column_x[2] + 4, row_y, "kpl.", FONT_REGULAR_NAME, 8)
    draw_right_text(pdf_canvas, column_x[4] - 4, row_y, "1,00", FONT_REGULAR_NAME, 8)
    draw_right_text(pdf_canvas, column_x[5] - 4, row_y, amount_text, FONT_REGULAR_NAME, 8)
    draw_right_text(pdf_canvas, right - 4, row_y, amount_text, FONT_REGULAR_NAME, 8)

    total_y = total_bottom + 3
    draw_right_text(pdf_canvas, column_x[5] - 4, total_y, "Razem", FONT_BOLD_NAME, 8)
    draw_right_text(pdf_canvas, right - 4, total_y, amount_text, FONT_BOLD_NAME, 8)

    return total_bottom


def draw_payment_section(
    pdf_canvas: CanvasLike,
    invoice: InvoiceData,
    left: float,
    right: float,
    top: float,
    label_value_x: float,
) -> float:
    """Draw payment details for the invoice.

    Args:
        pdf_canvas: Target PDF canvas.
        invoice: Prepared invoice data.
        left: Left content boundary.
        right: Right content boundary.
        top: Top Y coordinate for the section.
        label_value_x: X coordinate used for field values.

    Returns:
        Y coordinate of the last payment detail line.
    """
    payment_top = top - 30
    pdf_canvas.line(left, payment_top, right, payment_top)
    payment_y = payment_top - 14
    draw_text(pdf_canvas, left, payment_y, "Termin płatności", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, payment_y, invoice.due_date, FONT_BOLD_NAME, 8)
    payment_y -= 11
    draw_text(pdf_canvas, left, payment_y, "Sposób płatności", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, payment_y, PAYMENT_METHOD, FONT_BOLD_NAME, 8)
    payment_y -= 11
    draw_text(pdf_canvas, left, payment_y, "Rachunek bankowy", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, payment_y, BANK_ACCOUNT, FONT_BOLD_NAME, 8)

    return payment_y


def draw_amount_section(
    pdf_canvas: CanvasLike,
    invoice: InvoiceData,
    left: float,
    right: float,
    top: float,
    label_value_x: float,
) -> float:
    """Draw the amount due and textual amount section.

    Args:
        pdf_canvas: Target PDF canvas.
        invoice: Prepared invoice data.
        left: Left content boundary.
        right: Right content boundary.
        top: Top Y coordinate for the section.
        label_value_x: X coordinate used for field values.

    Returns:
        Y coordinate of the last line in the section.
    """
    amount_top = top - 20
    amount_text = format_currency_pln(invoice.amount)
    pdf_canvas.line(left, amount_top, right, amount_top)
    amount_y = amount_top - 16
    draw_text(pdf_canvas, left, amount_y, "Do zapłaty", FONT_REGULAR_NAME, 9)
    draw_text(pdf_canvas, label_value_x, amount_y, amount_text, FONT_BOLD_NAME, 9)
    amount_y -= 12
    draw_text(pdf_canvas, left, amount_y, "Słownie", FONT_REGULAR_NAME, 8)
    draw_text(pdf_canvas, label_value_x, amount_y, invoice.amount_words, FONT_BOLD_NAME, 8)

    return amount_y


def draw_vat_note(pdf_canvas: CanvasLike, left: float, right: float, top: float) -> None:
    """Draw the VAT exemption note.

    Args:
        pdf_canvas: Target PDF canvas.
        left: Left content boundary.
        right: Right content boundary.
        top: Top Y coordinate for the note.
    """
    vat_y = top - 21
    pdf_canvas.line(left, vat_y + 8, right, vat_y + 8)
    draw_text(pdf_canvas, left, vat_y, VAT_NOTE, FONT_REGULAR_NAME, 8)


def draw_signature(pdf_canvas: CanvasLike, left: float, millimeters: float) -> None:
    """Draw the issuer signature block.

    Args:
        pdf_canvas: Target PDF canvas.
        left: Left content boundary.
        millimeters: ReportLab millimeter unit.
    """
    signature_y = 90
    signature_left = left
    signature_right = left + 55 * millimeters
    signature_center = (signature_left + signature_right) / 2
    pdf_canvas.line(signature_left, signature_y, signature_right, signature_y)
    pdf_canvas.setFont(FONT_REGULAR_NAME, 8)
    pdf_canvas.drawCentredString(signature_center, signature_y + 2, SELLER_LINES[0])
    pdf_canvas.setFont(FONT_REGULAR_NAME, 6)
    pdf_canvas.drawCentredString(signature_center, signature_y - 10, "wystawca")


def generate_invoice_pdf(invoice: InvoiceData, output_path: Path) -> Path:
    """Generate an invoice PDF on disk.

    Args:
        invoice: Prepared invoice data to render.
        output_path: Destination path for the generated PDF.

    Returns:
        Expanded output path of the generated PDF file.

    Raises:
        PdfGenerationError: If ReportLab or a supported font pair is not
            available.
    """
    canvas_factory, a4, millimeters, pdfmetrics, tt_font = ensure_reportlab_available()
    register_invoice_fonts(pdfmetrics, tt_font)

    expanded_output_path = output_path.expanduser()
    expanded_output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf_canvas = canvas_factory(str(expanded_output_path), pagesize=a4, pageCompression=0)
    page_width, page_height = a4
    left = 18 * millimeters
    right = page_width - 18 * millimeters
    content_width = right - left
    top = page_height - 18 * millimeters
    label_value_x = left + 40 * millimeters

    divider_y = draw_header(pdf_canvas, invoice, left, right, top, label_value_x)
    section_top = draw_parties_section(pdf_canvas, left, divider_y, millimeters)
    total_bottom = draw_invoice_table(pdf_canvas, invoice, left, right, section_top, millimeters, content_width)
    payment_y = draw_payment_section(pdf_canvas, invoice, left, right, total_bottom, label_value_x)
    amount_y = draw_amount_section(pdf_canvas, invoice, left, right, payment_y, label_value_x)
    draw_vat_note(pdf_canvas, left, right, amount_y)
    draw_signature(pdf_canvas, left, millimeters)

    pdf_canvas.showPage()
    pdf_canvas.save()

    return expanded_output_path

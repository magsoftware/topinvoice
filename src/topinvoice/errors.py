from __future__ import annotations


class TopinvoiceError(Exception):
    """Base error for the application."""


class ConfigurationError(TopinvoiceError):
    """Raised when required configuration is missing or invalid."""


class CsvAnalysisError(TopinvoiceError):
    """Raised when the downloaded CSV cannot be parsed."""


class ScrapingError(TopinvoiceError):
    """Raised when browser automation fails."""


class PdfGenerationError(TopinvoiceError):
    """Raised when the invoice PDF cannot be generated."""

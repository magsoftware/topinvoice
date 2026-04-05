from __future__ import annotations

from collections.abc import Sequence

from topinvoice.cli import parse_arguments
from topinvoice.errors import TopinvoiceError
from topinvoice.logging import configure_logging, get_logger
from topinvoice.pipeline import run_pipeline


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    logger = get_logger()

    try:
        options = parse_arguments(argv)
        run_pipeline(options)
    except TopinvoiceError as error:
        logger.error("%s", error)
        return 1

    return 0

"""CSV runtime safety defaults for very large text fields."""

from __future__ import annotations

import csv
import sys


def configure_csv_field_limit() -> None:
    """Raise csv parser field size limit to the largest supported value."""
    max_size = sys.maxsize
    while max_size > 0:
        try:
            csv.field_size_limit(max_size)
        except OverflowError:
            max_size //= 10
        else:
            return

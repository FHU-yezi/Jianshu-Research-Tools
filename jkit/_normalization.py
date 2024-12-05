from __future__ import annotations

from datetime import datetime
from decimal import Context, Decimal


def normalize_datetime(x: int | float | str, /) -> datetime:
    if isinstance(x, (int, float)):
        result = datetime.fromtimestamp(x)
    else:
        result = datetime.fromisoformat(x)

    return result.replace(microsecond=0, tzinfo=None)


def normalize_assets_amount(x: int, /) -> float:
    return x / 1000


def normalize_assets_amount_precise(x: int, /) -> Decimal:
    return Context(prec=18).create_decimal_from_float(x / 10**18)


def normalize_percentage(x: int | float, /) -> float:
    return x / 100

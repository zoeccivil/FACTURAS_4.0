# date_utils.py
from __future__ import annotations
import datetime
from typing import Any, Optional

try:
    from google.cloud.firestore_v1._helpers import DatetimeWithNanoseconds  # type: ignore
except Exception:
    DatetimeWithNanoseconds = None  # type: ignore

def to_date(value: Any) -> Optional[datetime.date]:
    if value is None:
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    try:
        if DatetimeWithNanoseconds is not None and isinstance(value, DatetimeWithNanoseconds):  # type: ignore
            return value.date()
    except Exception:
        pass
    if isinstance(value, str):
        s = value.strip()
        # formato ISO esperado
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
            except Exception:
                pass
    # fallback: tratar de llamar .date()
    try:
        if hasattr(value, "date"):
            d = value.date()
            if isinstance(d, datetime.date):
                return d
    except Exception:
        pass
    return None

def date_to_iso(value: Any) -> Optional[str]:
    d = to_date(value)
    return d.isoformat() if d else None
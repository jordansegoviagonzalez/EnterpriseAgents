from __future__ import annotations

import datetime


def utc_now_iso() -> str:
    return datetime.datetime.now(tz=datetime.UTC).isoformat()

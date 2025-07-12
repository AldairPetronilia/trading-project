from datetime import UTC, datetime, timezone


def decode_content(date_time_str: str) -> datetime:
    if date_time_str.endswith("Z"):
        return datetime.fromisoformat(date_time_str[:-1]).replace(tzinfo=UTC)
    return datetime.fromisoformat(date_time_str)


def encode_content(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    utc_offset = dt.utcoffset()
    if dt.tzinfo == UTC or (utc_offset is not None and utc_offset.total_seconds() == 0):
        return dt.isoformat().replace("+00:00", "Z")
    return dt.isoformat()

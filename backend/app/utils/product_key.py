from datetime import datetime


def build_product_key(file_size_bytes: int, now: datetime | None = None) -> str:
    ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{file_size_bytes}"

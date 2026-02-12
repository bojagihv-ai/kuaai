from datetime import datetime

from app.utils.product_key import build_product_key


def test_product_key_exact_format():
    key = build_product_key(12345, now=datetime(2024, 1, 2, 3, 4, 5))
    assert key == "20240102_030405_12345"

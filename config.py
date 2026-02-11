"""Configuration for 1688 sourcing and Coupang listing automation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Config:
    # Product discovery strategy
    categories_or_keywords: list[str] = field(
        default_factory=lambda: ["주방용품", "수납", "생활잡화"]
    )
    max_items_per_run: int = 10

    # Margin model
    desired_margin: float = 0.25
    shipping_cost: float = 2500.0
    import_duty: float = 800.0
    other_costs: float = 700.0

    # FX (CNY -> KRW)
    currency_rate: float = 190.0
    fx_api_url: str = os.getenv("FX_API_URL", "https://api.exchangerate.host/convert")

    # API credentials / endpoints
    coupang_api_credentials: dict[str, str] = field(
        default_factory=lambda: {
            "accessKey": os.getenv("COUPANG_ACCESS_KEY", ""),
            "secretKey": os.getenv("COUPANG_SECRET_KEY", ""),
            "vendorId": os.getenv("COUPANG_VENDOR_ID", ""),
        }
    )
    coupang_search_endpoint: str = os.getenv("COUPANG_SEARCH_ENDPOINT", "")
    source_1688_endpoint: str = os.getenv("SOURCE_1688_ENDPOINT", "")
    source_1688_api_key: str = os.getenv("SOURCE_1688_API_KEY", "")

    # Translation
    translator_api_key: str = os.getenv("TRANSLATOR_API_KEY", "")
    translator_endpoint: str = os.getenv(
        "TRANSLATOR_ENDPOINT",
        "https://translation.googleapis.com/language/translate/v2",
    )

    # Notifications
    notification_email: str = os.getenv("NOTIFICATION_EMAIL", "")
    slack_webhook: str = os.getenv("SLACK_WEBHOOK", "")

    # Runtime behavior (for TOS-safe throttling)
    request_timeout_sec: int = 15
    request_delay_sec: float = 0.35
    user_agent: str = "kuaai-bot/1.1 (compliance-friendly)"

    # Storage
    data_dir: Path = Path("data")
    sqlite_path: Path = Path("data/results.db")
    latest_json_path: Path = Path("data/latest_results.json")

    # Automation
    auto_register: bool = False


config = Config()


def as_dict() -> dict[str, Any]:
    return config.__dict__.copy()

"""Analyze products by margin and Coupang competition."""
from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

from config import config

_rate_cache: dict[str, float] = {"value": config.currency_rate}


def update_currency_rate() -> float:
    """Refresh CNY->KRW exchange rate."""
    try:
        resp = requests.get(
            config.fx_api_url,
            params={"from": "CNY", "to": "KRW", "amount": 1},
            timeout=config.request_timeout_sec,
            headers={"User-Agent": config.user_agent},
        )
        if resp.ok:
            rate = float(resp.json().get("result", config.currency_rate))
            if rate > 0:
                _rate_cache["value"] = rate
    except requests.RequestException:
        pass
    return _rate_cache["value"]


def get_current_rate() -> float:
    return _rate_cache.get("value", config.currency_rate)


def search_coupang(keyword: str) -> int:
    """Return count of matching sellers via legal search endpoint/API."""
    if not config.coupang_search_endpoint:
        return 0

    try:
        resp = requests.get(
            config.coupang_search_endpoint,
            params={"q": keyword},
            timeout=config.request_timeout_sec,
            headers={"User-Agent": config.user_agent},
        )
        if resp.ok:
            return int(resp.json().get("seller_count", 0) or 0)
    except requests.RequestException:
        return 0
    return 0


def analyze_and_select(
    products: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select products that satisfy target margin and low competition."""
    selected: list[dict[str, Any]] = []
    new_products: list[dict[str, Any]] = []

    for item in products:
        cogs = (
            float(item.get("price_cny", 0.0)) * get_current_rate()
            + config.shipping_cost
            + config.import_duty
            + config.other_costs
        )
        sale_price = cogs / (1.0 - config.desired_margin)
        gross_margin = (sale_price - cogs) / sale_price
        competitors = search_coupang(item.get("translated_name") or item.get("name_zh", ""))

        item.update(
            {
                "cogs": round(cogs, 2),
                "sale_price": round(sale_price, 2),
                "gross_margin": round(gross_margin, 4),
                "coupang_competitors": competitors,
            }
        )

        if competitors == 0:
            new_products.append(item)
        if gross_margin >= config.desired_margin and competitors <= 1:
            selected.append(item)

        time.sleep(config.request_delay_sec)

    return selected, new_products


def to_dataframe(products: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.json_normalize(products) if products else pd.DataFrame()

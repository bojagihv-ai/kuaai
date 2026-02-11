"""Fetch products from a legal/allowed 1688 data provider."""
from __future__ import annotations

import time
from typing import Any

import requests

from config import config


def translate_zh_to_ko(text: str) -> str:
    """Translate Chinese -> Korean using a legal API endpoint."""
    if not text or not config.translator_api_key:
        return text

    params = {"key": config.translator_api_key}
    payload = {"q": text, "source": "zh-CN", "target": "ko", "format": "text"}
    try:
        resp = requests.post(
            config.translator_endpoint,
            params=params,
            json=payload,
            timeout=config.request_timeout_sec,
            headers={"User-Agent": config.user_agent},
        )
        if resp.ok:
            data = resp.json()
            translated = data.get("data", {}).get("translations", [{}])[0].get("translatedText")
            return translated or text
    except requests.RequestException:
        return text
    return text


def _normalize_item(row: dict[str, Any], keyword: str) -> dict[str, Any]:
    name_zh = str(row.get("title") or row.get("name") or "").strip()
    return {
        "product_id": str(row.get("id", "")),
        "name_zh": name_zh,
        "translated_name": translate_zh_to_ko(name_zh),
        "price_cny": float(row.get("price", 0.0) or 0.0),
        "moq": int(row.get("moq", 1) or 1),
        "product_url": row.get("url", ""),
        "image_url": row.get("image", ""),
        "keyword": keyword,
    }


def fetch_1688_products(keyword: str, page: int = 1) -> list[dict[str, Any]]:
    """Input: keyword/page. Output: normalized item dict list.

    NOTE: You must set SOURCE_1688_ENDPOINT to a provider you are legally
    allowed to use. If missing, this function returns an empty list.
    """
    if not config.source_1688_endpoint:
        return []

    headers = {
        "Accept": "application/json",
        "User-Agent": config.user_agent,
    }
    if config.source_1688_api_key:
        headers["Authorization"] = f"Bearer {config.source_1688_api_key}"

    params = {
        "q": keyword,
        "page": page,
        "page_size": min(config.max_items_per_run, 20),
    }

    try:
        resp = requests.get(
            config.source_1688_endpoint,
            params=params,
            headers=headers,
            timeout=config.request_timeout_sec,
        )
        if not resp.ok:
            return []
        raw_items = resp.json().get("items", [])
    except requests.RequestException:
        return []

    products: list[dict[str, Any]] = []
    for row in raw_items:
        products.append(_normalize_item(row, keyword))
        time.sleep(config.request_delay_sec)
    return products

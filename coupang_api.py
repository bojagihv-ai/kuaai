"""Coupang OPEN API helpers (auth + endpoint wrappers)."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlencode

import requests

from config import config

BASE_URL = "https://api-gateway.coupang.com"


def _auth_header(method: str, path_with_query: str) -> dict[str, str]:
    access_key = config.coupang_api_credentials.get("accessKey", "")
    secret_key = config.coupang_api_credentials.get("secretKey", "")

    now = dt.datetime.utcnow().strftime("%y%m%dT%H%M%SZ")
    message = f"{now}{method}{path_with_query}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "Authorization": (
            f"CEA algorithm=HmacSHA256, access-key={access_key}, "
            f"signed-date={now}, signature={signature}"
        ),
        "Content-Type": "application/json;charset=UTF-8",
    }


def _request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query = f"?{urlencode(params)}" if params else ""
    path_with_query = f"{path}{query}"
    url = f"{BASE_URL}{path_with_query}"
    headers = _auth_header(method.upper(), path_with_query)

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            data=json.dumps(payload) if payload else None,
            timeout=config.request_timeout_sec,
        )
        return resp.json() if resp.content else {}
    except requests.RequestException as exc:
        return {"error": str(exc), "path": path_with_query}


def create_shipping_location(payload: dict[str, Any]) -> dict[str, Any]:
    return _request(
        "POST",
        "/v2/providers/marketplace_openapi/apis/api/v1/vendor/shipping-place/outbound",
        payload=payload,
    )


def create_return_location(payload: dict[str, Any]) -> dict[str, Any]:
    return _request(
        "POST",
        "/v2/providers/openapi/apis/api/v1/vendor/returnShippingCenters",
        payload=payload,
    )


def get_category_code(keyword: str) -> dict[str, Any]:
    return _request(
        "GET",
        "/v2/providers/seller_api/apis/api/v1/marketplace/meta/category-related-metas/display-category-codes",
        params={"keyword": keyword},
    )


def map_to_coupang_format(
    item: dict[str, Any],
    category_code: str,
    shipping_code: str,
    return_code: str,
) -> dict[str, Any]:
    now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    name = item.get("translated_name") or item.get("name_zh") or "상품"
    sale_price = max(100, int(float(item.get("sale_price", 0) or 0)))

    return {
        "displayCategoryCode": category_code,
        "sellerProductName": name,
        "saleStartedAt": now,
        "saleEndedAt": "2099-12-31T00:00:00",
        "deliveryMethod": "SEQUENCIAL",
        "deliveryCompanyCode": "KGB",
        "deliveryChargeType": "FREE",
        "returnCenterCode": return_code,
        "outboundShippingPlaceCode": shipping_code,
        "items": [
            {
                "itemName": name,
                "originalPrice": sale_price,
                "salePrice": sale_price,
                "maximumBuyCount": 999,
                "images": [
                    {
                        "imageOrder": 0,
                        "imageType": "REPRESENTATION",
                        "vendorPath": item.get("image_url", ""),
                    }
                ],
            }
        ],
        "searchTags": [name[:20]],
        "afterServiceInformation": "채팅문의",
        "afterServiceContactNumber": "010-0000-0000",
    }


def create_product(product_info: dict[str, Any]) -> dict[str, Any]:
    return _request(
        "POST",
        "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products",
        payload=product_info,
    )

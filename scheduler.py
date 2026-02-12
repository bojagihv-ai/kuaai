"""30-minute scheduler: fetch -> analyze -> save -> notify -> optional register."""
from __future__ import annotations

import time
from typing import Any

import schedule

from analyze_products import analyze_and_select, update_currency_rate
from config import config
from coupang_api import (
    create_product,
    create_return_location,
    create_shipping_location,
    get_category_code,
    map_to_coupang_format,
)
from fetch_1688_products import fetch_1688_products
from notifier import notify_new_products, send_notification
from storage import save_results


def fetch_products_once() -> list[dict[str, Any]]:
    """모든 카테고리/키워드에 대해 1688에서 상품을 검색해 Raw 데이터를 반환한다."""
    results: list[dict[str, Any]] = []
    for keyword in config.categories_or_keywords:
        page = 1
        while len(results) < config.max_items_per_run:
            items = fetch_1688_products(keyword, page)
            if not items:
                break
            results.extend(items)
            page += 1
            if len(results) >= config.max_items_per_run:
                break
    return results[: config.max_items_per_run]


def analyze_and_select_products(
    products: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """상품 데이터를 분석하고 마진률이 목표 이상이며 쿠팡에서 경쟁이 없는 상품을 선별한다."""
    return analyze_and_select(products)


def register_products_on_coupang(products: list[dict[str, Any]]) -> None:
    """선택된 상품을 쿠팡 OPEN API로 자동 등록한다."""
    shipping_payload = {
        "placeName": "기본 출고지",
        "remoteInfo": {"deliveryCode": "", "deliveryName": ""},
        "usable": True,
    }
    return_payload = {
        "shippingPlaceName": "기본 반품지",
        "placeAddresses": [
            {
                "addressType": "JIBUN",
                "address": "서울",
                "companyContactNumber": "01000000000",
            }
        ],
    }

    ship_resp = create_shipping_location(shipping_payload)
    shipping_code = str(ship_resp.get("content", {}).get("outboundShippingPlaceCode", ""))

    ret_resp = create_return_location(return_payload)
    return_code = str(ret_resp.get("content", {}).get("returnCenterCode", ""))

    for item in products:
        category_resp = get_category_code(item.get("translated_name", ""))
        category_list = category_resp.get("data", []) if isinstance(category_resp, dict) else []
        category_code = str(category_list[0].get("displayCategoryCode", "0")) if category_list else "0"

        payload = map_to_coupang_format(item, category_code, shipping_code, return_code)
        resp = create_product(payload)
        item["registration_status"] = "SUCCESS" if not resp.get("error") else "FAILED"
        send_notification(item, resp)


def job() -> None:
    update_currency_rate()
    raw_products = fetch_products_once()
    selected, new_only = analyze_and_select_products(raw_products)

    if new_only:
        notify_new_products(new_only)

    if config.auto_register and selected:
        register_products_on_coupang(selected)

    save_results(raw_products, selected, new_only)


def main() -> None:
    job()
    schedule.every(30).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

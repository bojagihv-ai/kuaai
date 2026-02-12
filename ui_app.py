"""Beginner-friendly browser UI for the 1688 -> Coupang pipeline.

Run with:
    streamlit run ui_app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from analyze_products import analyze_and_select, update_currency_rate
from config import config
from fetch_1688_products import fetch_1688_products
from scheduler import register_products_on_coupang
from storage import JSON_PATH, save_results

st.set_page_config(page_title="1688→쿠팡 도우미", page_icon="🛍️", layout="wide")


@st.cache_data(ttl=300)
def load_latest_json() -> dict:
    if not JSON_PATH.exists():
        return {}
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def run_once(max_items: int, keywords: list[str], auto_register: bool) -> dict:
    config.max_items_per_run = max_items
    config.categories_or_keywords = keywords
    config.auto_register = auto_register

    update_currency_rate()

    results: list[dict] = []
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
    raw = results[: config.max_items_per_run]

    selected, new_only = analyze_and_select(raw)

    if config.auto_register and selected:
        register_products_on_coupang(selected)

    save_results(raw, selected, new_only)

    return {
        "raw": raw,
        "selected": selected,
        "new_only": new_only,
    }


st.title("🛍️ 1688 → 쿠팡 자동화 도우미")
st.caption("초보용 버튼형 UI: 설정 입력 → 1회 실행 → 결과 확인")

with st.sidebar:
    st.header("실행 설정")
    keywords_text = st.text_area(
        "키워드(한 줄에 하나)",
        value="\n".join(config.categories_or_keywords),
        height=120,
    )
    max_items = st.number_input("한 번에 가져올 최대 상품 수", min_value=1, max_value=100, value=config.max_items_per_run)
    desired_margin = st.number_input("목표 마진율 (예: 0.25 = 25%)", min_value=0.01, max_value=0.9, value=float(config.desired_margin), step=0.01)
    shipping_cost = st.number_input("예상 운송비(원)", min_value=0, value=int(config.shipping_cost), step=100)
    import_duty = st.number_input("예상 관세(원)", min_value=0, value=int(config.import_duty), step=100)
    other_costs = st.number_input("기타 비용(원)", min_value=0, value=int(config.other_costs), step=100)
    auto_register = st.checkbox("선택상품 쿠팡 자동등록 실행", value=False)

    st.markdown("---")
    st.info("※ 실제 API 주소/키는 환경변수로 설정해야 동작합니다.")

# apply sidebar values
config.desired_margin = float(desired_margin)
config.shipping_cost = float(shipping_cost)
config.import_duty = float(import_duty)
config.other_costs = float(other_costs)

keywords = [line.strip() for line in keywords_text.splitlines() if line.strip()]
if not keywords:
    keywords = config.categories_or_keywords

col1, col2 = st.columns([1, 1])
with col1:
    run_button = st.button("🚀 지금 1회 실행", use_container_width=True)
with col2:
    refresh_latest = st.button("🔄 저장된 최신 결과 불러오기", use_container_width=True)

if run_button:
    with st.spinner("실행 중입니다... (API 응답에 따라 10~60초)"):
        outcome = run_once(max_items=max_items, keywords=keywords, auto_register=auto_register)

    st.success("실행 완료!")
    st.write(f"총 수집: {len(outcome['raw'])}개 / 선별: {len(outcome['selected'])}개 / 신규: {len(outcome['new_only'])}개")

    if outcome["raw"]:
        st.subheader("전체 수집 결과")
        st.dataframe(pd.DataFrame(outcome["raw"]), use_container_width=True)

    if outcome["selected"]:
        st.subheader("선별 상품")
        st.dataframe(pd.DataFrame(outcome["selected"]), use_container_width=True)

    if outcome["new_only"]:
        st.subheader("신규 상품(경쟁 0)")
        st.dataframe(pd.DataFrame(outcome["new_only"]), use_container_width=True)

if refresh_latest:
    latest = load_latest_json()
    if not latest:
        st.warning("아직 저장된 결과가 없습니다. 먼저 1회 실행해주세요.")
    else:
        st.success("최신 저장 결과를 불러왔습니다.")
        st.json({
            "run_at": latest.get("run_at"),
            "raw_count": latest.get("raw_count"),
            "selected_count": latest.get("selected_count"),
            "new_count": latest.get("new_count"),
        })
        items = latest.get("items", [])
        if items:
            st.dataframe(pd.DataFrame(items), use_container_width=True)

st.markdown("---")
st.markdown(
    """
### 사용방법 (초간단)
1. 왼쪽에서 키워드/마진/비용 입력
2. **지금 1회 실행** 클릭
3. 결과표 확인
4. 필요하면 **최신 결과 불러오기** 클릭

실행 데이터 파일:
- JSON: `data/latest_results.json`
- SQLite: `data/results.db`
"""
)

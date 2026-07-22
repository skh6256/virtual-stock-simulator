import random
from typing import Any, Literal

import pandas as pd
import streamlit as st


DECIMALS = 2
UP_MULTIPLIER = 1.10
DOWN_MULTIPLIER = 10 / 11


def r2(value: float) -> float:
    """실제 계산값은 소수점 셋째 자리에서 반올림합니다."""
    return round(float(value), DECIMALS)


def comma(value: float, decimals: int = 2) -> str:
    """천 단위 쉼표를 적용한 숫자 문자열."""
    return f"{float(value):,.{decimals}f}"


def parse_number(text: str, field_name: str) -> float:
    """쉼표가 포함된 입력값을 실수로 변환합니다."""
    cleaned = str(text).replace(",", "").strip()
    if cleaned == "":
        raise ValueError(f"{field_name}을 입력해주세요.")
    try:
        return r2(float(cleaned))
    except ValueError as exc:
        raise ValueError(
            f"{field_name}은 숫자로 입력해주세요. 예: 20,000,000"
        ) from exc


def initialize_state(initial_capital: float, initial_price: float) -> None:
    initial_capital = r2(initial_capital)
    initial_price = r2(initial_price)

    st.session_state.day = 1
    st.session_state.initial_capital = initial_capital
    st.session_state.initial_price = initial_price
    st.session_state.price = initial_price
    st.session_state.cash = initial_capital
    st.session_state.shares = 0.0
    st.session_state.avg_price = 0.0
    st.session_state.realized_pnl = 0.0
    st.session_state.last_move = "시작"
    st.session_state.trade_history = []
    st.session_state.daily_history = [
        make_daily_record(action="시작", action_amount=0.0)
    ]

    st.session_state.initial_capital_text = comma(initial_capital, 0)
    st.session_state.initial_price_text = comma(initial_price, 0)
    st.session_state.buy_amount_text = "20,000,000"
    st.session_state.sell_amount_text = "20,000,000"


def ensure_state() -> None:
    if "day" not in st.session_state:
        initialize_state(100_000_000.0, 200_000.0)


def portfolio_values() -> dict[str, float]:
    market_value = r2(st.session_state.shares * st.session_state.price)
    total_assets = r2(st.session_state.cash + market_value)
    unrealized_pnl = r2(
        (st.session_state.price - st.session_state.avg_price)
        * st.session_state.shares
    )
    total_pnl = r2(total_assets - st.session_state.initial_capital)

    total_return = (
        0.0
        if st.session_state.initial_capital == 0
        else r2(total_pnl / st.session_state.initial_capital * 100)
    )

    return {
        "market_value": market_value,
        "total_assets": total_assets,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "total_return": total_return,
    }


def make_daily_record(action: str, action_amount: float) -> dict[str, Any]:
    values = portfolio_values()
    return {
        "일차": st.session_state.day,
        "주가": r2(st.session_state.price),
        "등락": st.session_state.last_move,
        "행동": action,
        "거래금액": r2(action_amount),
        "보유현금": r2(st.session_state.cash),
        "보유수량": r2(st.session_state.shares),
        "평균매수가": r2(st.session_state.avg_price),
        "평가금액": values["market_value"],
        "총자산": values["total_assets"],
        "실현손익": r2(st.session_state.realized_pnl),
        "미실현손익": values["unrealized_pnl"],
        "누적손익": values["total_pnl"],
        "누적수익률(%)": values["total_return"],
    }


def append_daily_record(action: str, action_amount: float) -> None:
    st.session_state.daily_history.append(
        make_daily_record(action=action, action_amount=action_amount)
    )


def buy(amount: float) -> tuple[bool, str]:
    amount = r2(amount)

    if amount <= 0:
        return False, "매수금액은 0보다 커야 합니다."
    if st.session_state.price <= 0:
        return False, "주가가 0 이하이므로 매수할 수 없습니다."

    purchased_shares = r2(amount / st.session_state.price)
    if purchased_shares <= 0:
        return False, "계산된 매수수량이 0입니다."

    old_cost = r2(st.session_state.avg_price * st.session_state.shares)
    new_cost = r2(old_cost + amount)
    new_shares = r2(st.session_state.shares + purchased_shares)

    st.session_state.shares = new_shares
    st.session_state.cash = r2(st.session_state.cash - amount)
    st.session_state.avg_price = (
        r2(new_cost / new_shares) if new_shares > 0 else 0.0
    )

    st.session_state.trade_history.append(
        {
            "일차": st.session_state.day,
            "구분": "매수",
            "체결주가": r2(st.session_state.price),
            "거래금액": amount,
            "거래수량": purchased_shares,
            "실현손익": 0.0,
        }
    )
    append_daily_record("매수", amount)

    return True, (
        f"{comma(amount, 0)}원 매수 완료 "
        f"({comma(purchased_shares)}주)"
    )


def sell(amount: float) -> tuple[bool, str]:
    """입력 금액이 보유 평가액보다 크면 자동으로 전량 매도합니다."""
    amount = r2(amount)

    if amount <= 0:
        return False, "매도금액은 0보다 커야 합니다."
    if st.session_state.price <= 0:
        return False, "주가가 0 이하이므로 매도할 수 없습니다."
    if st.session_state.shares <= 0:
        return False, "보유 주식이 없습니다."

    max_sell_value = r2(st.session_state.shares * st.session_state.price)
    full_sale = amount >= max_sell_value

    if full_sale:
        sold_shares = st.session_state.shares
        proceeds = max_sell_value
    else:
        sold_shares = r2(amount / st.session_state.price)
        sold_shares = min(sold_shares, st.session_state.shares)
        proceeds = r2(sold_shares * st.session_state.price)

    realized = r2(
        (st.session_state.price - st.session_state.avg_price) * sold_shares
    )

    st.session_state.shares = r2(st.session_state.shares - sold_shares)
    st.session_state.cash = r2(st.session_state.cash + proceeds)
    st.session_state.realized_pnl = r2(
        st.session_state.realized_pnl + realized
    )

    if st.session_state.shares <= 0.01:
        st.session_state.shares = 0.0
        st.session_state.avg_price = 0.0

    st.session_state.trade_history.append(
        {
            "일차": st.session_state.day,
            "구분": "전량매도" if full_sale else "매도",
            "체결주가": r2(st.session_state.price),
            "거래금액": proceeds,
            "거래수량": r2(sold_shares),
            "실현손익": realized,
        }
    )
    append_daily_record("전량매도" if full_sale else "매도", proceeds)

    action_text = "전량 매도" if full_sale else "매도"
    return True, (
        f"{action_text} 완료: {comma(proceeds, 0)}원 "
        f"({comma(sold_shares)}주, 실현손익 {comma(realized, 0)}원)"
    )


def next_day(direction: Literal["random", "up", "down"] = "random") -> str:
    """랜덤 또는 지정된 방향으로 하루를 진행합니다."""
    if direction == "random":
        direction = "up" if random.random() < 0.5 else "down"

    if direction == "up":
        st.session_state.price = r2(
            st.session_state.price * UP_MULTIPLIER
        )
        st.session_state.last_move = "상승 (+10%)"
    else:
        st.session_state.price = r2(
            st.session_state.price * DOWN_MULTIPLIER
        )
        st.session_state.last_move = "하락 (-9.0909%)"

    st.session_state.day += 1
    append_daily_record("날짜 진행", 0.0)
    return st.session_state.last_move


def format_won(value: float) -> str:
    """원 단위 화면 표시는 소수점 없이 표시합니다."""
    return f"{comma(value, 0)}원"


def formatted_daily_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    money_columns = [
        "주가", "거래금액", "보유현금", "평균매수가", "평가금액",
        "총자산", "실현손익", "미실현손익", "누적손익",
    ]
    for col in money_columns:
        if col in result.columns:
            result[col] = result[col].map(lambda x: comma(x, 0))
    if "보유수량" in result.columns:
        result["보유수량"] = result["보유수량"].map(lambda x: comma(x))
    if "누적수익률(%)" in result.columns:
        result["누적수익률(%)"] = result["누적수익률(%)"].map(
            lambda x: f"{comma(x)}%"
        )
    return result


def formatted_trade_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in ["체결주가", "거래금액", "실현손익"]:
        if col in result.columns:
            result[col] = result[col].map(lambda x: comma(x, 0))
    if "거래수량" in result.columns:
        result["거래수량"] = result["거래수량"].map(lambda x: comma(x))
    return result


st.set_page_config(
    page_title="가상 주식시장 시뮬레이터",
    page_icon="📈",
    layout="wide",
)

# 좁은 브라우저에서도 metric 값이 ...으로 잘리지 않고 자동 축소되도록 설정합니다.
st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        min-width: 0;
    }

    [data-testid="stMetricValue"] {
        min-width: 0;
        overflow: visible !important;
    }

    [data-testid="stMetricValue"] > div {
        font-size: clamp(1.05rem, 2.45vw, 2.35rem) !important;
        line-height: 1.15 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        letter-spacing: -0.035em;
    }

    [data-testid="stMetricLabel"] {
        min-width: 0;
    }

    @media (max-width: 1100px) {
        [data-testid="stMetricValue"] > div {
            font-size: clamp(0.92rem, 2.15vw, 1.75rem) !important;
            letter-spacing: -0.055em;
        }
    }

    @media (max-width: 760px) {
        [data-testid="stMetricValue"] > div {
            font-size: clamp(0.82rem, 3.3vw, 1.35rem) !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ensure_state()

st.title("📈 가상 주식시장 시뮬레이터")
st.caption(
    "매일 50% 확률로 +10%, 50% 확률로 -9.0909% 움직입니다. "
    "실제 계산값은 소수점 셋째 자리에서 반올림하며 수수료는 0원입니다."
)

with st.sidebar:
    st.header("초기 설정")

    initial_capital_text = st.text_input(
        "초기 자본금",
        key="initial_capital_text",
        help="쉼표를 포함해 입력할 수 있습니다. 예: 100,000,000",
    )
    initial_price_text = st.text_input(
        "초기 주가",
        key="initial_price_text",
        help="쉼표를 포함해 입력할 수 있습니다. 예: 200,000",
    )

    if st.button("🔄 입력값으로 초기화", use_container_width=True):
        try:
            capital = parse_number(initial_capital_text, "초기 자본금")
            price = parse_number(initial_price_text, "초기 주가")
            if price <= 0:
                raise ValueError("초기 주가는 0보다 커야 합니다.")
            initialize_state(capital, price)
            st.success("시뮬레이션을 초기화했습니다.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

    st.divider()
    st.subheader("시장 규칙")
    st.write("상승 확률: **50%**")
    st.write("상승률: **+10%**")
    st.write("하락 확률: **50%**")
    st.write("하락률: **-9.0909%**")
    st.write("수수료: **0원**")
    st.write("보유 현금: **음수 허용**")
    st.write("초과 매도: **자동 전량 매도**")

values = portfolio_values()

top1 = st.columns(5)
top1[0].metric("현재 일차", f"{st.session_state.day:,}일")
top1[1].metric("현재 주가", format_won(st.session_state.price))
top1[2].metric("오늘 등락", st.session_state.last_move)
top1[3].metric("보유 현금", format_won(st.session_state.cash))
top1[4].metric("보유수량", f"{comma(st.session_state.shares)}주")

top2 = st.columns(5)
top2[0].metric("평균 매수가", format_won(st.session_state.avg_price))
top2[1].metric("주식 평가금액", format_won(values["market_value"]))
top2[2].metric("총자산", format_won(values["total_assets"]))
top2[3].metric("누적 수익금", format_won(values["total_pnl"]))
top2[4].metric("누적 수익률", f"{comma(values['total_return'])}%")

top3 = st.columns(2)
top3[0].metric("실현손익", format_won(st.session_state.realized_pnl))
top3[1].metric("미실현손익", format_won(values["unrealized_pnl"]))

st.divider()

control_col, buy_col, sell_col = st.columns([1, 1.4, 1.4])

with control_col:
    st.subheader("날짜 진행")

    if st.button("⏭️ 내일로 넘기기", use_container_width=True):
        next_day("random")
        st.rerun()

    forced_cols = st.columns(2)
    with forced_cols[0]:
        if st.button(
            "📈 내일로 넘기기\n(상승)",
            use_container_width=True,
        ):
            next_day("up")
            st.rerun()

    with forced_cols[1]:
        if st.button(
            "📉 내일로 넘기기\n(하락)",
            use_container_width=True,
        ):
            next_day("down")
            st.rerun()

with buy_col:
    st.subheader("매수")
    buy_amount_text = st.text_input(
        "매수금액",
        key="buy_amount_text",
        help="예: 20,000,000",
    )
    if st.button("🟢 매수", use_container_width=True):
        try:
            buy_amount = parse_number(buy_amount_text, "매수금액")
            ok, message = buy(buy_amount)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        except ValueError as error:
            st.error(str(error))

with sell_col:
    st.subheader("매도")
    sell_amount_text = st.text_input(
        "매도금액",
        key="sell_amount_text",
        help="보유 평가액보다 크게 입력하면 전량 매도됩니다.",
    )
    if st.button("🔴 매도", use_container_width=True):
        try:
            sell_amount = parse_number(sell_amount_text, "매도금액")
            ok, message = sell(sell_amount)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        except ValueError as error:
            st.error(str(error))

if st.session_state.cash < 0:
    st.warning(
        "현재 보유 현금이 음수입니다. 이 시뮬레이션에서는 허용되지만, "
        "사실상 차입 또는 레버리지 사용과 같은 효과입니다."
    )

st.divider()

history_df = pd.DataFrame(st.session_state.daily_history)

st.subheader("주가 변화")
price_chart = history_df[["일차", "주가"]].drop_duplicates(
    subset=["일차"], keep="last"
)
st.line_chart(price_chart.set_index("일차"))

st.subheader("자산 변화")
asset_chart = history_df[
    ["일차", "총자산", "보유현금", "평가금액"]
].drop_duplicates(subset=["일차"], keep="last")
st.line_chart(asset_chart.set_index("일차"))

tab1, tab2 = st.tabs(["일별 기록", "거래 내역"])

with tab1:
    st.dataframe(
        formatted_daily_table(history_df),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    trade_df = pd.DataFrame(st.session_state.trade_history)
    if trade_df.empty:
        st.info("아직 거래 내역이 없습니다.")
    else:
        st.dataframe(
            formatted_trade_table(trade_df),
            use_container_width=True,
            hide_index=True,
        )

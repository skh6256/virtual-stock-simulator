import html
import random
from typing import Any, Literal

import pandas as pd
import streamlit as st


DECIMALS = 2
UP_MULTIPLIER = 1.10
DOWN_MULTIPLIER = 10 / 11


def r2(value: float) -> float:
    return round(float(value), DECIMALS)


def comma(value: float, decimals: int = 2) -> str:
    return f"{float(value):,.{decimals}f}"


def format_won(value: float) -> str:
    return f"{comma(value, 0)}원"


def parse_number(text: str, field_name: str) -> float:
    cleaned = str(text).replace(",", "").strip()

    if not cleaned:
        raise ValueError(f"{field_name}을 입력해주세요.")

    try:
        return r2(float(cleaned))
    except ValueError as exc:
        raise ValueError(
            f"{field_name}은 숫자로 입력해주세요. 예: 20,000,000"
        ) from exc


def initialize_state(
    initial_capital: float,
    initial_price: float,
) -> None:
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
        make_daily_record(
            action="시작",
            action_amount=0.0,
        )
    ]


def ensure_state() -> None:
    defaults = {
        "initial_capital_text": "100,000,000",
        "initial_price_text": "200,000",
        "buy_amount_text": "20,000,000",
        "sell_amount_text": "20,000,000",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "day" not in st.session_state:
        initialize_state(
            initial_capital=100_000_000.0,
            initial_price=200_000.0,
        )


def portfolio_values() -> dict[str, float]:
    market_value = r2(
        st.session_state.shares
        * st.session_state.price
    )

    total_assets = r2(
        st.session_state.cash
        + market_value
    )

    unrealized_pnl = r2(
        (
            st.session_state.price
            - st.session_state.avg_price
        )
        * st.session_state.shares
    )

    total_pnl = r2(
        total_assets
        - st.session_state.initial_capital
    )

    if st.session_state.initial_capital == 0:
        total_return = 0.0
    else:
        total_return = r2(
            total_pnl
            / st.session_state.initial_capital
            * 100
        )

    return {
        "market_value": market_value,
        "total_assets": total_assets,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "total_return": total_return,
    }


def make_daily_record(
    action: str,
    action_amount: float,
) -> dict[str, Any]:
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
        "실현손익": r2(
            st.session_state.realized_pnl
        ),
        "미실현손익": values["unrealized_pnl"],
        "누적손익": values["total_pnl"],
        "누적수익률(%)": values["total_return"],
    }


def append_daily_record(
    action: str,
    action_amount: float,
) -> None:
    st.session_state.daily_history.append(
        make_daily_record(
            action=action,
            action_amount=action_amount,
        )
    )


def buy(amount: float) -> tuple[bool, str]:
    amount = r2(amount)

    if amount <= 0:
        return False, "매수금액은 0보다 커야 합니다."

    if st.session_state.price <= 0:
        return False, "주가가 0 이하이므로 매수할 수 없습니다."

    purchased_shares = r2(
        amount / st.session_state.price
    )

    if purchased_shares <= 0:
        return False, "계산된 매수수량이 0입니다."

    old_cost = r2(
        st.session_state.avg_price
        * st.session_state.shares
    )

    new_cost = r2(
        old_cost + amount
    )

    new_shares = r2(
        st.session_state.shares
        + purchased_shares
    )

    st.session_state.shares = new_shares
    st.session_state.cash = r2(
        st.session_state.cash - amount
    )

    if new_shares > 0:
        st.session_state.avg_price = r2(
            new_cost / new_shares
        )
    else:
        st.session_state.avg_price = 0.0

    st.session_state.trade_history.append(
        {
            "일차": st.session_state.day,
            "구분": "매수",
            "체결주가": r2(
                st.session_state.price
            ),
            "거래금액": amount,
            "거래수량": purchased_shares,
            "실현손익": 0.0,
        }
    )

    append_daily_record(
        action="매수",
        action_amount=amount,
    )

    return True, (
        f"{comma(amount, 0)}원 매수 완료 "
        f"({comma(purchased_shares)}주)"
    )


def sell(amount: float) -> tuple[bool, str]:
    amount = r2(amount)

    if amount <= 0:
        return False, "매도금액은 0보다 커야 합니다."

    if st.session_state.price <= 0:
        return False, "주가가 0 이하이므로 매도할 수 없습니다."

    if st.session_state.shares <= 0:
        return False, "보유 주식이 없습니다."

    max_sell_value = r2(
        st.session_state.shares
        * st.session_state.price
    )

    full_sale = amount >= max_sell_value

    if full_sale:
        sold_shares = st.session_state.shares
        proceeds = max_sell_value
    else:
        sold_shares = r2(
            amount / st.session_state.price
        )

        sold_shares = min(
            sold_shares,
            st.session_state.shares,
        )

        proceeds = r2(
            sold_shares
            * st.session_state.price
        )

    realized = r2(
        (
            st.session_state.price
            - st.session_state.avg_price
        )
        * sold_shares
    )

    st.session_state.shares = r2(
        st.session_state.shares
        - sold_shares
    )

    st.session_state.cash = r2(
        st.session_state.cash
        + proceeds
    )

    st.session_state.realized_pnl = r2(
        st.session_state.realized_pnl
        + realized
    )

    if st.session_state.shares <= 0.01:
        st.session_state.shares = 0.0
        st.session_state.avg_price = 0.0

    trade_type = (
        "전량매도"
        if full_sale
        else "매도"
    )

    st.session_state.trade_history.append(
        {
            "일차": st.session_state.day,
            "구분": trade_type,
            "체결주가": r2(
                st.session_state.price
            ),
            "거래금액": proceeds,
            "거래수량": r2(sold_shares),
            "실현손익": realized,
        }
    )

    append_daily_record(
        action=trade_type,
        action_amount=proceeds,
    )

    action_text = (
        "전량 매도"
        if full_sale
        else "매도"
    )

    return True, (
        f"{action_text} 완료: "
        f"{comma(proceeds, 0)}원 "
        f"({comma(sold_shares)}주, "
        f"실현손익 {comma(realized, 0)}원)"
    )


def next_day(
    direction: Literal[
        "random",
        "up",
        "down",
    ] = "random",
) -> None:
    if direction == "random":
        direction = (
            "up"
            if random.random() < 0.5
            else "down"
        )

    if direction == "up":
        st.session_state.price = r2(
            st.session_state.price
            * UP_MULTIPLIER
        )

        st.session_state.last_move = (
            "상승 (+10%)"
        )
    else:
        st.session_state.price = r2(
            st.session_state.price
            * DOWN_MULTIPLIER
        )

        st.session_state.last_move = (
            "하락 (-9.0909%)"
        )

    st.session_state.day += 1

    append_daily_record(
        action="날짜 진행",
        action_amount=0.0,
    )


def formatted_daily_table(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    money_columns = [
        "주가",
        "거래금액",
        "보유현금",
        "평균매수가",
        "평가금액",
        "총자산",
        "실현손익",
        "미실현손익",
        "누적손익",
    ]

    for column in money_columns:
        if column in result.columns:
            result[column] = result[column].map(
                lambda value: comma(value, 0)
            )

    if "보유수량" in result.columns:
        result["보유수량"] = result[
            "보유수량"
        ].map(
            lambda value: comma(value)
        )

    if "누적수익률(%)" in result.columns:
        result["누적수익률(%)"] = result[
            "누적수익률(%)"
        ].map(
            lambda value: f"{comma(value)}%"
        )

    return result


def formatted_trade_table(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    for column in [
        "체결주가",
        "거래금액",
        "실현손익",
    ]:
        if column in result.columns:
            result[column] = result[column].map(
                lambda value: comma(value, 0)
            )

    if "거래수량" in result.columns:
        result["거래수량"] = result[
            "거래수량"
        ].map(
            lambda value: comma(value)
        )

    return result


def value_size_class(value: str) -> str:
    length = len(value)

    if length <= 7:
        return "metric-value-large"

    if length <= 12:
        return "metric-value-medium"

    return "metric-value-small"


def show_metric_grid(
    metrics: list[tuple[str, str]],
) -> None:
    cards = []

    for label, value in metrics:
        safe_label = html.escape(str(label))
        safe_value = html.escape(str(value))
        size_class = value_size_class(str(value))

        cards.append(
            (
                '<div class="metric-card">'
                f'<div class="metric-label">{safe_label}</div>'
                f'<div class="metric-value {size_class}">'
                f'{safe_value}'
                '</div>'
                '</div>'
            )
        )

    grid_html = (
        '<div class="metric-grid">'
        + "".join(cards)
        + "</div>"
    )

    st.markdown(
        grid_html,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="가상 주식시장 시뮬레이터",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
<style>
.block-container {
    max-width: 1280px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

h1 {
    font-size: clamp(1.9rem, 5vw, 3.2rem) !important;
    line-height: 1.15 !important;
}

h2,
h3 {
    line-height: 1.25 !important;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.8rem;
    margin-top: 0.8rem;
    margin-bottom: 1.2rem;
}

.metric-card {
    min-width: 0;
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-radius: 0.8rem;
    padding: 0.9rem;
    background: rgba(128, 128, 128, 0.06);
}

.metric-label {
    font-size: 0.82rem;
    font-weight: 600;
    opacity: 0.78;
    margin-bottom: 0.35rem;
    white-space: nowrap;
}

.metric-value {
    font-weight: 650;
    line-height: 1.15;
    white-space: nowrap;
    letter-spacing: -0.045em;
    font-variant-numeric: tabular-nums;
}

.metric-value-large {
    font-size: clamp(1.45rem, 2.4vw, 2.1rem);
}

.metric-value-medium {
    font-size: clamp(1.15rem, 1.9vw, 1.65rem);
}

.metric-value-small {
    font-size: clamp(0.9rem, 1.5vw, 1.25rem);
}

div[data-testid="stButton"] button {
    min-height: 3rem;
    border-radius: 0.7rem;
}

div[data-testid="stTextInput"] input {
    min-height: 2.8rem;
}

div[data-testid="stExpander"] {
    border-radius: 0.8rem;
}

@media (max-width: 1000px) {
    .metric-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 700px) {
    .block-container {
        padding-left: 0.85rem;
        padding-right: 0.85rem;
        padding-top: 0.8rem;
    }

    .metric-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem;
    }

    .metric-card {
        padding: 0.7rem;
        border-radius: 0.65rem;
    }

    .metric-label {
        font-size: 0.72rem;
    }

    .metric-value-large {
        font-size: 1.35rem;
    }

    .metric-value-medium {
        font-size: 1.05rem;
    }

    .metric-value-small {
        font-size: 0.82rem;
    }

    div[data-testid="stButton"] button {
        min-height: 3.2rem;
        font-size: 0.9rem;
    }

    div[data-testid="stDataFrame"] {
        overflow-x: auto;
    }
}

@media (max-width: 390px) {
    .metric-grid {
        grid-template-columns: 1fr;
    }

    .metric-value-large {
        font-size: 1.55rem;
    }

    .metric-value-medium {
        font-size: 1.3rem;
    }

    .metric-value-small {
        font-size: 1.05rem;
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
    "계산값은 소수점 셋째 자리에서 반올림하며 수수료는 0원입니다."
)


with st.expander(
    "⚙️ 초기 설정 및 시장 규칙",
    expanded=False,
):
    settings_col1, settings_col2 = st.columns(2)

    with settings_col1:
        initial_capital_text = st.text_input(
            "초기 자본금",
            key="initial_capital_text",
            help="예: 100,000,000",
        )

    with settings_col2:
        initial_price_text = st.text_input(
            "초기 주가",
            key="initial_price_text",
            help="예: 200,000",
        )

    if st.button(
        "입력값으로 시뮬레이션 초기화",
        use_container_width=True,
        type="primary",
    ):
        try:
            capital = parse_number(
                initial_capital_text,
                "초기 자본금",
            )

            price = parse_number(
                initial_price_text,
                "초기 주가",
            )

            if price <= 0:
                raise ValueError(
                    "초기 주가는 0보다 커야 합니다."
                )

            initialize_state(
                initial_capital=capital,
                initial_price=price,
            )

            st.success(
                "시뮬레이션을 초기화했습니다."
            )

            st.rerun()

        except ValueError as error:
            st.error(str(error))

    st.markdown(
        """
- 상승 확률: **50%**
- 상승률: **+10%**
- 하락 확률: **50%**
- 하락률: **-9.0909%**
- 수수료: **0원**
- 보유 현금: **음수 허용**
- 초과 매도: **자동 전량 매도**
"""
    )


values = portfolio_values()


show_metric_grid(
    [
        (
            "현재 일차",
            f"{st.session_state.day:,}일",
        ),
        (
            "현재 주가",
            format_won(
                st.session_state.price
            ),
        ),
        (
            "오늘 등락",
            st.session_state.last_move,
        ),
        (
            "보유 현금",
            format_won(
                st.session_state.cash
            ),
        ),
        (
            "보유수량",
            f"{comma(st.session_state.shares)}주",
        ),
        (
            "평균 매수가",
            format_won(
                st.session_state.avg_price
            ),
        ),
        (
            "주식 평가금액",
            format_won(
                values["market_value"]
            ),
        ),
        (
            "총자산",
            format_won(
                values["total_assets"]
            ),
        ),
        (
            "누적 수익금",
            format_won(
                values["total_pnl"]
            ),
        ),
        (
            "누적 수익률",
            f"{comma(values['total_return'])}%",
        ),
        (
            "실현손익",
            format_won(
                st.session_state.realized_pnl
            ),
        ),
        (
            "미실현손익",
            format_won(
                values["unrealized_pnl"]
            ),
        ),
    ]
)


if st.session_state.cash < 0:
    st.warning(
        "현재 보유 현금이 음수입니다. "
        "이는 사실상 차입 또는 레버리지 사용과 같은 효과입니다."
    )


st.subheader("📅 날짜 진행")

if st.button(
    "🎲 랜덤으로 내일 진행",
    use_container_width=True,
    type="primary",
):
    next_day("random")
    st.rerun()


direction_col1, direction_col2 = st.columns(2)

with direction_col1:
    if st.button(
        "📈 상승으로 진행",
        use_container_width=True,
    ):
        next_day("up")
        st.rerun()

with direction_col2:
    if st.button(
        "📉 하락으로 진행",
        use_container_width=True,
    ):
        next_day("down")
        st.rerun()


st.subheader("💰 거래")

buy_tab, sell_tab = st.tabs(
    [
        "매수",
        "매도",
    ]
)


with buy_tab:
    buy_amount_text = st.text_input(
        "매수금액",
        key="buy_amount_text",
        help="예: 20,000,000",
    )

    if st.button(
        "매수 실행",
        use_container_width=True,
        type="primary",
        key="buy_button",
    ):
        try:
            buy_amount = parse_number(
                buy_amount_text,
                "매수금액",
            )

            success, message = buy(
                buy_amount
            )

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        except ValueError as error:
            st.error(str(error))


with sell_tab:
    sell_amount_text = st.text_input(
        "매도금액",
        key="sell_amount_text",
        help="보유 평가액보다 크게 입력하면 전량 매도됩니다.",
    )

    if st.button(
        "매도 실행",
        use_container_width=True,
        type="primary",
        key="sell_button",
    ):
        try:
            sell_amount = parse_number(
                sell_amount_text,
                "매도금액",
            )

            success, message = sell(
                sell_amount
            )

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        except ValueError as error:
            st.error(str(error))


history_df = pd.DataFrame(
    st.session_state.daily_history
)


st.subheader("📊 차트")

price_tab, asset_tab = st.tabs(
    [
        "주가 변화",
        "자산 변화",
    ]
)


with price_tab:
    price_chart = history_df[
        [
            "일차",
            "주가",
        ]
    ].drop_duplicates(
        subset=["일차"],
        keep="last",
    )

    st.line_chart(
        price_chart.set_index("일차"),
        use_container_width=True,
    )


with asset_tab:
    asset_chart = history_df[
        [
            "일차",
            "총자산",
            "보유현금",
            "평가금액",
        ]
    ].drop_duplicates(
        subset=["일차"],
        keep="last",
    )

    st.line_chart(
        asset_chart.set_index("일차"),
        use_container_width=True,
    )


st.subheader("🧾 기록")

daily_tab, trade_tab = st.tabs(
    [
        "일별 기록",
        "거래 내역",
    ]
)


with daily_tab:
    st.dataframe(
        formatted_daily_table(
            history_df
        ),
        use_container_width=True,
        hide_index=True,
    )


with trade_tab:
    trade_df = pd.DataFrame(
        st.session_state.trade_history
    )

    if trade_df.empty:
        st.info(
            "아직 거래 내역이 없습니다."
        )
    else:
        st.dataframe(
            formatted_trade_table(
                trade_df
            ),
            use_container_width=True,
            hide_index=True,
        )
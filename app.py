from pathlib import Path
import shutil
import py_compile
import re

src = Path("/mnt/data/virtual_stock_simulator_v3/app.py")
code = src.read_text(encoding="utf-8")

# 기존 metric용 CSS 블록을 사용자 정의 카드 CSS로 교체
start_marker = '# 좁은 브라우저에서도 metric 값이 ...으로 잘리지 않고 자동 축소되도록 설정합니다.'
start = code.index(start_marker)
end = code.index('ensure_state()', start)

new_css = r'''# 값의 길이에 따라 글자 크기를 줄이는 사용자 정의 지표 카드입니다.
st.markdown(
    """
    <style>
    .custom-metric {
        min-width: 0;
        width: 100%;
        padding: 0.15rem 0 0.55rem 0;
    }

    .custom-metric-label {
        font-size: 0.88rem;
        font-weight: 600;
        margin-bottom: 0.22rem;
        white-space: nowrap;
    }

    .custom-metric-value {
        width: 100%;
        line-height: 1.12;
        white-space: nowrap;
        overflow: visible;
        text-overflow: clip;
        letter-spacing: -0.045em;
        font-variant-numeric: tabular-nums;
    }

    @media (max-width: 1000px) {
        .custom-metric-label {
            font-size: 0.78rem;
        }

        .custom-metric-value {
            letter-spacing: -0.065em;
        }
    }

    @media (max-width: 700px) {
        .custom-metric-label {
            font-size: 0.72rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def metric_font_size(value: str) -> float:
    """표시 문자열 길이에 따라 지표 글자 크기를 결정합니다."""
    length = len(value)

    if length <= 4:
        return 2.05
    if length <= 7:
        return 1.82
    if length <= 9:
        return 1.58
    if length <= 11:
        return 1.35
    if length <= 13:
        return 1.16
    if length <= 16:
        return 1.00
    return 0.88


def show_metric(container, label: str, value: str) -> None:
    """말줄임표 없이 전체 값을 표시하는 지표 카드."""
    font_size = metric_font_size(value)
    safe_label = (
        label.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    safe_value = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    container.markdown(
        f"""
        <div class="custom-metric">
            <div class="custom-metric-label">{safe_label}</div>
            <div class="custom-metric-value"
                 style="font-size:{font_size}rem;">
                {safe_value}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


'''

code = code[:start] + new_css + code[end:]

old_metrics = '''top1 = st.columns(5)
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
'''

new_metrics = '''top1 = st.columns(5)
show_metric(top1[0], "현재 일차", f"{st.session_state.day:,}일")
show_metric(top1[1], "현재 주가", format_won(st.session_state.price))
show_metric(top1[2], "오늘 등락", st.session_state.last_move)
show_metric(top1[3], "보유 현금", format_won(st.session_state.cash))
show_metric(top1[4], "보유수량", f"{comma(st.session_state.shares)}주")

top2 = st.columns(5)
show_metric(top2[0], "평균 매수가", format_won(st.session_state.avg_price))
show_metric(top2[1], "주식 평가금액", format_won(values["market_value"]))
show_metric(top2[2], "총자산", format_won(values["total_assets"]))
show_metric(top2[3], "누적 수익금", format_won(values["total_pnl"]))
show_metric(top2[4], "누적 수익률", f"{comma(values['total_return'])}%")

top3 = st.columns(2)
show_metric(
    top3[0],
    "실현손익",
    format_won(st.session_state.realized_pnl),
)
show_metric(
    top3[1],
    "미실현손익",
    format_won(values["unrealized_pnl"]),
)
'''

if old_metrics not in code:
    raise RuntimeError("기존 metric 코드 블록을 찾지 못했습니다.")
code = code.replace(old_metrics, new_metrics)

base = Path("/mnt/data/virtual_stock_simulator_v4")
base.mkdir(exist_ok=True)

(base / "app.py").write_text(code, encoding="utf-8")
(base / "requirements.txt").write_text(
    "streamlit>=1.40\npandas>=2.0\n",
    encoding="utf-8",
)
(base / "README.md").write_text(
    """# 가상 주식시장 시뮬레이터 v4

- Streamlit 기본 metric을 사용자 정의 카드로 교체
- 표시 문자열 길이에 따라 글자 크기 자동 조절
- 좁은 창에서도 말줄임표(...) 없이 전체 숫자 표시
""",
    encoding="utf-8",
)
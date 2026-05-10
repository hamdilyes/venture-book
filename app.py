import calendar
import datetime as dt
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "fundraises.csv"

ROUND_ORDER = [
    "pre-seed",
    "seed",
    "series-a",
    "series-b",
    "series-c",
    "series-d",
    "series-e",
    "growth",
]


def format_eur(amount: int) -> str:
    if amount >= 1_000_000:
        n = amount / 1_000_000
        s = f"{n:.2f}".rstrip("0").rstrip(".")
        return f"{s}M"
    if amount >= 1_000:
        n = amount / 1_000
        s = f"{n:.2f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(amount)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, dtype=str).fillna("")
    df["amount_eur"] = df["amount_eur"].astype(int)
    return df


CARD_STYLES = """
<style>
.fr-card {
    border: 1px solid rgba(128,128,128,0.28);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: rgba(128,128,128,0.10);
    text-align: center;
}
.fr-card .fr-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: inherit;
    line-height: 1.25;
}
.fr-card .fr-amt {
    color: #4f9eff;
    font-size: 0.85rem;
    margin-top: 2px;
}
.fr-month-label {
    text-align: center;
    color: rgba(160,160,160,0.85);
    font-size: 0.8rem;
    margin: 6px 0 10px;
}
</style>
"""


def card_html(company: str, amount: int) -> str:
    return (
        "<div class='fr-card'>"
        f"<div class='fr-name'>{company}</div>"
        f"<div class='fr-amt'>{format_eur(amount)}</div>"
        "</div>"
    )


def date_to_window(date_str: str) -> tuple[int, int]:
    year_s, month_s = date_str.split("-")
    half = 1 if int(month_s) <= 6 else 2
    return (int(year_s), half)


def window_months(window: tuple[int, int]) -> list[str]:
    year, half = window
    rng = range(1, 7) if half == 1 else range(7, 13)
    return [f"{year}-{m:02d}" for m in rng]


def window_label(window: tuple[int, int]) -> str:
    year, _ = window
    return str(year)


def step_window(window: tuple[int, int], delta: int) -> tuple[int, int]:
    year, half = window
    idx = year * 2 + (half - 1) + delta
    return (idx // 2, (idx % 2) + 1)


def round_sort_key(r: str) -> int:
    return ROUND_ORDER.index(r) if r in ROUND_ORDER else 99


def collect_all_funds(df: pd.DataFrame) -> list[str]:
    all_funds: set[str] = set()
    for funds_str in df["funds"]:
        if not funds_str:
            continue
        for f in funds_str.split(";"):
            f = f.strip()
            if f:
                all_funds.add(f)
    return sorted(all_funds)


def fund_participates(funds_str: str, fund: str) -> bool:
    if not funds_str:
        return False
    return fund in [f.strip() for f in funds_str.split(";")]


def render_nav(window: tuple[int, int], earliest: tuple[int, int], latest: tuple[int, int]) -> None:
    left, label, right = st.columns([1, 6, 1])
    with left:
        if st.button("←", use_container_width=True, disabled=(window <= earliest), key="nav_left"):
            st.session_state.window = step_window(window, -1)
            st.rerun()
    with label:
        st.markdown(
            f"<h3 style='text-align:center;margin:0;line-height:2.2rem'>{window_label(window)}</h3>",
            unsafe_allow_html=True,
        )
    with right:
        if st.button("→", use_container_width=True, disabled=(window >= latest), key="nav_right"):
            st.session_state.window = step_window(window, 1)
            st.rerun()


def render_month_columns(df: pd.DataFrame, window: tuple[int, int]) -> None:
    months = window_months(window)
    cols = st.columns(6)
    for col, month in zip(cols, months):
        with col:
            month_name = calendar.month_name[int(month.split("-")[1])]
            st.markdown(
                f"<div class='fr-month-label'>{month_name}</div>",
                unsafe_allow_html=True,
            )
            sub = df[df["date"] == month].sort_values("amount_eur", ascending=False)
            for _, row in sub.iterrows():
                st.markdown(
                    card_html(row["company"], int(row["amount_eur"])),
                    unsafe_allow_html=True,
                )


def render_timeline_tab(df: pd.DataFrame) -> None:
    rounds_present = [r for r in ROUND_ORDER if r in set(df["round"])]
    extras = sorted(set(df["round"]) - set(ROUND_ORDER))
    rounds_present.extend(extras)

    if not rounds_present:
        st.info("No fundraises in data/fundraises.csv yet.")
        return

    selected = st.radio(
        "Round",
        rounds_present,
        horizontal=True,
        format_func=lambda r: r.replace("-", " ").title(),
        key="timeline_round",
    )

    filtered = df[df["round"] == selected]
    if filtered.empty:
        st.info(f"No {selected} fundraises yet.")
        return

    windows_in_data = sorted({date_to_window(d) for d in filtered["date"]})
    earliest, latest = windows_in_data[0], windows_in_data[-1]

    today = dt.date.today()
    current_window = (today.year, 1 if today.month <= 6 else 2)
    default_window = min(max(current_window, earliest), latest)

    last_round = st.session_state.get("timeline_last_round")
    if (
        last_round != selected
        or "window" not in st.session_state
        or not (earliest <= st.session_state.window <= latest)
    ):
        st.session_state.window = default_window
    st.session_state.timeline_last_round = selected

    render_nav(st.session_state.window, earliest, latest)
    render_month_columns(filtered, st.session_state.window)


def render_evolutions_tab(df: pd.DataFrame) -> None:
    counts = df.groupby("company").size()
    multi_companies = counts[counts >= 2].index.tolist()
    multi = df[df["company"].isin(multi_companies)].copy()

    if multi.empty:
        st.info("No company has more than one fundraise yet — add a follow-on round to populate this view.")
        return

    multi["cell"] = multi.apply(
        lambda r: f"{format_eur(int(r['amount_eur']))} · {r['date']}",
        axis=1,
    )

    pivot = multi.pivot_table(
        index="company",
        columns="round",
        values="cell",
        aggfunc="first",
    )

    rounds_present = [r for r in ROUND_ORDER if r in pivot.columns]
    extras = sorted([r for r in pivot.columns if r not in ROUND_ORDER])
    pivot = pivot[rounds_present + extras]
    pivot.columns = [r.replace("-", " ").title() for r in pivot.columns]
    pivot = pivot.fillna("—")

    pivot = pivot.reset_index().rename(columns={"company": "Company"})
    pivot = pivot.sort_values("Company").reset_index(drop=True)

    st.dataframe(pivot, use_container_width=True, hide_index=True)


def render_fund_tab(df: pd.DataFrame) -> None:
    fund_list = collect_all_funds(df)
    if not fund_list:
        st.info("No funds found in the CSV.")
        return

    rows = []
    for fund in fund_list:
        mask = df["funds"].apply(lambda s, f=fund: fund_participates(s, f))
        deals = df[mask]
        if deals.empty:
            continue
        amounts = deals["amount_eur"]
        rows.append(
            {
                "Fund": fund,
                "Deals": len(deals),
                "Min (€M)": round(amounts.min() / 1_000_000, 2),
                "Median (€M)": round(amounts.median() / 1_000_000, 2),
                "Max (€M)": round(amounts.max() / 1_000_000, 2),
            }
        )

    table = (
        pd.DataFrame(rows)
        .sort_values(["Deals", "Median (€M)"], ascending=[False, False])
        .reset_index(drop=True)
    )

    st.caption(
        "Stats are based on the total round size — the CSV doesn't track "
        "per-fund check sizes — so this measures the rounds each fund participated in."
    )

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fund": st.column_config.TextColumn(width="medium"),
            "Deals": st.column_config.NumberColumn(width="small"),
            "Min (€M)": st.column_config.NumberColumn(format="%.2f"),
            "Median (€M)": st.column_config.NumberColumn(format="%.2f"),
            "Max (€M)": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def render_orderbook_tab(df: pd.DataFrame) -> None:
    rounds_present = [r for r in ROUND_ORDER if r in set(df["round"])]
    extras = sorted(set(df["round"]) - set(ROUND_ORDER))
    rounds_present.extend(extras)

    if not rounds_present:
        st.info("No fundraises yet.")
        return

    today = dt.date.today()

    def months_ago(date_str: str) -> int:
        y, m = date_str.split("-")
        d = dt.date(int(y), int(m), 1)
        return (today.year - d.year) * 12 + (today.month - d.month)

    plot = df.copy()
    plot["months_ago"] = plot["date"].apply(months_ago)
    plot["amount_label"] = plot["amount_eur"].apply(format_eur)
    plot["round_label"] = plot["round"].str.replace("-", " ").str.title()

    round_labels = [r.replace("-", " ").title() for r in rounds_present]

    early = plot[plot["round"].isin(["pre-seed", "seed"])]
    early = early[early["amount_eur"] <= 50_000_000]
    if not early.empty:
        early_round_labels = [
            r.replace("-", " ").title()
            for r in ("pre-seed", "seed")
            if r in set(early["round"])
        ]
        early_box = (
            alt.Chart(early)
            .mark_boxplot(size=80, opacity=0.35, color="#9aa0a6", outliers=False)
            .encode(
                x=alt.X(
                    "round_label:N",
                    sort=early_round_labels,
                    title="Round",
                    axis=alt.Axis(labelAngle=0),
                ),
                y=alt.Y(
                    "amount_eur:Q",
                    scale=alt.Scale(domain=[0, 50_000_000]),
                    title="Amount (€)",
                    axis=alt.Axis(format="~s"),
                ),
            )
        )
        early_dots = (
            alt.Chart(early)
            .transform_calculate(jitter="random()")
            .mark_circle(size=110, opacity=0.75, color="#4f9eff", stroke="white", strokeWidth=0.5)
            .encode(
                x=alt.X(
                    "round_label:N",
                    sort=early_round_labels,
                    title="Round",
                    axis=alt.Axis(labelAngle=0),
                ),
                xOffset=alt.XOffset("jitter:Q"),
                y=alt.Y("amount_eur:Q", scale=alt.Scale(domain=[0, 50_000_000])),
                tooltip=[
                    alt.Tooltip("company:N", title="Company"),
                    alt.Tooltip("amount_label:N", title="Amount"),
                    alt.Tooltip("round_label:N", title="Round"),
                    alt.Tooltip("date:N", title="Date"),
                    alt.Tooltip("funds:N", title="Funds"),
                ],
            )
        )
        early_chart = (
            (early_box + early_dots).properties(height=420).configure_view(strokeWidth=0)
        )
        st.caption("Pre-seed and seed only — linear scale, capped at €50M.")
        st.altair_chart(early_chart, use_container_width=True)

    box = (
        alt.Chart(plot)
        .mark_boxplot(size=44, opacity=0.35, color="#9aa0a6", outliers=False)
        .encode(
            x=alt.X("round_label:N", sort=round_labels, title="Round", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "amount_eur:Q",
                scale=alt.Scale(type="log"),
                title="Amount (€)",
                axis=alt.Axis(format="~s"),
            ),
        )
    )

    dots = (
        alt.Chart(plot)
        .transform_calculate(jitter="random()")
        .mark_circle(size=110, opacity=0.85, stroke="white", strokeWidth=0.5)
        .encode(
            x=alt.X("round_label:N", sort=round_labels, title="Round", axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset("jitter:Q"),
            y=alt.Y("amount_eur:Q", scale=alt.Scale(type="log"), title="Amount (€)"),
            color=alt.Color(
                "months_ago:Q",
                scale=alt.Scale(scheme="viridis", reverse=True, domain=[0, 24], clamp=True),
                legend=alt.Legend(title="Months ago"),
            ),
            tooltip=[
                alt.Tooltip("company:N", title="Company"),
                alt.Tooltip("amount_label:N", title="Amount"),
                alt.Tooltip("round_label:N", title="Round"),
                alt.Tooltip("date:N", title="Date"),
                alt.Tooltip("funds:N", title="Funds"),
            ],
        )
    )

    chart = (box + dots).properties(height=560).configure_view(strokeWidth=0)

    st.caption(
        "Each dot is one round. Box = P25–median–P75 per stage. "
        "Color tracks recency (brighter = more recent). Y-axis is log scale."
    )
    st.altair_chart(chart, use_container_width=True)

    stage_stats = (
        plot.groupby("round")["amount_eur"]
        .agg(["count", "min", "median", "max"])
        .reindex(rounds_present)
        .dropna()
    )
    stage_stats = stage_stats.reset_index().rename(columns={"round": "Round"})
    stage_stats["Round"] = stage_stats["Round"].str.replace("-", " ").str.title()
    stage_stats["count"] = stage_stats["count"].astype(int)
    for col in ("min", "median", "max"):
        stage_stats[col] = stage_stats[col].apply(lambda v: format_eur(int(v)))
    stage_stats = stage_stats.rename(
        columns={"count": "Deals", "min": "Min", "median": "Median", "max": "Max"}
    )
    st.dataframe(stage_stats, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="venture-book", layout="wide")
    st.markdown(CARD_STYLES, unsafe_allow_html=True)
    st.title("venture-book")
    st.caption("An orderbook of venture fundraises.")

    df = load_data()
    if df.empty:
        st.info("No fundraises in data/fundraises.csv yet.")
        return

    tab_orderbook, tab_timeline, tab_evolutions, tab_fund = st.tabs(
        ["Order book", "Timeline", "Evolutions", "Fund analysis"]
    )

    with tab_orderbook:
        render_orderbook_tab(df)
    with tab_timeline:
        render_timeline_tab(df)
    with tab_evolutions:
        render_evolutions_tab(df)
    with tab_fund:
        render_fund_tab(df)


if __name__ == "__main__":
    main()

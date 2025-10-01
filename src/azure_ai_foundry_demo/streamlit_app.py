from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from azure_ai_foundry_demo.agents.orchestrator import StockAgentOrchestrator
from azure_ai_foundry_demo.workflow import AgentResearchReport, StockResearchWorkflow


@st.cache_resource(show_spinner=False)
def get_services() -> dict[str, Any]:
    orchestrator = StockAgentOrchestrator()
    workflow = StockResearchWorkflow(orchestrator=orchestrator)
    return {"orchestrator": orchestrator, "workflow": workflow}


def _init_session_state() -> None:
    if "report" not in st.session_state:
        st.session_state.report = None
    if "summary" not in st.session_state:
        st.session_state.summary = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "selected_ticker" not in st.session_state:
        st.session_state.selected_ticker = "MSFT"

def _render_report(report: AgentResearchReport) -> None:
    st.subheader("Research Summary")
    st.markdown(report.formatted_summary().replace("\n", "  \n"))
    price = report.quote.get("price")
    currency = report.quote.get("currency", "")
    change = report.quote.get("change")
    change_pct = report.quote.get("change_percent")
    cols = st.columns(3)
    cols[0].metric("Price", f"{price} {currency}" if price is not None else "-")
    cols[1].metric("Change", f"{change:.2f}" if change is not None else "-")
    cols[2].metric("Change %", f"{change_pct:.2f}%" if change_pct is not None else "-")
    if report.metrics:
        metrics = report.metrics
        st.markdown("### Multi-day trend")
        trend = st.columns(3)
        period = metrics.get("period_days") or len(report.historical)
        change_value = metrics.get("absolute_change")
        change_pct_value = metrics.get("percent_change")
        if change_value is not None or change_pct_value is not None:
            delta = f"{change_pct_value:.2f}%" if change_pct_value is not None else None
            value_text = f"{change_value:.2f}" if change_value is not None else "-"
            trend[0].metric(f"Change ({period}d)", value_text, delta=delta)
        avg_volume = metrics.get("average_volume")
        if avg_volume is not None:
            trend[1].metric("Avg volume", f"{avg_volume:,.0f}")
        range_parts: list[str] = []
        high = metrics.get("high")
        low = metrics.get("low")
        if high is not None:
            range_parts.append(f"High {high:.2f}")
        if low is not None:
            range_parts.append(f"Low {low:.2f}")
        if range_parts:
            trend[2].metric("Range", " / ".join(range_parts))
    if report.historical:
        st.markdown("### Recent daily performance")
        ordered_history = sorted(
            report.historical,
            key=lambda entry: entry.get("date", ""),
            reverse=True,
        )
        st.dataframe(ordered_history, use_container_width=True)

        chart_rows = [
            {
                "date": entry.get("date"),
                "open": entry.get("open"),
                "close": entry.get("close"),
            }
            for entry in report.historical
            if entry.get("date") and (
                entry.get("open") is not None or entry.get("close") is not None
            )
        ]
        if chart_rows:
            sorted_rows = sorted(chart_rows, key=lambda entry: entry["date"])
            price_frame = pd.DataFrame(sorted_rows)
            price_frame["date"] = pd.to_datetime(price_frame["date"])  # type: ignore[assignment]
            melted = price_frame.melt(
                id_vars="date",
                value_vars=["open", "close"],
                var_name="Series",
                value_name="Price",
            )
            y_values = melted["Price"].dropna()
            domain = None
            if not y_values.empty:
                y_min = float(y_values.min())
                y_max = float(y_values.max())
                padding = (y_max - y_min) * 0.05
                if padding == 0:
                    padding = max(abs(y_min) * 0.01, 1.0)
                domain = [y_min - padding, y_max + padding]
            price_chart = (
                alt.Chart(melted)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y(
                        "Price:Q",
                        title="Price",
                        scale=alt.Scale(domain=domain) if domain else alt.Scale(),
                    ),
                    color=alt.Color("Series:N", title=""),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date"),
                        alt.Tooltip("Series:N", title="Series"),
                        alt.Tooltip("Price:Q", title="Price", format=".2f"),
                    ],
                )
                .properties(height=300)
            )
            st.altair_chart(price_chart.interactive(), use_container_width=True)

        volume_rows = [
            {"date": entry.get("date"), "volume": entry.get("volume")}
            for entry in report.historical
            if entry.get("date") and entry.get("volume") is not None
        ]
        if volume_rows:
            sorted_volume = sorted(volume_rows, key=lambda entry: entry["date"])
            volume_frame = pd.DataFrame(sorted_volume)
            volume_frame["date"] = pd.to_datetime(volume_frame["date"])  # type: ignore[assignment]
            volume_chart = (
                alt.Chart(volume_frame)
                .mark_bar()
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("volume:Q", title="Volume"),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date"),
                        alt.Tooltip("volume:Q", title="Volume", format=".0f"),
                    ],
                )
                .properties(height=240)
            )
            st.altair_chart(volume_chart.interactive(), use_container_width=True)
    if report.news:
        st.markdown("### Latest Headlines")
        for item in report.news[:5]:
            title = item.get("title", "Untitled")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            if link:
                st.markdown(f"- [{title}]({link})")
            else:
                st.markdown(f"- {title}")
            if snippet:
                st.caption(snippet)
    else:
        st.info("No headlines available yet.")


def _render_chat_interface(orchestrator: StockAgentOrchestrator) -> None:
    report: AgentResearchReport | None = st.session_state.report
    if report is None:
        return
    st.divider()
    st.subheader("Chat with the research agent")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    prompt = st.chat_input("Ask a follow-up question")
    if not prompt:
        return
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.spinner("Thinking..."):
        try:
            follow_up = orchestrator.follow_up(
                ticker=report.ticker,
                user_message=prompt,
                summary=st.session_state.summary,
                conversation_history=st.session_state.chat_history[:-1],
            )
        except Exception as exc:  # pragma: no cover
            st.session_state.chat_history.pop()
            st.error(f"Chat request failed: {exc}")
            return
    reply = follow_up.get("reply", "") or "I'm not sure how to respond."
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    if follow_up.get("quote"):
        report.quote = follow_up["quote"]
    if follow_up.get("news"):
        report.news = follow_up["news"]
    if follow_up.get("organic_results"):
        report.organic_results = follow_up["organic_results"]
    if follow_up.get("historical"):
        report.historical = follow_up["historical"]
    if follow_up.get("metrics"):
        report.metrics = follow_up["metrics"]
    st.session_state.report = report
    st.session_state.summary = report.formatted_summary()
    with st.chat_message("assistant"):
        st.markdown(reply)


def main() -> None:
    st.set_page_config(page_title="Stock Research Copilot", page_icon="📈", layout="wide")
    services = get_services()
    orchestrator: StockAgentOrchestrator = services["orchestrator"]
    workflow: StockResearchWorkflow = services["workflow"]
    _init_session_state()
    with st.sidebar:
        st.header("Ticker selection")
        default_tickers = ["MSFT", "AAPL", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
        selected_default = st.selectbox(
            "Choose a ticker",
            default_tickers,
            index=default_tickers.index(st.session_state.selected_ticker)
            if st.session_state.selected_ticker in default_tickers
            else 0,
        )
        custom_ticker = st.text_input(
            "Or type a custom ticker",
            value=(
                ""
                if st.session_state.selected_ticker in default_tickers
                else st.session_state.selected_ticker
            ),
        )
        run_requested = st.button("Run research", use_container_width=True)
    if run_requested:
        ticker = (custom_ticker or selected_default).strip().upper()
        if not ticker:
            st.error("Please select or enter a ticker symbol.")
        else:
            st.session_state.selected_ticker = ticker
            with st.spinner(f"Researching {ticker}..."):
                try:
                    report = workflow.run(ticker)
                except Exception as exc:  # pragma: no cover
                    st.error(f"Workflow run failed: {exc}")
                else:
                    st.session_state.report = report
                    st.session_state.summary = report.formatted_summary()
                    st.session_state.chat_history = []
                    st.success(f"Research complete for {ticker}")
    if st.session_state.report:
        _render_report(st.session_state.report)
        _render_chat_interface(orchestrator)
    else:
        st.info("Select a ticker and start the workflow to see insights.")


if __name__ == "__main__":
    main()

"""
Multi-Agent Research Dashboard — Streamlit UI
"""
import time
import warnings
from pathlib import Path
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*ssl")

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agents import AgentState, build_graph

# Load .env from the same directory as this file
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

# ──────────────────────────────────────────
# Page config
# ──────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Research",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    text-align: center;
    border: 1px solid #313244;
}
.metric-label { color: #cdd6f4; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { color: #89b4fa; font-size: 2rem; font-weight: bold; }
.log-box {
    background: #181825;
    border-radius: 8px;
    padding: 1rem;
    font-family: monospace;
    font-size: 0.85rem;
    border: 1px solid #313244;
    max-height: 320px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# Header
# ──────────────────────────────────────────
st.markdown("# 🤖 Multi-Agent Research Dashboard")
st.caption("Researcher Agent → Writer Agent · Powered by GPT-4o + DuckDuckGo · Built with LangGraph")
st.divider()

# ──────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Research Settings")

    if "topic_input" not in st.session_state:
        st.session_state["topic_input"] = (
            "Current status of Solid State Battery commercialization in the automotive sector for 2026"
        )
    if "pending_example" in st.session_state:
        st.session_state["topic_input"] = st.session_state.pop("pending_example")

    topic = st.text_area(
        "Research Topic",
        key="topic_input",
        height=130,
        help="Be specific. Include a year for best results.",
    )

    st.divider()
    run_btn = st.button("🚀 Run Pipeline", use_container_width=True, type="primary")

    st.divider()
    st.markdown("#### 💡 Example Topics")
    examples = [
        "NVIDIA vs AMD AI chip market share in 2026",
        "GLP-1 weight loss drugs competition in 2026",
        "India unicorn startup IPO pipeline 2026",
        "Quantum computing commercialization status 2026",
        "Green hydrogen production costs and viability 2026",
        "Humanoid robotics — Figure, Tesla Optimus, Boston Dynamics",
        "BRICS expansion impact on US dollar dominance",
        "Generative AI adoption in enterprise software 2026",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state["pending_example"] = ex
            st.session_state["auto_run"] = True
            st.rerun()

    st.divider()
    st.markdown("#### 🔄 Pipeline")
    st.markdown("""
1. 🔍 **Researcher Agent**
   - Generates 3 search queries
   - Fetches top web results
2. ✍️ **Writer Agent**
   - Synthesizes executive report
   - Extracts chart data (outlook, themes)
""")

# ──────────────────────────────────────────
# Placeholder layout
# ──────────────────────────────────────────
status_placeholder = st.empty()
metrics_placeholder = st.empty()
charts_placeholder = st.empty()
st.divider()
log_col, report_col = st.columns([1, 2])

with log_col:
    st.subheader("📋 Activity Log")
    log_placeholder = st.empty()
    log_placeholder.markdown("_Waiting to start..._")

with report_col:
    st.subheader("📄 Executive Report")
    report_placeholder = st.empty()
    report_placeholder.info("Run the pipeline to generate a report.")

# ──────────────────────────────────────────
# LLM — module-level so cache_resource works
# ──────────────────────────────────────────
@st.cache_resource
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0.2)


# ──────────────────────────────────────────
# Pipeline execution
# ──────────────────────────────────────────
run_requested = run_btn or st.session_state.pop("auto_run", False)

if run_requested and topic.strip():

    log: list[str] = []
    queries_run: list[str] = []
    sources_found: dict[str, int] = {}
    start_time = time.time()

    def refresh_log() -> None:
        log_placeholder.markdown(
            "<div class='log-box'>" +
            "<br>".join(f"▸ {line}" for line in log) +
            "</div>",
            unsafe_allow_html=True,
        )

    def on_query(q: str) -> None:
        queries_run.append(q)
        log.append(f"🔎 Searching: <i>{q}</i>")
        status_placeholder.info(f"🔍 Researcher Agent — Searching: `{q}`")
        refresh_log()

    def on_status(msg: str) -> None:
        log.append(f"✍️ {msg}")
        status_placeholder.info(f"✍️ Writer Agent — {msg}")
        refresh_log()

    # Kick off
    log.append(f"🚀 Topic: <b>{topic}</b>")
    refresh_log()

    llm = get_llm()
    graph = build_graph(llm, on_query=on_query, on_status=on_status)

    initial_state: AgentState = {
        "task": topic,
        "research_data": [],
        "sources_per_query": {},
        "report": "",
        "chart_data": {},
    }

    result = graph.invoke(initial_state)
    elapsed = round(time.time() - start_time, 1)
    total_sources = sum(result["sources_per_query"].values())

    log.append(f"⏱️ Done in <b>{elapsed}s</b>")
    refresh_log()
    status_placeholder.success("✅ Pipeline complete!")

    # ── Metrics row ──────────────────────────────
    with metrics_placeholder.container():
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔍 Queries Run", len(result["sources_per_query"]))
        m2.metric("📰 Sources Found", total_sources)
        m3.metric("⏱️ Time Taken", f"{elapsed}s")
        m4.metric("🎯 Confidence", f"{result['chart_data'].get('confidence', '—')}%")

    # ── Charts row ───────────────────────────────
    chart_data = result["chart_data"]
    with charts_placeholder.container():
        c1, c2, c3 = st.columns(3)

        # Pie chart — Outlook breakdown
        with c1:
            st.markdown("##### 🥧 Research Outlook")
            outlook = chart_data.get("outlook", {})
            if outlook:
                fig_pie = px.pie(
                    names=list(outlook.keys()),
                    values=list(outlook.values()),
                    color=list(outlook.keys()),
                    color_discrete_map={
                        "Positive": "#a6e3a1",
                        "Challenges": "#f38ba8",
                        "Neutral": "#89b4fa",
                    },
                    hole=0.4,
                )
                fig_pie.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    showlegend=True,
                    height=260,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        # Bar chart — Sources per query
        with c2:
            st.markdown("##### 📊 Sources per Query")
            spq = result["sources_per_query"]
            if spq:
                short_labels = [q[:35] + "…" if len(q) > 35 else q for q in spq.keys()]
                fig_bar = px.bar(
                    x=list(spq.values()),
                    y=short_labels,
                    orientation="h",
                    color=list(spq.values()),
                    color_continuous_scale="Blues",
                    labels={"x": "Sources", "y": ""},
                )
                fig_bar.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=260,
                    showlegend=False,
                    coloraxis_showscale=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(tickfont=dict(size=10)),
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        # Gauge — Confidence score
        with c3:
            st.markdown("##### 🎯 Research Confidence")
            confidence = chart_data.get("confidence", 70)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=confidence,
                number={"suffix": "%"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#89b4fa"},
                    "steps": [
                        {"range": [0, 40], "color": "#f38ba8"},
                        {"range": [40, 70], "color": "#fab387"},
                        {"range": [70, 100], "color": "#a6e3a1"},
                    ],
                    "threshold": {
                        "line": {"color": "white", "width": 3},
                        "thickness": 0.75,
                        "value": confidence,
                    },
                },
            ))
            fig_gauge.update_layout(
                height=260,
                margin=dict(t=20, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)",
                font={"color": "white"},
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        # Key themes as badges
        themes = chart_data.get("themes", [])
        if themes:
            st.markdown("##### 🏷️ Key Themes Identified")
            theme_html = " &nbsp; ".join(
                f"<span style='background:#313244;padding:4px 12px;border-radius:20px;"
                f"font-size:0.85rem;color:#cdd6f4'>{t}</span>"
                for t in themes
            )
            st.markdown(theme_html, unsafe_allow_html=True)

    # ── Full report ──────────────────────────────
    report_placeholder.markdown(result["report"])

elif run_requested:
    st.warning("⚠️ Please enter a research topic before running.")

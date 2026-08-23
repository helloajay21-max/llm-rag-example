"""
Core multi-agent logic: Researcher + Writer agents orchestrated via LangGraph.
"""
import json
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*ssl")

from typing import Any, TypedDict
import truststore
# noinspection PyUnresolvedReferences
from duckduckgo_search import DDGS
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

truststore.inject_into_ssl()


# ──────────────────────────────────────────
# State schema
# ──────────────────────────────────────────
class AgentState(TypedDict):
    task: str
    research_data: list[str]
    sources_per_query: dict[str, int]
    report: str
    chart_data: dict[str, Any]


# ──────────────────────────────────────────
# Web search tool
# ──────────────────────────────────────────
def web_search_tool(query: str) -> tuple[str, int]:
    """Returns (formatted results string, number of results found)."""
    try:
        with warnings.catch_warnings(record=True) as _:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No relevant search results found.", 0
        formatted = []
        for r in results:
            formatted.append(
                f"Title: {r['title']}\nSource: {r['href']}\nSnippet: {r['body']}\n---"
            )
        return "\n".join(formatted), len(results)
    except Exception as e:
        return f"Search failed: {str(e)}", 0


# ──────────────────────────────────────────
# Agent nodes
# ──────────────────────────────────────────
def researcher_node(state: AgentState, llm: ChatOpenAI, on_query: Any = None) -> dict[str, Any]:
    """Agent 1: Formulates queries and searches the web for facts."""
    topic = state["task"]

    search_prompt = (
        f"Given the request '{topic}', output the 3 best search queries to find hard facts. "
        "Separate them with a newline. Output nothing else."
    )
    queries = str(llm.invoke([HumanMessage(content=search_prompt)]).content).split("\n")
    queries = [q.strip() for q in queries if q.strip()]

    collected_facts: list[str] = []
    sources_per_query: dict[str, int] = {}

    for q in queries:
        if on_query:
            on_query(q)
        result_text, count = web_search_tool(q)
        collected_facts.append(result_text)
        sources_per_query[q] = count

    return {"research_data": collected_facts, "sources_per_query": sources_per_query}


def writer_node(state: AgentState, llm: ChatOpenAI, on_status: Any = None) -> dict[str, Any]:
    """Agent 2: Synthesizes research into a structured report + chart metadata."""
    if on_status:
        on_status("Synthesizing executive report...")

    topic = state["task"]
    raw_data = "\n".join(state["research_data"])

    # Generate the written report
    system_prompt = (
        "You are an Elite Enterprise Research Analyst. Your job is to take raw research data "
        "and organize it into an executive-level summary. You must cite specific sources and links "
        "provided in the research. Use clear Markdown sections, bullet points, and an outlook summary."
    )
    report = str(llm.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=f"User Request: {topic}\n\nRaw Research Findings:\n{raw_data}"),
    ]).content)

    # Generate structured chart metadata from the report
    chart_prompt = (
        f"Based on this research report about '{topic}', return ONLY a valid JSON object with:\n"
        '- "outlook": object with keys "Positive", "Challenges", "Neutral" as integer percentages summing to 100\n'
        '- "themes": list of 5 key theme strings (short, 2-4 words each)\n'
        '- "confidence": integer 0-100 representing how well the research answered the question\n'
        "JSON only, no markdown, no explanation.\n\n"
        f"Report:\n{report[:3000]}"
    )
    try:
        chart_raw = str(llm.invoke([HumanMessage(content=chart_prompt)]).content)
        chart_data = json.loads(chart_raw)
    except Exception:
        chart_data = {
            "outlook": {"Positive": 40, "Challenges": 35, "Neutral": 25},
            "themes": ["Market Growth", "Technical Barriers", "Investment", "Timeline", "Competition"],
            "confidence": 65,
        }

    return {"report": report, "chart_data": chart_data}


# ──────────────────────────────────────────
# Graph builder
# ──────────────────────────────────────────
def build_graph(llm: ChatOpenAI, on_query: Any = None, on_status: Any = None):
    """Builds and compiles the LangGraph workflow."""

    def _researcher(state: AgentState) -> dict[str, Any]:
        return researcher_node(state, llm, on_query)

    def _writer(state: AgentState) -> dict[str, Any]:
        return writer_node(state, llm, on_status)

    workflow = StateGraph(AgentState)  # type: ignore[arg-type]
    workflow.add_node("researcher", _researcher)  # type: ignore[arg-type]
    workflow.add_node("writer", _writer)  # type: ignore[arg-type]
    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)
    return workflow.compile()

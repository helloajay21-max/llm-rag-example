# 🤖 Multi-Agent Research Dashboard

An AI-powered research pipeline that uses **two autonomous agents** (Researcher + Writer) orchestrated via **LangGraph**, with a **Streamlit dashboard** for live results and visualizations.

---

## 🏗️ Architecture

```
User Topic
    │
    ▼
┌─────────────────────┐
│  Researcher Agent   │  → Generates 3 search queries → Fetches web results (DuckDuckGo)
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│   Writer Agent      │  → Synthesizes executive report → Extracts chart metadata (JSON)
└─────────────────────┘
    │
    ▼
Streamlit Dashboard  →  Report + Pie Chart + Bar Chart + Confidence Gauge
```

---

## ⚙️ Installation

### 1. Clone / copy this folder
```bash
cd MultiAgentResearch
```

### 2. Create a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
# Copy the template
copy .env.template .env        # Windows
cp .env.template .env          # macOS / Linux

# Edit .env and add your OpenAI API key
OPENAI_API_KEY=sk-your-key-here
```

---

## 🚀 Run the Dashboard

```bash
streamlit run app.py
```

Then open your browser at: **http://localhost:8501**

---

## 📊 Dashboard Features

| Feature | Description |
|---|---|
| **🥧 Outlook Pie Chart** | Positive / Challenges / Neutral breakdown of research findings |
| **📊 Sources Bar Chart** | Number of web sources found per search query |
| **🎯 Confidence Gauge** | How well the research answered the question (0–100%) |
| **🏷️ Key Themes** | Top 5 themes extracted from the report |
| **📋 Activity Log** | Live feed of agent actions and queries |
| **📄 Executive Report** | Full structured markdown report with sources |

---

## 💡 Types of Research Questions You Can Ask

The pipeline works best with **current events + structured analysis** topics.
Be specific and include a year for the most up-to-date results.

### 💼 Business & Market Analysis
- *"Market share battle between NVIDIA and AMD in AI chips for 2026"*
- *"Current valuation and IPO pipeline of Indian unicorn startups in 2026"*
- *"Impact of US tariffs on Apple's supply chain in 2026"*
- *"Amazon vs Flipkart e-commerce battle in India 2026"*

### ⚡ Technology & Innovation
- *"Latest advancements in quantum computing commercialization in 2026"*
- *"Current state of humanoid robotics — Figure, Tesla Optimus, Boston Dynamics"*
- *"Generative AI adoption in enterprise software in 2026"*
- *"Solid state battery commercialization in automotive sector 2026"*

### 🌿 Energy & Sustainability
- *"Green hydrogen production costs and viability in 2026"*
- *"Status of nuclear fusion energy projects — ITER, Commonwealth Fusion"*
- *"EV battery recycling industry growth in 2026"*
- *"Solar energy cost reduction trends in 2026"*

### 🏥 Healthcare & Pharma
- *"GLP-1 weight loss drugs market — Ozempic, Wegovy competition in 2026"*
- *"AI in drug discovery — current clinical trials and approvals"*
- *"Cancer immunotherapy breakthroughs in 2026"*

### 🌍 Geopolitics & Economy
- *"India-China trade relations and border situation in 2026"*
- *"BRICS expansion and its impact on the US dollar dominance"*
- *"US Federal Reserve interest rate outlook for 2026"*
- *"Impact of AI on global job markets in 2026"*

### 🏭 Industry & Supply Chain
- *"Semiconductor chip shortage status and recovery in 2026"*
- *"Tesla vs BYD EV sales competition globally in 2026"*
- *"Cloud computing market — AWS vs Azure vs Google Cloud 2026"*

---

## 🗂️ Project Structure

```
MultiAgentResearch/
├── app.py              # Streamlit dashboard UI
├── agents.py           # Core agent logic (Researcher + Writer + LangGraph)
├── requirements.txt    # Python dependencies
├── .env.template       # Environment variable template
├── .env                # Your secrets (not committed to git)
└── README.md           # This file
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | Your OpenAI API key (GPT-4o) |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `langchain-openai` | GPT-4o LLM integration |
| `langgraph` | Multi-agent orchestration |
| `duckduckgo-search` | Live web search (no API key needed) |
| `streamlit` | Dashboard UI |
| `plotly` | Interactive charts |
| `python-dotenv` | Environment variable loading |
| `truststore` | SSL certificate handling (corporate proxies) |

---

## 🛠️ Troubleshooting

**SSL Certificate Error**
> Already handled via `truststore.inject_into_ssl()` — uses your system's certificate store.

**OpenAI API Key Error**
> Ensure your `.env` file has `OPENAI_API_KEY=sk-...` with no spaces around `=`.

**DuckDuckGo Rate Limiting**
> If searches fail, wait 30 seconds and retry. DuckDuckGo has soft rate limits.

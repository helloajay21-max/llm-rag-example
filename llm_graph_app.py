import truststore
truststore.inject_into_ssl()

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# CONFIG
# ==========================================

st.set_page_config(layout="wide")
st.title("🌍 Global Leader Timeline (Official Wikidata Accurate)")

query_input = st.text_input(
    "Ask (Example: Prime Ministers of India, Presidents of United States)"
)

# ==========================================
# PARSE QUERY
# ==========================================

def parse_query(text):

    text = text.lower()

    if "prime minister" in text:
        role = "Prime Minister"
    elif "president" in text:
        role = "President"
    else:
        return None, None

    if "of" not in text:
        return None, None

    country = text.split("of")[-1].strip().title()

    return role, country


# ==========================================
# GET OFFICE QID
# ==========================================

def get_office_qid(role, country):

    search_term = f"{role} of {country}"

    url = "https://www.wikidata.org/w/api.php"

    headers = {"User-Agent": "LeaderTimelineApp/1.0"}

    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "search": search_term
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        if not data.get("search"):
            return None

        return data["search"][0]["id"]

    except:
        return None


# ==========================================
# FETCH LEADERS
# ==========================================

def fetch_leaders(office_qid):

    query = f"""
    SELECT ?personLabel ?start ?end WHERE {{
      ?person p:P39 ?statement.
      ?statement ps:P39 wd:{office_qid}.
      ?statement pq:P580 ?start.
      OPTIONAL {{ ?statement pq:P582 ?end. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    ORDER BY ?start
    """

    url = "https://query.wikidata.org/sparql"

    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "LeaderTimelineApp/1.0"
    }

    try:
        r = requests.get(url, params={"query": query}, headers=headers, timeout=20)

        if r.status_code != 200:
            return []

        data = r.json()

        leaders = []

        for item in data["results"]["bindings"]:

            name = item["personLabel"]["value"]
            start = item["start"]["value"]

            if "end" in item:
                end = item["end"]["value"]
            else:
                end = datetime.utcnow().isoformat()

            leaders.append((name, start, end))

        return leaders

    except:
        return []


# ==========================================
# RENDER TIMELINE
# ==========================================

def render_vertical_bar_chart(leaders, role, country):

    import pandas as pd
    import plotly.express as px
    import streamlit as st

    if not leaders:
        st.error("No leaders found.")
        return

    df = pd.DataFrame(leaders, columns=["Leader", "Start", "End"])

    # Clean datetime strings
    df["Start"] = df["Start"].astype(str).str.replace("+", "", regex=False)
    df["End"] = df["End"].astype(str).str.replace("+", "", regex=False)

    # Convert safely
    df["Start"] = pd.to_datetime(df["Start"], errors="coerce", utc=True)
    df["End"] = pd.to_datetime(df["End"], errors="coerce", utc=True)

    # Current leader handling
    df["End"] = df["End"].fillna(pd.Timestamp.utcnow())

    df = df.dropna(subset=["Start", "End"])

    # Remove timezone
    df["Start"] = df["Start"].dt.tz_convert(None)
    df["End"] = df["End"].dt.tz_convert(None)

    # Extract years
    df["Start Year"] = df["Start"].dt.year
    df["End Year"] = df["End"].dt.year

    # Label like "2001-2026"
    df["Tenure Label"] = df["Start Year"].astype(str) + "-" + df["End Year"].astype(str)

    # Tenure length for bar height
    df["Years Served"] = df["End Year"] - df["Start Year"]

    df = df.sort_values("Start Year")

    # VERTICAL BAR GRAPH
    fig = px.bar(
        df,
        x="Leader",
        y="Years Served",
        color="Leader",
        text="Tenure Label",   # <-- SHOW 2001-2026
        title=f"{role}s of {country} (Vertical Tenure Chart)"
    )

    fig.update_traces(textposition="outside")

    fig.update_layout(
        height=700,
        showlegend=False,
        xaxis_title="Leader",
        yaxis_title="Years Served",
        xaxis_tickangle=-45,
        font=dict(size=14)
    )

    st.plotly_chart(fig, use_container_width=True)
# ==========================================
# MAIN
# ==========================================

if st.button("Generate Official Chart") and query_input:

    role, country = parse_query(query_input)

    if not role:
        st.error("Use format: Prime Ministers of India / Presidents of United States")
    else:

        office_qid = get_office_qid(role, country)

        if not office_qid:
            st.error("Office not found in Wikidata")
        else:

            leaders = fetch_leaders(office_qid)

            render_vertical_bar_chart(leaders, role, country)
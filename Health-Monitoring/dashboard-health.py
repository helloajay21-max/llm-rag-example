import streamlit as st
import plotly.express as px
from data_loader import load_sample_data, load_uploaded_file
from genai_insights import generate_insights, chat_with_ai

# Page config
st.set_page_config(
    page_title="AI Health Dashboard",
    layout="wide",
    page_icon="🏥"
)

st.title("🏥 AI Health Monitoring System")

# -------------------------------
# DATA SECTION
# -------------------------------
st.sidebar.header("📂 Data Source")

uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

try:
    if uploaded_file:
        df = load_uploaded_file(uploaded_file)
    else:
        df = load_sample_data()
except Exception as e:
    st.error(str(e))
    st.stop()

# Preview
st.subheader("📊 Data Preview")
st.dataframe(df.head())

# Debug columns
columns = list(df.columns)
st.write("Columns detected:", columns)

# -------------------------------
# KPI CARDS
# -------------------------------
st.subheader("📌 Key Metrics")

col1, col2, col3 = st.columns(3)

if "heart_rate" in df.columns:
    col1.metric("Avg Heart Rate", round(df["heart_rate"].mean(), 1))

if "steps" in df.columns:
    col2.metric("Avg Steps", int(df["steps"].mean()))

if "sleep_hours" in df.columns:
    col3.metric("Avg Sleep", round(df["sleep_hours"].mean(), 1))

# -------------------------------
# FILTER (OPTIONAL)
# -------------------------------
st.sidebar.header("📅 Filter")

if len(df) > 1:
    start, end = st.sidebar.slider(
        "Select Data Range",
        0, len(df)-1, (0, len(df)-1)
    )
    df = df.iloc[start:end+1]

# -------------------------------
# CHARTS (PLOTLY)
# -------------------------------
st.subheader("📈 Health Trends")

if len(columns) > 1:

    # Single metric
    metric = st.selectbox("Select Metric", columns[1:])

    fig = px.line(
        df,
        x=columns[0],
        y=metric,
        title=f"{metric} Trend",
        markers=True
    )

    fig.update_layout(
        template="plotly_white",
        title_font_size=20,
        xaxis_title="Date",
        yaxis_title=metric,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Multi-metric comparison
    st.subheader("📊 Compare Metrics")

    selected_metrics = st.multiselect(
        "Select multiple metrics",
        columns[1:],
        default=[columns[1]]
    )

    if selected_metrics:
        fig2 = px.line(
            df,
            x=columns[0],
            y=selected_metrics,
            markers=True
        )
        st.plotly_chart(fig2, use_container_width=True)

else:
    st.error("Not enough columns in dataset")
    st.stop()

# -------------------------------
# ALERTS
# -------------------------------
st.subheader("⚠️ Health Alerts")

if "heart_rate" in df.columns and df["heart_rate"].mean() > 90:
    st.warning("High average heart rate detected")

if "sleep_hours" in df.columns and df["sleep_hours"].mean() < 5:
    st.warning("Low sleep detected")

# -------------------------------
# AI INSIGHTS
# -------------------------------
st.subheader("🤖 AI Insights")

if st.button("Generate Insights"):
    with st.spinner("Analyzing data..."):
        summary = df.describe().to_string()
        insights = generate_insights(summary)
        st.success(insights)

# -------------------------------
# CHAT UI
# -------------------------------
st.subheader("💬 Health Chat Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful health assistant."}
    ]

# Display chat history
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
user_input = st.chat_input("Ask your health question...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        response = chat_with_ai(st.session_state.messages)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

# -------------------------------
# DISCLAIMER
# -------------------------------
st.info("⚠️ This AI provides general guidance and is not a substitute for professional medical advice.")
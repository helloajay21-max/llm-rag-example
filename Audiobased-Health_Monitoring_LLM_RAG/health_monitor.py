import streamlit as st
import whisper
import tempfile
import numpy as np
import soundfile as sf

from openai import OpenAI
from streamlit_mic_recorder import mic_recorder

# =========================
# 🔐 OpenAI
# =========================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =========================
# 🎤 Whisper
# =========================
@st.cache_resource
def load_whisper():
    return whisper.load_model("small", device="cpu")

# =========================
# 🤖 LLM
# =========================
def analyze(query):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}]
    )
    return response.choices[0].message.content

# =========================
# 🧠 Pipeline
# =========================
def run_pipeline(audio_bytes):
    model = load_whisper()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        audio_path = f.name

    result = model.transcribe(audio_path, language="en", fp16=False)
    text = result["text"].strip()

    if not text:
        return None, "❌ Could not understand audio."

    output = analyze(text)
    return text, output

# =========================
# 🖥️ UI
# =========================
st.title("🎤 Universal Voice AI Assistant")

st.write("👉 Click Start → Speak → Stop → Ask")

# 🔥 SESSION STATE FIX
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

# 🎤 Record
audio = mic_recorder(
    start_prompt="🎤 Start Recording",
    stop_prompt="⏹ Stop Recording",
    just_once=True,
)

# Save audio in session
if audio:
    st.session_state.audio_bytes = audio["bytes"]

# Show audio if exists
if st.session_state.audio_bytes:
    st.success("✅ Audio recorded successfully")
    st.audio(st.session_state.audio_bytes, format="audio/wav")

# 🚀 ASK BUTTON
if st.button("Ask AI"):

    if st.session_state.audio_bytes is None:
        st.error("❌ No audio recorded")
    else:
        with st.spinner("Processing..."):
            text, output = run_pipeline(st.session_state.audio_bytes)

        if text is None:
            st.error(output)
        else:
            st.subheader("📝 You said")
            st.write(text)

            st.subheader("🤖 AI Answer")
            st.write(output)

# =========================
st.info("⚠️ For medical queries, consult a professional.")
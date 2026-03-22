import streamlit as st
import whisper
import tempfile
from openai import OpenAI

from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import numpy as np

from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# =========================
# 🔐 OpenAI Client
# =========================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =========================
# 🎤 Whisper Model
# =========================
@st.cache_resource
def load_whisper():
    return whisper.load_model("base", device="cpu")

# =========================
# 📚 Vector DB
# =========================
@st.cache_resource
def build_vector_db():
    docs = """
    Cough and fever may indicate respiratory infection.
    Chest pain with shortness of breath may indicate cardiac issues.
    Fatigue and dizziness may indicate anemia.
    """

    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = splitter.split_text(docs)

    embeddings = HuggingFaceEmbeddings()
    return FAISS.from_texts(texts, embeddings)

# =========================
# 🔍 RAG
# =========================
def retrieve_context(query, db):
    docs = db.similarity_search(query, k=3)
    return "\n".join([d.page_content for d in docs])

# =========================
# 🤖 LLM
# =========================
def analyze(query, context):
    prompt = f"""
    Patient said: {query}
    Context: {context}

    Give:
    - Possible condition
    - Risk level
    - Advice
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content

# =========================
# 🎙️ AUDIO PROCESSOR
# =========================
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame: av.AudioFrame):
        audio = frame.to_ndarray()
        self.frames.append(audio)
        return frame

# =========================
# 🧠 PROCESS AUDIO
# =========================
def process_audio(frames):
    audio = np.concatenate(frames, axis=0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        import soundfile as sf
        sf.write(f.name, audio, 16000)
        return f.name

def run_pipeline(audio_path):
    model = load_whisper()
    db = build_vector_db()

    text = model.transcribe(audio_path)["text"]
    context = retrieve_context(text, db)
    output = analyze(text, context)

    return text, output

# =========================
# 🖥️ UI
# =========================
st.title("🩺 AI Health Assistant (Voice + RAG + LLM)")

# 🎤 MIC INPUT
st.subheader("🎙️ Speak your question")

ctx = webrtc_streamer(
    key="audio",
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

# 📁 Upload fallback
uploaded = st.file_uploader("Or upload audio", type=["wav", "mp3"])

if st.button("Analyze"):

    audio_path = None

    # Mic input
    if ctx.audio_processor and ctx.audio_processor.frames:
        audio_path = process_audio(ctx.audio_processor.frames)

    # Upload fallback
    elif uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(uploaded.read())
            audio_path = f.name

    if audio_path:
        with st.spinner("Processing..."):
            text, output = run_pipeline(audio_path)

        st.subheader("📝 Transcription")
        st.write(text)

        st.subheader("🤖 AI Response")
        st.write(output)

    else:
        st.warning("Please record or upload audio")

st.info("⚠️ Not a medical diagnosis tool")
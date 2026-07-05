"""
Central configuration for HaqDar.
Import from here everywhere instead of hardcoding paths/models.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load variables from a .env file in the project root into os.environ.
# Without this, python-dotenv being installed does nothing on its own —
# os.environ.get(...) below would only ever see real OS/shell environment
# variables, never anything written in a .env file. This was silently
# breaking OPENAI_API_KEY / GMAIL_ADDRESS / GMAIL_APP_PASSWORD / TAVILY_API_KEY
# any time the app was started in a terminal session where those hadn't been
# manually exported first.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# --- Paths ---
DATA_DIR = BASE_DIR / "data"
DATASET_PATH = DATA_DIR / "scpa_dataset.json"

RAG_DIR = BASE_DIR / "rag"
CHROMA_PATH = str(RAG_DIR / "chroma_db")
VECTORIZER_PATH = RAG_DIR / "tfidf_vectorizer.pkl"
CHROMA_COLLECTION_NAME = "scpa_sections"

# --- LLM config ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.2

# --- Langfuse (optional observability) ---
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# --- Agent behavior ---
RETRIEVAL_TOP_K = 4
MAX_REFLECTION_LOOPS = 1  # how many times the drafter can be sent back for revision

# --- Email delivery (Gmail SMTP) ---
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
DELIVERY_ENABLED = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)

# --- Tavily (real-time web search via official remote MCP server) ---
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# --- Location lookup (forum address via OpenStreetMap Nominatim — free, no API key) ---
DEFAULT_CITY = "Karachi"

# --- FastAPI backend (security + deployment) ---
# Comma-separated list of origins allowed to call the API (the Streamlit
# frontend's own origin, e.g. "http://localhost:8501,https://myapp.example.com").
# Defaults to localhost Streamlit ports for local dev.
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if o.strip()
]

# Optional shared-secret header (X-API-Key) required on every backend request.
# Leave BACKEND_API_KEY unset in dev to disable this check entirely; set it in
# production and configure the same value on the Streamlit side.
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "")
BACKEND_AUTH_ENABLED = bool(BACKEND_API_KEY)

# Simple in-memory rate limit: max requests per IP per window (seconds).
# Good enough for a single-process deployment; swap for Redis-backed limiting
# (e.g. slowapi + redis) if the backend is ever scaled to multiple workers.
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

# Where the Streamlit frontend should reach the backend (used by frontend/streamlit_app.py).
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

"""
Frontend-only configuration.

Deliberately separate from the root config.py: the Streamlit frontend never
needs (and should never have) OPENAI_API_KEY, GMAIL_APP_PASSWORD, or
TAVILY_API_KEY. It only ever talks to the backend over HTTP, so its .env
should contain nothing but BACKEND_URL and (optionally) BACKEND_API_KEY.
This keeps the two deployable as separate containers/hosts without the
frontend image ever bundling secrets it has no use for.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Where the FastAPI backend is reachable from the frontend's network.
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")

# Must match the backend's BACKEND_API_KEY if the backend has auth enabled.
# Leave blank if the backend doesn't require it (local dev default).
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "")

REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "60"))

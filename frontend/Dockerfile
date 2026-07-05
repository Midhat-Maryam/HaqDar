FROM python:3.12-slim

WORKDIR /app

COPY requirements-frontend.txt .
RUN pip install --no-cache-dir -r requirements-frontend.txt

# Only the frontend/ directory is copied in — this image never sees agents/,
# backend/, or the root .env, so it has no way to leak OPENAI_API_KEY,
# GMAIL_APP_PASSWORD, or TAVILY_API_KEY even if compromised. It only ever
# talks to the backend over HTTP via BACKEND_URL.
COPY frontend/ .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import requests,os,sys; sys.exit(0 if requests.get('http://localhost:8501/_stcore/health', timeout=3).ok else 1)"

CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]

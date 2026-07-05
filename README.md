# HaqDar (AI Consumer Rights Advisor

An agentic AI system that listens to a Pakistani consumer's complaint, identifies their legal rights under the **Sindh Consumer Protection Act, 2014** (and its 2017 Rules), drafts a formal complaint letter, and routes them to the exact authority or forum to file with.


## Architecture

![Architecture](docs/architecture.svg)

**Flow:**
1. **Classifier** — GPT-4o mini classifies the complaint into one of four issue types (defective product, defective service, unfair/deceptive practice, pricing/receipt/disclosure), or flags it unclear.
2. **Supervisor decision** — if classification confidence is low, the graph ends and asks a clarifying question instead of guessing (dynamic routing, not a fixed pipeline).
3. **Legal Retrieval** — queries a ChromaDB collection of the Act's 48 sections (chunked by section, enriched with plain-language trigger phrases) for the most relevant provisions.
4. **Letter Drafter** — GPT-4o mini drafts a formal complaint letter, instructed to cite *only* the retrieved section numbers.
5. **Reflection** — a second GPT-4o call checks the draft against the actual retrieved text, catching hallucinated citations or unsupported claims. If it fails, the graph loops back to the drafter.
6. **Authority Router** — an MCP tool call maps the issue type to the correct forum (Consumer Court vs. the Authority) and any filing pre-requisites (e.g. the mandatory 15-day notice under s.29).
7. **Output assembly** — final letter + cited sections + filing instructions returned to the UI.

Every node call is traced via **Langfuse** when configured.

## UI Architecture: FastAPI backend + Streamlit frontend

The agent graph is served behind a **FastAPI backend** (`backend/`) and consumed by a **Streamlit frontend** (`frontend/`) — the two are separate deployable services that only talk to each other over HTTP.

- **`backend/`** — owns all secrets and heavy dependencies (LangGraph, ChromaDB, OpenAI, Tavily, Gmail SMTP). Exposes three endpoints: `POST /api/complaint/analyze`, `POST /api/company/lookup`, `POST /api/letter/send`, plus `GET /health`. See "Security" below.
- **`frontend/`** — a guided, one-question-at-a-time Streamlit UI that never imports agent code or sees any secret; it only calls the backend's REST API (`frontend/api_client.py`) using `BACKEND_URL` (and an optional `BACKEND_API_KEY`). This means the frontend container can be safely deployed even in a lower-trust environment (e.g. a public-facing edge) since compromising it exposes nothing beyond the backend's public API surface.

The legacy Gradio UI (`app/main.py`) still works standalone (`python app/main.py`) and is kept for reference, but is superseded by the backend/frontend split for anything beyond local experimentation.

## Tech Stack
LangGraph · ChromaDB · MCP · OpenAI GPT-4o mini · Langfuse · FastAPI · Streamlit · Docker

## Project Structure
```
haqdar/
├── agents/
│   ├── state.py              # shared LangGraph state schema
│   ├── llm.py                 # shared ChatOpenAI client
│   ├── classifier.py          # Node 1: intake/classifier
│   ├── retrieval_node.py      # Node 2: legal retrieval (ChromaDB)
│   ├── drafter.py             # Node 3: letter drafter
│   ├── reflection.py          # Node 4: reflection/critique loop
│   ├── authority_router.py    # Node 5: authority/forum routing
│   ├── company_lookup.py      # shop/company contact search (Tavily MCP)
│   ├── delivery_node.py       # Node 6: email delivery (Gmail SMTP)
│   ├── graph.py                # graph wiring, supervisor conditional edges
│   └── tracing.py             # Langfuse callback wrapper
├── backend/
│   ├── main.py                 # FastAPI app: /api/complaint/analyze, /api/company/lookup, /api/letter/send, /health
│   ├── schemas.py              # Pydantic request/response models (input validation)
│   └── security.py             # API-key auth + per-IP rate limiting
├── frontend/
│   ├── streamlit_app.py        # guided intake wizard + complaint/letter/send UI
│   ├── api_client.py           # thin HTTP client to the backend
│   ├── config.py               # frontend-only config (BACKEND_URL, no secrets)
│   ├── .env.example
│   └── Dockerfile
├── data/
│   ├── build_dataset.py       # builds scpa_dataset.json from the Act text
│   └── scpa_dataset.json      # 40 Act sections + 8 Rules sections + routing table
├── rag/
│   ├── build_index.py         # embeds dataset into ChromaDB (TF-IDF)
│   ├── retriever.py            # retrieval function used by agents + MCP
│   ├── tfidf_vectorizer.pkl
│   └── chroma_db/              # persistent Chroma collection
├── mcp_server/
│   └── server.py               # exposes lookup_authority + search_consumer_law as MCP tools
├── app/
│   └── main.py                 # legacy Gradio UI (kept for reference; superseded by backend/ + frontend/)
├── tests/
├── docs/
│   └── architecture.svg
├── config.py                   # central paths/model config + backend security settings
├── requirements.txt            # legacy combined deps (Gradio UI)
├── requirements-backend.txt    # FastAPI backend deps
├── requirements-frontend.txt   # Streamlit frontend deps (no agent/LLM deps)
├── Dockerfile.backend
├── frontend/Dockerfile
├── docker-compose.yml           # backend + frontend services
├── .env.example                 # backend secrets + security config
└── README.md
```

## Setup

```bash
git clone <your-repo-url>
cd haqdar
pip install -r requirements-backend.txt
pip install -r requirements-frontend.txt   # if also running the frontend locally
cp .env.example .env    # fill in OPENAI_API_KEY (and Langfuse/Tavily/Gmail keys as needed)
cp frontend/.env.example frontend/.env
```

### Build the knowledge base
```bash
python data/build_dataset.py   # generates data/scpa_dataset.json
python rag/build_index.py      # embeds into ChromaDB, prints retrieval sanity checks
```

### Run locally (two processes)
```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
streamlit run frontend/streamlit_app.py
```
Visit `http://localhost:8501`. The frontend calls the backend at `http://localhost:8000` by default (`frontend/.env`'s `BACKEND_URL`).

### Run via Docker Compose (recommended for anything beyond local dev)
```bash
docker-compose up --build
```
This builds and runs both services on one network: backend on `:8000`, frontend on `:8501`, with the frontend automatically pointed at `http://backend:8000`.

### Run the legacy Gradio UI (optional, single process)
```bash
pip install -r requirements.txt
python app/main.py
```
Visit `http://localhost:7860`.

### Run the MCP server standalone
```bash
python mcp_server/server.py
```
## Sample Interaction

**Input:**
> "I bought a washing machine two weeks ago and it stopped working. The shop refuses to repair or replace it."

**Output:**
- **Classified as:** Defective Product
- **Cited sections:** Act §4 (Liability for defective products), Act §29 (Settlement of Claims — mandatory notice), Act §32 (Order of Consumer Court)
- **Forum:** Consumer Court (District level, presided by Judicial Magistrate)
- **Draft letter:** formal notice citing §4 and §29, demanding repair/replacement/refund within 15 days per the mandatory pre-filing notice requirement

## Design Notes

- **Why TF-IDF instead of OpenAI embeddings for the knowledge base:** the corpus is small (48 sections) and legal text has distinctive vocabulary; TF-IDF avoids an external embedding-model dependency for local dev. Section text is enriched with plain-language "trigger phrases" (e.g. "phone stopped working" → §4) to close the vocabulary gap between everyday complaint language and legal terminology. Swapping to `text-embedding-3-small` is a one-line change in `rag/build_index.py` if you want semantic embeddings in production.
- **Why reflection matters here:** legal citation accuracy is the single biggest failure mode for an LLM-drafted legal letter. The reflection node is a genuine second LLM pass checking the draft against ground-truth retrieved text, not just a formatting check.
- **Jurisdiction scope:** Sindh only, matching the province of the source Act. Federal/other-provincial consumer protection laws are out of scope for this MVP.

## Author
Midhat Maryam

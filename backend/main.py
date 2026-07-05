"""
HaqDar FastAPI backend.

Exposes the existing LangGraph agent (agents/graph.py) and helper modules
(company_lookup, drafter.assemble_letter, delivery_node) as a small REST API
so any frontend — the new Streamlit app in frontend/, or anything else — can
drive HaqDar without importing LangGraph/Chroma/LLM code directly.

Endpoints:
  GET  /health                    liveness check (no auth, no rate limit)
  POST /api/complaint/analyze     classify + draft letter + route to authority
  POST /api/company/lookup        find a shop/company's email + address
  POST /api/letter/send           rebuild the letter with shop details and email it

Security:
  - CORS restricted to config.ALLOWED_ORIGINS (set to your Streamlit origin(s))
  - Optional shared-secret auth via X-API-Key header (config.BACKEND_API_KEY)
  - Per-IP in-memory rate limiting (config.RATE_LIMIT_*)
  - Strict Pydantic request models (backend/schemas.py) — no raw dict payloads
  - No internal exception detail (stack traces, file paths) ever reaches the
    client; everything is logged server-side and mapped to a generic message
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS, BACKEND_AUTH_ENABLED
from backend.schemas import (
    AnalyzeComplaintRequest,
    AnalyzeComplaintResponse,
    CompanyLookupRequest,
    CompanyLookupResponse,
    SendLetterRequest,
    SendLetterResponse,
)
from backend.security import require_api_key, enforce_rate_limit

from agents.graph import haqdar_graph
from agents.tracing import invoke_traced
from agents.company_lookup import search_company_contact
from agents.delivery_node import send_email_notice
from agents.drafter import assemble_letter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("haqdar.backend")

app = FastAPI(
    title="HaqDar API",
    description="AI Consumer Rights Advisor for Pakistani Consumers (Sindh) — backend API",
    version="1.0.0",
    # Disable interactive docs in production if you'd rather not expose the
    # schema publicly; leaving them on by default since this is a student
    # capstone project meant to be inspected.
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

_COMMON_DEPS = [Depends(enforce_rate_limit), Depends(require_api_key)]


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak internal error detail (stack traces, file paths, API
    key fragments in exception messages, etc.) to the client — log the
    full exception server-side and return a generic message instead."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/health", tags=["meta"])
async def health():
    """Liveness check — intentionally has no auth/rate-limit dependency so
    orchestrators (Docker, k8s, load balancers) can hit it freely."""
    return {"status": "ok", "auth_enabled": BACKEND_AUTH_ENABLED}


@app.post(
    "/api/complaint/analyze",
    response_model=AnalyzeComplaintResponse,
    dependencies=_COMMON_DEPS,
    tags=["complaint"],
)
async def analyze_complaint(payload: AnalyzeComplaintRequest):
    """
    Runs the full LangGraph pipeline: classify -> retrieve legal sections ->
    draft letter -> reflect/revise -> route to authority. Returns everything
    the frontend needs to show the consumer their letter and where to file,
    or a clarifying question if the complaint was too vague to classify.
    """
    try:
        result = invoke_traced(
            haqdar_graph,
            {
                "complaint_text": payload.complaint_text,
                "user_name": payload.user_name,
                "user_address": payload.user_address,
                "user_city_postal": payload.user_city_postal,
                "user_email": payload.user_email,
                "user_phone": payload.user_phone,
            },
        )
    except Exception:
        logger.exception("Graph invocation failed during /api/complaint/analyze")
        raise HTTPException(status_code=502, detail="Failed to analyze complaint. Please try again.")

    if result.get("clarifying_question"):
        return AnalyzeComplaintResponse(clarifying_question=result["clarifying_question"])

    final = result.get("final_output", {})
    return AnalyzeComplaintResponse(
        issue_type=final.get("issue_type"),
        cited_sections=final.get("cited_sections", []),
        authority=final.get("authority"),
        letter_draft=final.get("letter_draft"),
        letter_body=result.get("letter_body", ""),
    )


@app.post(
    "/api/company/lookup",
    response_model=CompanyLookupResponse,
    dependencies=_COMMON_DEPS,
    tags=["company"],
)
async def lookup_company(payload: CompanyLookupRequest):
    """
    Best-effort search for a shop/company's public contact email and
    address, for the consumer to review and confirm — never auto-sent.
    """
    try:
        kwargs = {"company_name": payload.company_name}
        if payload.city:
            kwargs["city"] = payload.city
        result = search_company_contact(**kwargs)
    except Exception:
        logger.exception("Company lookup failed during /api/company/lookup")
        raise HTTPException(status_code=502, detail="Company lookup failed. Please try again.")

    if result.get("error"):
        # Not a server error — just "please type a company name" etc.
        raise HTTPException(status_code=400, detail=result["error"])

    return CompanyLookupResponse(**result)


@app.post(
    "/api/letter/send",
    response_model=SendLetterResponse,
    dependencies=_COMMON_DEPS,
    tags=["letter"],
)
async def send_letter(payload: SendLetterRequest):
    """
    Rebuilds the full letter deterministically (now that the shop's name/
    address are known) via the same assemble_letter() used at draft time,
    then sends it via Gmail SMTP. This endpoint IS the human-in-the-loop
    confirmation gate — the frontend only calls this after the consumer has
    reviewed the draft and explicitly clicked "Confirm & Send".
    """
    rebuild_state = {
        "letter_body": payload.letter_body,
        "issue_type": payload.issue_type,
        "user_name": payload.user_name,
        "user_address": payload.user_address,
        "user_city_postal": payload.user_city_postal,
        "user_email": payload.user_email,
        "user_phone": payload.user_phone,
        "shop_name": payload.shop_name,
        "shop_address": payload.shop_address,
    }

    try:
        final_letter = assemble_letter(payload.letter_body, rebuild_state)
        result = send_email_notice(
            to_email=str(payload.shop_contact),
            letter_text=final_letter,
            shop_name=payload.shop_name,
        )
    except Exception:
        logger.exception("Delivery failed during /api/letter/send")
        raise HTTPException(status_code=502, detail="Failed to send the letter. Please try again.")

    return SendLetterResponse(
        sent=result.get("sent", False),
        to=result.get("to"),
        reason=result.get("reason"),
        final_letter=final_letter,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

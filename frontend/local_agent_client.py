"""
In-process replacement for api_client.py.

Same function names/signatures as api_client.py (analyze_complaint,
lookup_company, send_letter, check_health, ApiError) so streamlit_app.py
needs only a one-line import change to switch between:
  - api_client.py       -> HTTP calls to a separately-deployed FastAPI backend
  - local_agent_client.py -> direct in-process calls to agents/ (this file)

Use this version for a single-service deploy (e.g. Streamlit Community
Cloud on its own, with OPENAI_API_KEY etc. set as Streamlit secrets) where
running a separate backend host is unnecessary overhead. This file DOES
import LangGraph/Chroma/LLM code and DOES touch secrets directly, unlike
api_client.py — that's the trade-off for collapsing the two services into
one deployable app.
"""

from typing import Optional

from agents.graph import haqdar_graph
from agents.tracing import invoke_traced
from agents.company_lookup import search_company_contact
from agents.delivery_node import send_email_notice
from agents.drafter import assemble_letter


class ApiError(Exception):
    """Raised for any pipeline failure. `detail` is safe to show to the user."""

    def __init__(self, detail: str, status_code: Optional[int] = None):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def analyze_complaint(complaint_text: str, user_details: dict) -> dict:
    try:
        result = invoke_traced(
            haqdar_graph,
            {
                "complaint_text": complaint_text,
                "user_name": user_details.get("user_name", ""),
                "user_address": user_details.get("user_address", ""),
                "user_city_postal": user_details.get("user_city_postal", ""),
                "user_email": user_details.get("user_email", ""),
                "user_phone": user_details.get("user_phone", ""),
            },
        )
    except Exception as e:
        raise ApiError(f"Failed to analyze complaint: {e}")

    if result.get("clarifying_question"):
        return {"clarifying_question": result["clarifying_question"]}

    final = result.get("final_output", {})
    return {
        "issue_type": final.get("issue_type"),
        "cited_sections": final.get("cited_sections", []),
        "authority": final.get("authority"),
        "letter_draft": final.get("letter_draft"),
        "letter_body": result.get("letter_body", ""),
    }


def lookup_company(company_name: str, city: Optional[str] = None) -> dict:
    try:
        kwargs = {"company_name": company_name}
        if city:
            kwargs["city"] = city
        result = search_company_contact(**kwargs)
    except Exception as e:
        raise ApiError(f"Company lookup failed: {e}")

    if result.get("error"):
        raise ApiError(result["error"], status_code=400)

    return result


def send_letter(
    letter_body: str,
    issue_type: str,
    user_details: dict,
    shop_name: str,
    shop_address: str,
    shop_contact: str,
) -> dict:
    rebuild_state = {
        "letter_body": letter_body,
        "issue_type": issue_type,
        **user_details,
        "shop_name": shop_name,
        "shop_address": shop_address,
    }
    try:
        final_letter = assemble_letter(letter_body, rebuild_state)
        result = send_email_notice(
            to_email=str(shop_contact),
            letter_text=final_letter,
            shop_name=shop_name,
        )
    except Exception as e:
        raise ApiError(f"Failed to send the letter: {e}")

    return {
        "sent": result.get("sent", False),
        "to": result.get("to"),
        "reason": result.get("reason"),
        "final_letter": final_letter,
    }


def check_health() -> bool:
    # No separate service to ping — the pipeline runs in this same process.
    return True

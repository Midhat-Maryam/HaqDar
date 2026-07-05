"""
Thin HTTP client the Streamlit app uses to talk to the FastAPI backend.
Centralizes headers, timeouts, and error normalization so streamlit_app.py
only ever deals with plain dicts and a consistent error shape, never raw
requests/HTTP exceptions.
"""

from typing import Optional

import requests

from config import BACKEND_URL, BACKEND_API_KEY, REQUEST_TIMEOUT_SECONDS


class ApiError(Exception):
    """Raised for any backend call failure — network error, timeout, or a
    non-2xx response. `detail` is safe to show directly to the user (the
    backend never leaks stack traces in its error responses)."""

    def __init__(self, detail: str, status_code: Optional[int] = None):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if BACKEND_API_KEY:
        headers["X-API-Key"] = BACKEND_API_KEY
    return headers


def _post(path: str, payload: dict) -> dict:
    url = f"{BACKEND_URL}{path}"
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise ApiError("The server took too long to respond. Please try again.")
    except requests.exceptions.ConnectionError:
        raise ApiError(f"Couldn't reach the HaqDar backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.RequestException as e:
        raise ApiError(f"Request failed: {e}")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text or f"HTTP {resp.status_code}"
        raise ApiError(detail, status_code=resp.status_code)

    try:
        return resp.json()
    except ValueError:
        raise ApiError("Backend returned an unexpected (non-JSON) response.")


def analyze_complaint(complaint_text: str, user_details: dict) -> dict:
    return _post("/api/complaint/analyze", {"complaint_text": complaint_text, **user_details})


def lookup_company(company_name: str, city: Optional[str] = None) -> dict:
    payload = {"company_name": company_name}
    if city:
        payload["city"] = city
    return _post("/api/company/lookup", payload)


def send_letter(
    letter_body: str,
    issue_type: str,
    user_details: dict,
    shop_name: str,
    shop_address: str,
    shop_contact: str,
) -> dict:
    return _post(
        "/api/letter/send",
        {
            "letter_body": letter_body,
            "issue_type": issue_type,
            **user_details,
            "shop_name": shop_name,
            "shop_address": shop_address,
            "shop_contact": shop_contact,
        },
    )


def check_health() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False

"""
Node 6: Delivery (optional, human-confirmed)
Sends the drafted + reflected complaint letter to the shop/company via email
(Gmail SMTP). This node ONLY sends if state["send_confirmed"] is True — the
consumer must explicitly confirm in the UI after reading the draft. Nothing
is sent automatically as part of the base graph run.

Core function is also wrapped as an MCP tool in mcp_server/server.py so it can
be called either directly (as here) or via MCP protocol.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, SMTP_HOST, SMTP_PORT, DELIVERY_ENABLED
from agents.state import HaqDarState


def send_email_notice(to_email: str, letter_text: str, shop_name: str = "") -> dict:
    """
    Core delivery function. Sends `letter_text` to `to_email` via Gmail SMTP.
    Wrapped as an MCP tool (send_notice_tool) in mcp_server/server.py.

    to_email: consumer-provided shop/company email address
    shop_name: consumer-provided shop/company name, used in the subject line
               so the recipient sees at a glance who the notice concerns
    """
    if not DELIVERY_ENABLED:
        return {
            "sent": False,
            "reason": "Email credentials not configured (set GMAIL_ADDRESS, "
                      "GMAIL_APP_PASSWORD in .env).",
        }

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    subject = f"Formal Consumer Complaint Notice — {shop_name}" if shop_name else "Formal Consumer Complaint Notice"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(letter_text, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        return {"sent": True, "to": to_email}
    except Exception as e:
        return {"sent": False, "reason": str(e)}


def deliver_notice(state: HaqDarState) -> HaqDarState:
    """
    LangGraph node. Only fires the actual send if the consumer has confirmed
    (state["send_confirmed"] is True) and provided a shop contact email.
    This is the human-in-the-loop gate — the graph will reach this node after
    authority routing, but will not send anything unless the UI has already
    obtained explicit user confirmation and re-invoked the graph with
    send_confirmed=True.
    """
    if not state.get("send_confirmed"):
        return {
            **state,
            "delivery_status": {"sent": False, "reason": "not confirmed by user"},
        }

    to_email = state.get("shop_contact")
    shop_name = state.get("shop_name", "")
    letter = state.get("letter_draft", "")

    if not to_email:
        return {
            **state,
            "delivery_status": {"sent": False, "reason": "no shop contact email provided"},
        }

    result = send_email_notice(to_email, letter, shop_name)
    return {**state, "delivery_status": result}

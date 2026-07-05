"""
HaqDar Streamlit app (single-service deploy).

Calls the LangGraph agent pipeline directly in-process via
local_agent_client.py — no separate FastAPI backend needed. This is the
simplest deploy path (e.g. Streamlit Community Cloud on its own): set
OPENAI_API_KEY (and optionally LANGFUSE_*/TAVILY_API_KEY/GMAIL_*) as
Streamlit secrets, and everything runs in this one app/process.

(If you want the frontend/backend split instead — e.g. because you don't
want this UI process to hold OPENAI_API_KEY directly — swap the import
below back to `from api_client import ...` and deploy backend/ separately.
See README.md for that path.)

Flow (mirrors the original guided intake):
  1. Guided, one-question-at-a-time intake for the consumer's own details
     (name, address, city/postal, email, phone) — skippable per question or
     all at once.
  2. Complaint description -> classification, cited legal sections, filing
     authority, and a drafted letter.
  3. Optional: look up a shop/company's contact details, review/edit, then
     send — which is the human-in-the-loop confirmation gate; nothing sends
     without it.
"""

import sys
from pathlib import Path

# agents/ and config.py live one directory up from frontend/ — make sure
# they're importable regardless of the working directory Streamlit is
# launched from (Streamlit Cloud runs from the repo root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from local_agent_client import ApiError, analyze_complaint, check_health, lookup_company, send_letter

WIZARD_STEPS = [
    {"key": "user_name", "question": "First, what's your full name?", "placeholder": "e.g. Ayesha Khan"},
    {"key": "user_address", "question": "What's your address? (house/street, area)", "placeholder": "e.g. House 12, Street 5, Gulshan-e-Iqbal"},
    {"key": "user_city_postal", "question": "Which city, and postal code?", "placeholder": "e.g. Karachi, 75300"},
    {"key": "user_email", "question": "What's your email address?", "placeholder": "e.g. you@example.com"},
    {"key": "user_phone", "question": "Last one — what's your phone number?", "placeholder": "e.g. 0300-1234567"},
]

EXAMPLE_COMPLAINTS = [
    "I bought a washing machine two weeks ago and it stopped working. The shop refuses to repair or replace it.",
    "The shopkeeper never gave me a receipt when I bought my groceries.",
    "A restaurant advertised 50% off but charged me full price at checkout.",
    "An electrician I hired did such a bad wiring job that a socket started sparking.",
]

st.set_page_config(page_title="HaqDar — AI Consumer Rights Advisor", page_icon="🧾", layout="centered")


def _init_state():
    defaults = {
        "wizard_index": 0,
        "wizard_answers": {},
        "wizard_done": False,
        "analysis": None,          # last /api/complaint/analyze response (dict)
        "company_result": None,    # last /api/company/lookup response (dict)
        "shop_name": "",
        "shop_contact": "",
        "shop_address": "",
        "send_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_state()


def _user_details() -> dict:
    a = st.session_state.wizard_answers
    return {
        "user_name": a.get("user_name", ""),
        "user_address": a.get("user_address", ""),
        "user_city_postal": a.get("user_city_postal", ""),
        "user_email": a.get("user_email", ""),
        "user_phone": a.get("user_phone", ""),
    }


def _reset_wizard():
    st.session_state.wizard_index = 0
    st.session_state.wizard_done = False


def _start_over():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    _init_state()


st.title("HaqDar 🧾")
st.caption("AI Consumer Rights Advisor for Pakistani Consumers (Sindh)")
st.write(
    "Describe your consumer complaint below. HaqDar will identify your rights under the "
    "Sindh Consumer Protection Act 2014, draft a formal complaint letter, and tell you "
    "exactly where to file it."
)

if not check_health():
    st.warning(
        "⚠️ Something's misconfigured — the agent pipeline isn't reachable. Check that "
        "OPENAI_API_KEY is set in your environment or Streamlit secrets.",
        icon="⚠️",
    )

with st.sidebar:
    st.subheader("Session")
    if st.button("🔄 Start over", use_container_width=True):
        _start_over()
        st.rerun()

# ---------------------------------------------------------------------------
# Step 1: guided intake wizard
# ---------------------------------------------------------------------------
if not st.session_state.wizard_done:
    st.subheader("Let's get a few details first")
    st.caption(
        "I need a few details for the letter's sender block. You can skip any question — "
        "it'll show as a `[PLACEHOLDER]` in the letter for you to fill in by hand."
    )

    for step in WIZARD_STEPS[: st.session_state.wizard_index]:
        with st.chat_message("assistant"):
            st.write(step["question"])
        with st.chat_message("user"):
            answer = st.session_state.wizard_answers.get(step["key"], "")
            st.write(answer if answer else "_(skipped)_")

    if st.session_state.wizard_index < len(WIZARD_STEPS):
        current = WIZARD_STEPS[st.session_state.wizard_index]
        with st.chat_message("assistant"):
            st.write(current["question"])

        with st.form(key=f"wizard_form_{st.session_state.wizard_index}", clear_on_submit=True):
            answer = st.text_input(
                current["question"], placeholder=current["placeholder"], label_visibility="collapsed"
            )
            col1, col2 = st.columns([3, 2])
            next_clicked = col1.form_submit_button("Next →", use_container_width=True, type="primary")
            skip_all_clicked = col2.form_submit_button("Skip — fill in later", use_container_width=True)

        if next_clicked:
            st.session_state.wizard_answers[current["key"]] = answer.strip()
            st.session_state.wizard_index += 1
            st.rerun()

        if skip_all_clicked:
            st.session_state.wizard_index = len(WIZARD_STEPS)
            st.session_state.wizard_done = True
            st.rerun()
    else:
        st.session_state.wizard_done = True
        st.rerun()

# ---------------------------------------------------------------------------
# Step 2: complaint description + analysis
# ---------------------------------------------------------------------------
else:
    st.button("✏️ Edit my details", on_click=_reset_wizard)

    with st.expander("Need an example?"):
        for example in EXAMPLE_COMPLAINTS:
            if st.button(example, key=f"example_{hash(example)}", use_container_width=True):
                st.session_state["complaint_text"] = example
                st.rerun()

    complaint_text = st.text_area(
        "Describe your complaint",
        placeholder=EXAMPLE_COMPLAINTS[0],
        height=120,
        key="complaint_text",
    )

    analyze_clicked = st.button("Analyze My Complaint", type="primary")

    if analyze_clicked:
        if not complaint_text.strip():
            st.error("Please describe your complaint first.")
        else:
            with st.spinner("Classifying your complaint and drafting your letter…"):
                try:
                    st.session_state.analysis = analyze_complaint(complaint_text.strip(), _user_details())
                    st.session_state.send_result = None
                except ApiError as e:
                    st.error(f"Couldn't analyze your complaint: {e.detail}")
                    st.session_state.analysis = None

    analysis = st.session_state.analysis
    if analysis:
        if analysis.get("clarifying_question"):
            st.info(f"**I need a bit more detail:**\n\n{analysis['clarifying_question']}")
        else:
            issue_type = (analysis.get("issue_type") or "unknown").replace("_", " ").title()
            sections = analysis.get("cited_sections") or []
            sections_md = "\n".join(
                f"- **{s['source']} Section {s['section_no']}**: {s['title']}" for s in sections
            ) or "No sections retrieved."

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Classification & Legal Basis")
                st.markdown(f"**Issue classified as:** {issue_type}\n\n**Relevant sections:**\n{sections_md}")
            with col2:
                st.markdown("#### Where to File")
                authority = analysis.get("authority") or {}
                st.markdown(f"**Forum:** {authority.get('forum', 'N/A')}")
                st.markdown(f"**Process:** {authority.get('process', 'N/A')}")
                st.markdown(f"**Pre-requisite:** {authority.get('pre_requisite', 'N/A')}")
                location = authority.get("location") or {}
                if location.get("found"):
                    st.markdown(f"**Nearest Office:** {location.get('name', 'N/A')}")
                    st.markdown(f"📍 {location.get('address', 'N/A')}")
                    st.markdown(f"📞 {location.get('phone', 'Not listed')}")
                    if location.get("maps_link"):
                        st.markdown(f"[View on Map]({location['maps_link']})")
                elif location.get("reason"):
                    st.caption(f"(Location lookup unavailable: {location['reason']})")

            st.markdown("#### Draft Complaint Letter")
            st.text_area("Letter", value=analysis.get("letter_draft", ""), height=350, key="letter_display")

            # -----------------------------------------------------------------
            # Step 3: send to the shop
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("### Send this notice to the shop")
            st.caption(
                "Review the letter above first. Search for the shop's contact details, review what's "
                "found, then confirm before anything is sent — HaqDar never sends automatically."
            )

            company_name = st.text_input("Shop/Company name", placeholder="e.g. XYZ Electronics")
            if st.button("🔍 Find Contact Info"):
                if not company_name.strip():
                    st.warning("Please enter a company/shop name.")
                else:
                    with st.spinner("Searching for contact details…"):
                        try:
                            st.session_state.company_result = lookup_company(company_name.strip())
                            result = st.session_state.company_result
                            emails = result.get("candidate_emails") or []
                            address = result.get("address") or {}
                            st.session_state.shop_name = company_name.strip()
                            st.session_state.shop_contact = emails[0] if emails else ""
                            st.session_state.shop_address = address.get("address", "") if address.get("found") else ""
                        except ApiError as e:
                            st.error(f"Company lookup failed: {e.detail}")
                            st.session_state.company_result = None

            company_result = st.session_state.company_result
            if company_result:
                st.markdown(f"**Searched for:** {company_result.get('company_name', '')}")
                if company_result.get("search_error"):
                    st.warning(f"Web search error: {company_result['search_error']}")
                if company_result.get("website"):
                    st.markdown(f"**Website found:** {company_result['website']}")
                emails = company_result.get("candidate_emails") or []
                if emails:
                    st.markdown(f"**Candidate email(s):** {', '.join(emails)}")
                else:
                    st.markdown("**Candidate email(s):** none found — please enter manually below")
                address = company_result.get("address") or {}
                if address.get("found"):
                    st.markdown(f"**Address found:** {address['address']}")
                else:
                    st.markdown(f"**Address:** not found ({address.get('reason', 'n/a')})")
                st.caption(company_result.get("note", ""))
                st.caption("These are best-effort search results. Please verify the email and address are correct before sending.")

            shop_col1, shop_col2 = st.columns(2)
            with shop_col1:
                st.session_state.shop_name = st.text_input(
                    "Shop/Company name (confirm or edit)", value=st.session_state.shop_name
                )
            with shop_col2:
                st.session_state.shop_contact = st.text_input(
                    "Shop's email address (confirm or edit)",
                    value=st.session_state.shop_contact,
                    placeholder="shop@example.com",
                )
            st.session_state.shop_address = st.text_input(
                "Shop's address (confirm or edit)",
                value=st.session_state.shop_address,
                placeholder="e.g. Shop 12, XYZ Plaza, Shahrah-e-Faisal, Karachi",
            )

            if st.button("✅ Confirm & Send Notice via Email", type="primary"):
                if not st.session_state.shop_contact.strip():
                    st.warning("Please enter the shop's email address.")
                elif not st.session_state.shop_name.strip():
                    st.warning("Please enter the shop/company name.")
                else:
                    with st.spinner("Sending…"):
                        try:
                            st.session_state.send_result = send_letter(
                                letter_body=analysis.get("letter_body", ""),
                                issue_type=analysis.get("issue_type") or "consumer_complaint",
                                user_details=_user_details(),
                                shop_name=st.session_state.shop_name.strip(),
                                shop_address=st.session_state.shop_address.strip(),
                                shop_contact=st.session_state.shop_contact.strip(),
                            )
                        except ApiError as e:
                            st.session_state.send_result = {"sent": False, "reason": e.detail}

            send_result = st.session_state.send_result
            if send_result:
                if send_result.get("sent"):
                    st.success(f"✅ Notice emailed to {send_result.get('to')}.")
                else:
                    st.error(f"❌ Not sent — {send_result.get('reason', 'unknown error')}.")
                if send_result.get("final_letter"):
                    st.text_area("Final letter sent", value=send_result["final_letter"], height=300)

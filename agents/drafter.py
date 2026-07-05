"""
Node 3: Letter Drafter
Drafts the substantive body of a formal complaint letter, grounded ONLY in
the retrieved sections, to minimize hallucinated section numbers/citations.

IMPORTANT DESIGN NOTE: the LLM is deliberately NOT responsible for the
letter's header, recipient block, greeting, or signature. Earlier versions
asked the LLM to leave literal placeholders like [YOUR NAME] / [SHOP NAME]
for those parts, but this proved unreliable — for some complaints the model
invented its own bracket wording entirely (e.g. [Shopkeeper's Name],
[Shop Name], [Shop Address], a "Subject:" line, "Dear [Shopkeeper's Name],")
instead of the instructed format. Chasing every new placeholder wording the
LLM might invent is not sustainable.

Instead: the LLM only ever writes the substantive legal content (the body).
Everything structural — sender block, date, recipient block, greeting,
signature — is built deterministically in Python via assemble_letter(),
using whatever consumer/shop details are in state, falling back to a fixed,
predictable [PLACEHOLDER] token per field if that detail isn't known yet.
This guarantees the structure is byte-for-byte consistent on every run,
regardless of what the LLM does.
"""

from datetime import date
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from agents.llm import llm
from agents.state import HaqDarState

DRAFTER_SYSTEM_PROMPT = """You are drafting the BODY of a formal consumer complaint letter under
the Sindh Consumer Protection Act, 2014 (Pakistan). You are NOT writing the letter's header,
recipient address, greeting ("Dear..."), or signature — those are added separately by the
application. Write ONLY the paragraphs that go between the greeting and the signature.

STRICT RULES:
1. Only cite section numbers that appear in the "AVAILABLE SECTIONS" list below. Never invent a section number.
2. Each available section is tagged with a role: "liability", "notice", "filing", or "remedy".
   You MUST use sections only for their tagged role — never substitute one role for another:
   - "liability" sections: cite these to explain WHY the product/service is defective (the legal basis of the complaint).
   - "notice" section: cite this ONLY for the statement that this letter itself is a formal 15-day notice.
   - "filing" section: cite this ONLY if/when describing how a claim would be filed with the Consumer Court.
     Do NOT cite the "remedy" section for filing — filing and remedy are different sections with different roles.
   - "remedy" section: cite this ONLY to describe what the Consumer Court can order AFTER a claim is filed
     (e.g. repair, replacement, refund, damages) — never as the mechanism for filing.
3. Write in formal but plain English, suitable for a layperson to send to a business.
4. Structure of the BODY only: (a) description of the issue, (b) the specific legal provisions violated
   (cite "liability" section numbers), (c) the remedy being demanded, (d) a statement that this letter is a
   formal notice under the "notice" section, giving the recipient 15 days to respond, (e) a warning that
   failure to resolve may lead to a claim filed under the "filing" section, at which point the Consumer
   Court may order the outcomes described in the "remedy" section.
5. Do NOT write a "To,", "Dear...,", "Subject:", "Sincerely," or any sender/recipient name, address, date,
   or contact detail, in any form — not even as a placeholder. Refer to the recipient only as "you" or
   "your shop"/"your business" within the body text if needed. The application adds all of that separately.
6. Do not include markdown headers or a letter title. Just the plain body paragraphs.
7. Keep it under 280 words (shorter than before, since the header/signature are no longer part of your output).
"""


def _field_or_placeholder(value: Optional[str], placeholder: str) -> str:
    value = (value or "").strip()
    return value if value else placeholder


def assemble_letter(body: str, state: HaqDarState) -> str:
    """
    Deterministically builds the full letter (sender block, date, recipient
    block, subject, greeting, body, signature) from state. Called twice in
    practice: once right after drafting (shop name/address usually still
    unknown, so they render as placeholders) and again right before sending
    (once the consumer has confirmed the shop's details) — both calls just
    re-run this same function with an updated state, so there's no fragile
    text substitution involved, only a fresh deterministic build each time.
    """
    sender_lines = [
        _field_or_placeholder(state.get("user_name"), "[YOUR NAME]"),
        _field_or_placeholder(state.get("user_address"), "[ADDRESS]"),
        _field_or_placeholder(state.get("user_city_postal"), "[CITY, POSTAL CODE]"),
        _field_or_placeholder(state.get("user_email"), "[EMAIL]"),
        _field_or_placeholder(state.get("user_phone"), "[PHONE NUMBER]"),
    ]

    date_line = date.today().strftime("%B %d, %Y")

    shop_name = _field_or_placeholder(state.get("shop_name"), "[SHOP NAME]")
    shop_address = _field_or_placeholder(state.get("shop_address"), "[SHOP ADDRESS]")
    recipient_lines = ["To,", "The Management", shop_name, shop_address]

    issue_type = (state.get("issue_type") or "consumer_complaint").replace("_", " ").title()
    subject_line = f"Subject: Formal Consumer Complaint — {issue_type}"

    signoff_name = _field_or_placeholder(state.get("user_name"), "[YOUR NAME]")

    parts = [
        "\n".join(sender_lines),
        date_line,
        "",
        "\n".join(recipient_lines),
        "",
        subject_line,
        "",
        "Dear Sir/Madam,",
        "",
        body.strip(),
        "",
        "Sincerely,",
        signoff_name,
    ]
    return "\n".join(parts)


def draft_letter(state: HaqDarState) -> HaqDarState:
    complaint = state["complaint_text"]
    sections = state.get("retrieved_sections", [])
    reflection_notes = state.get("reflection_notes", "")

    sections_text = "\n\n".join(
        f"Section {s['section_no']} ({s['source']}) - {s['title']} [role: {s.get('role', 'liability')}]:\n{s['text']}"
        for s in sections
    )

    user_content = f"""CONSUMER COMPLAINT:
{complaint}

AVAILABLE SECTIONS (cite only from these):
{sections_text}
"""

    if reflection_notes:
        user_content += f"\n\nPREVIOUS DRAFT WAS REJECTED. Reviewer notes to fix:\n{reflection_notes}"

    response = llm.invoke([
        SystemMessage(content=DRAFTER_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])

    body = response.content.strip()
    letter = assemble_letter(body, state)

    return {
        **state,
        "letter_body": body,
        "letter_draft": letter,
    }
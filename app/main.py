import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gradio as gr
from agents.graph import haqdar_graph
from agents.tracing import invoke_traced
from agents.company_lookup import search_company_contact
from agents.delivery_node import send_email_notice
from agents.drafter import assemble_letter


def _format_authority_md(authority: dict) -> str:
    authority_md = f"""**Forum:** {authority.get('forum', 'N/A')}

**Process:** {authority.get('process', 'N/A')}

**Pre-requisite:** {authority.get('pre_requisite', 'N/A')}"""

    location = authority.get("location", {})
    if location.get("found"):
        authority_md += f"""

**Nearest Office:** {location.get('name', 'N/A')}
📍 {location.get('address', 'N/A')}
📞 {location.get('phone', 'Not listed')}
[View on Map]({location.get('maps_link', '#')})"""
    elif location.get("reason"):
        authority_md += f"\n\n*(Location lookup unavailable: {location['reason']})*"

    return authority_md


def process_complaint(
    complaint_text: str,
    user_name: str,
    user_address: str,
    user_city_postal: str,
    user_email: str,
    user_phone: str,
):
    if not complaint_text.strip():
        return "Please describe your complaint.", "", "", gr.update(visible=False), {}

    result = invoke_traced(haqdar_graph, {
        "complaint_text": complaint_text,
        "user_name": user_name,
        "user_address": user_address,
        "user_city_postal": user_city_postal,
        "user_email": user_email,
        "user_phone": user_phone,
    })

    if result.get("clarifying_question"):
        return (
            f"**I need a bit more detail:**\n\n{result['clarifying_question']}",
            "",
            "",
            gr.update(visible=False),
            {},
        )

    final = result.get("final_output", {})

    issue_type = final.get("issue_type", "unknown")
    issue_type_title = issue_type.replace("_", " ").title()
    sections = final.get("cited_sections", [])
    sections_md = "\n".join(
        f"- **{s['source']} Section {s['section_no']}**: {s['title']}" for s in sections
    ) or "No sections retrieved."

    authority = final.get("authority", {})
    authority_md = _format_authority_md(authority)

    letter = final.get("letter_draft", "No draft generated.")
    body = result.get("letter_body", "")

    classification_md = f"**Issue classified as:** {issue_type_title}\n\n**Relevant sections:**\n{sections_md}"

    # Stash everything needed to REBUILD the letter later (once the shop's
    # name/address are known) via assemble_letter() — not just the finished
    # text. This is what lets the recipient block be regenerated
    # deterministically at send time instead of relying on fragile string
    # substitution into whatever the LLM happened to write.
    send_state = {
        "letter_body": body,
        "issue_type": issue_type,
        "user_name": user_name,
        "user_address": user_address,
        "user_city_postal": user_city_postal,
        "user_email": user_email,
        "user_phone": user_phone,
    }

    return classification_md, letter, authority_md, gr.update(visible=True), send_state


def lookup_company(company_name: str):
    if not company_name.strip():
        return "Please enter a company/shop name.", "", "", ""

    result = search_company_contact(company_name.strip())

    if result.get("error"):
        return result["error"], "", "", ""

    emails = result.get("candidate_emails", [])
    address = result.get("address", {})

    summary_lines = [f"**Searched for:** {result['company_name']}"]
    if result.get("search_error"):
        summary_lines.append(f"⚠️ **Web search error:** {result['search_error']}")
    if result.get("website"):
        summary_lines.append(f"**Website found:** {result['website']}")
    if emails:
        summary_lines.append(f"**Candidate email(s):** {', '.join(emails)}")
    else:
        summary_lines.append("**Candidate email(s):** none found — please enter manually below")
    if address.get("found"):
        summary_lines.append(f"**Address found:** {address['address']}")
    else:
        summary_lines.append(f"**Address:** not found ({address.get('reason', 'n/a')})")
    summary_lines.append(f"\n*{result.get('note', '')}*")

    summary_md = "\n\n".join(summary_lines)

    # Pre-fill the editable fields, but the user must still hit Send themselves
    prefill_email = emails[0] if emails else ""
    prefill_address = address.get("address", "") if address.get("found") else ""

    return summary_md, prefill_email, company_name.strip(), prefill_address


def send_letter(shop_name: str, shop_contact: str, shop_address: str, send_state: dict):
    if not shop_contact.strip():
        return "⚠️ Please enter the shop's email address.", gr.update()
    if not shop_name.strip():
        return "⚠️ Please enter the shop/company name.", gr.update()

    body = send_state.get("letter_body", "")
    if not body:
        return "⚠️ No draft letter available to send. Analyze a complaint first.", gr.update()

    # Rebuild the FULL letter now that the shop's name/address are known,
    # by re-running the same deterministic assemble_letter() used at draft
    # time — not by trying to text-substitute into whatever the LLM wrote.
    # This is what guarantees the recipient block is always correct and
    # consistent, regardless of what shape the LLM's body text took.
    rebuild_state = {
        **send_state,
        "shop_name": shop_name.strip(),
        "shop_address": shop_address.strip(),
    }
    final_letter = assemble_letter(body, rebuild_state)

    
    result = send_email_notice(
        to_email=shop_contact.strip(),
        letter_text=final_letter,
        shop_name=shop_name.strip(),
    )

    if result.get("sent"):
        return f"✅ Notice emailed to {result.get('to')}.", final_letter
    return f"❌ Not sent — {result.get('reason', 'unknown error')}.", final_letter


WIZARD_STEPS = [
    {
        "key": "user_name",
        "question": "First, what's your full name?",
        "placeholder": "e.g. Ayesha Khan",
    },
    {
        "key": "user_address",
        "question": "What's your address? (house/street, area)",
        "placeholder": "e.g. House 12, Street 5, Gulshan-e-Iqbal",
    },
    {
        "key": "user_city_postal",
        "question": "Which city, and postal code?",
        "placeholder": "e.g. Karachi, 75300",
    },
    {
        "key": "user_email",
        "question": "What's your email address?",
        "placeholder": "e.g. you@example.com",
    },
    {
        "key": "user_phone",
        "question": "Last one — what's your phone number?",
        "placeholder": "e.g. 0300-1234567",
    },
]


def _new_wizard_state():
    return {"index": 0, "answers": {}}


def _build_chat_md(state: dict) -> str:
    lines = ["**HaqDar:** Before I draft your letter, I need a few details for the sender block. "
             "You can skip any question — it'll show as a `[PLACEHOLDER]` in the letter for you to fill in by hand."]
    for step in WIZARD_STEPS[: state["index"]]:
        answer = state["answers"].get(step["key"], "")
        lines.append(f"\n**HaqDar:** {step['question']}")
        lines.append(f"**You:** {answer if answer else '_(skipped)_'}")
    return "\n".join(lines)


def wizard_start():
    state = _new_wizard_state()
    chat_md = _build_chat_md(state)
    first_q = WIZARD_STEPS[0]
    return (
        state,
        chat_md,
        gr.update(value="", label=first_q["question"], placeholder=first_q["placeholder"], visible=True),
        gr.update(visible=True),   # wizard_group
        gr.update(visible=False),  # complaint_group
    )


def wizard_advance(answer: str, state: dict):
    """Record the current answer (possibly blank if skipped) and move to the next question,
    or finish the wizard and reveal the complaint section once all steps are done."""
    if state is None:
        state = _new_wizard_state()

    idx = state["index"]
    if idx < len(WIZARD_STEPS):
        state["answers"][WIZARD_STEPS[idx]["key"]] = (answer or "").strip()
        state["index"] += 1

    chat_md = _build_chat_md(state)

    if state["index"] < len(WIZARD_STEPS):
        next_q = WIZARD_STEPS[state["index"]]
        return (
            state,
            chat_md,
            gr.update(value="", label=next_q["question"], placeholder=next_q["placeholder"]),
            gr.update(visible=True),   # wizard_group stays open
            gr.update(visible=False),  # complaint_group stays hidden
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),  # hidden fields untouched
        )

    # All questions answered — reveal the complaint box, populate hidden fields
    answers = state["answers"]
    chat_md += "\n\n**HaqDar:** Got it, thanks! ✅ Now tell me about your complaint below."
    return (
        state,
        chat_md,
        gr.update(),
        gr.update(visible=False),  # hide wizard_group
        gr.update(visible=True),   # show complaint_group
        gr.update(value=answers.get("user_name", "")),
        gr.update(value=answers.get("user_address", "")),
        gr.update(value=answers.get("user_city_postal", "")),
        gr.update(value=answers.get("user_email", "")),
        gr.update(value=answers.get("user_phone", "")),
    )


def wizard_skip_all():
    """Skip the whole intake — go straight to the complaint box with blank sender details."""
    state = _new_wizard_state()
    state["index"] = len(WIZARD_STEPS)
    chat_md = "**HaqDar:** No problem — you can fill your details in later. Tell me about your complaint below."
    return (
        state,
        chat_md,
        gr.update(visible=False),
        gr.update(visible=False),  # hide wizard_group
        gr.update(visible=True),   # show complaint_group
        gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=""),
    )


def wizard_restart():
    """Let the user re-open the guided intake to edit their details."""
    return wizard_start()


with gr.Blocks(title="HaqDar — AI Consumer Rights Advisor") as demo:
    gr.Markdown("# HaqDar 🧾\n### AI Consumer Rights Advisor for Pakistani Consumers (Sindh)")
    gr.Markdown(
        "Describe your consumer complaint below. HaqDar will identify your rights under the "
        "Sindh Consumer Protection Act 2014, draft a formal complaint letter, and tell you "
        "exactly where to file it."
    )

    wizard_state = gr.State(_new_wizard_state())

    # Hidden fields — populated by the wizard once the user finishes answering.
    # These are what actually feed process_complaint(); they're never shown directly.
    user_name_input = gr.Textbox(visible=False)
    user_address_input = gr.Textbox(visible=False)
    user_city_postal_input = gr.Textbox(visible=False)
    user_email_input = gr.Textbox(visible=False)
    user_phone_input = gr.Textbox(visible=False)

    with gr.Group(visible=True) as wizard_group:
        wizard_chat_md = gr.Markdown(_build_chat_md(_new_wizard_state()))
        with gr.Row():
            wizard_input = gr.Textbox(
                label=WIZARD_STEPS[0]["question"],
                placeholder=WIZARD_STEPS[0]["placeholder"],
                show_label=True,
                scale=4,
            )
            wizard_next_btn = gr.Button("Next →", variant="primary", scale=1)
        wizard_skip_btn = gr.Button("Skip — I'll fill my details in later", variant="secondary", size="sm")

    with gr.Group(visible=False) as complaint_group:
        edit_details_btn = gr.Button("✏️ Edit my details", size="sm")
        with gr.Row():
            complaint_input = gr.Textbox(
                label="Describe your complaint",
                placeholder="e.g. I bought a washing machine two weeks ago and it stopped working. The shop refuses to repair or replace it.",
                lines=4,
            )

        submit_btn = gr.Button("Analyze My Complaint", variant="primary")

        with gr.Row():
            with gr.Column():
                classification_output = gr.Markdown(label="Classification & Legal Basis")
            with gr.Column():
                authority_output = gr.Markdown(label="Where to File")

        letter_output = gr.Textbox(label="Draft Complaint Letter", lines=15)

    send_state = gr.State({})

    with gr.Group(visible=False) as send_group:
        gr.Markdown(
            "### Send this notice to the shop\n"
            "Review the letter above first. Enter the shop/company name to search for its "
            "contact details, review what's found, then confirm before anything is sent — "
            "HaqDar never sends automatically. Once confirmed, the letter above is rebuilt "
            "with the shop's name and address filled in automatically before sending."
        )

        with gr.Row():
            company_search_input = gr.Textbox(
                label="Shop/Company name",
                placeholder="e.g. XYZ Electronics",
            )
            search_btn = gr.Button("🔍 Find Contact Info", variant="secondary")

        search_result_md = gr.Markdown()

        with gr.Row():
            shop_name_input = gr.Textbox(
                label="Shop/Company name (confirm or edit)",
            )
            shop_contact_input = gr.Textbox(
                label="Shop's email address (confirm or edit)",
                placeholder="shop@example.com",
            )
        shop_address_input = gr.Textbox(
            label="Shop's address (confirm or edit)",
            placeholder="e.g. Shop 12, XYZ Plaza, Shahrah-e-Faisal, Karachi",
        )

        send_btn = gr.Button("✅ Confirm & Send Notice via Email", variant="primary")
        send_status = gr.Markdown()

    wizard_hidden_field_outputs = [
        user_name_input,
        user_address_input,
        user_city_postal_input,
        user_email_input,
        user_phone_input,
    ]

    wizard_next_btn.click(
        fn=wizard_advance,
        inputs=[wizard_input, wizard_state],
        outputs=[wizard_state, wizard_chat_md, wizard_input, wizard_group, complaint_group, *wizard_hidden_field_outputs],
    )

    wizard_input.submit(
        fn=wizard_advance,
        inputs=[wizard_input, wizard_state],
        outputs=[wizard_state, wizard_chat_md, wizard_input, wizard_group, complaint_group, *wizard_hidden_field_outputs],
    )

    wizard_skip_btn.click(
        fn=wizard_skip_all,
        inputs=[],
        outputs=[wizard_state, wizard_chat_md, wizard_input, wizard_group, complaint_group, *wizard_hidden_field_outputs],
    )

    edit_details_btn.click(
        fn=wizard_restart,
        inputs=[],
        outputs=[wizard_state, wizard_chat_md, wizard_input, wizard_group, complaint_group],
    )

    submit_btn.click(
        fn=process_complaint,
        inputs=[
            complaint_input,
            user_name_input,
            user_address_input,
            user_city_postal_input,
            user_email_input,
            user_phone_input,
        ],
        outputs=[classification_output, letter_output, authority_output, send_group, send_state],
    )

    search_btn.click(
        fn=lookup_company,
        inputs=[company_search_input],
        outputs=[search_result_md, shop_contact_input, shop_name_input, shop_address_input],
    )

    send_btn.click(
        fn=send_letter,
        inputs=[shop_name_input, shop_contact_input, shop_address_input, send_state],
        outputs=[send_status, letter_output],
    )

    gr.Examples(
        examples=[
            "I bought a washing machine two weeks ago and it stopped working. The shop refuses to repair or replace it.",
            "The shopkeeper never gave me a receipt when I bought my groceries.",
            "A restaurant advertised 50% off but charged me full price at checkout.",
            "An electrician I hired did such a bad wiring job that a socket started sparking.",
        ],
        inputs=[complaint_input],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)

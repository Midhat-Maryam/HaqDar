"""
Shared state object passed between LangGraph nodes.
"""

from typing import TypedDict, Optional


class HaqDarState(TypedDict, total=False):
    complaint_text: str              # raw user input
    issue_type: str                  # classifier output: defective_product | defective_service | unfair_deceptive_practice | pricing_receipt_disclosure | unclear
    classification_confidence: str   # "high" | "low" — drives supervisor routing
    clarifying_question: Optional[str]  # set if classifier needs more info

    retrieved_sections: list[dict]   # from legal_retrieval node

    letter_draft: str                # FULL assembled letter (header + body + signoff) — see drafter.py's assemble_letter()
    letter_body: str                 # LLM-generated substantive content ONLY — no header/greeting/signoff.
                                      # Kept separate so the recipient block can be rebuilt deterministically
                                      # once the shop name/address is known, without touching the legal content.
    reflection_notes: str            # from reflection node
    reflection_passed: bool          # whether reflection approved the draft
    reflection_loop_count: int       # guards against infinite loops

    authority_info: dict             # from authority_router node (now includes nested "location")
    final_output: dict               # assembled final response for the UI

    shop_contact: Optional[str]      # consumer-provided shop email address
    shop_name: Optional[str]         # consumer-provided company/shop name — used in the recipient block, email subject
    shop_address: Optional[str]      # consumer-provided/looked-up shop address — used in the recipient block
    send_confirmed: bool             # human-in-the-loop gate before any email send
    delivery_status: Optional[dict]  # result of the email send attempt

    # Consumer's own details, collected once via the UI and used to build the
    # letter's sender block and signature deterministically (not via LLM) —
    # see drafter.py's assemble_letter(). Any field left blank renders as its
    # own [PLACEHOLDER] in the assembled letter, same as before.
    user_name: Optional[str]
    user_address: Optional[str]
    user_city_postal: Optional[str]
    user_email: Optional[str]
    user_phone: Optional[str]
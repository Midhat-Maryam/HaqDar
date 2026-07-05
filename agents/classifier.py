"""
Node 1: Intake / Classifier
Reads the raw complaint and classifies it into one of the routing categories
used by authority_routing in the dataset.
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from agents.llm import llm
from agents.state import HaqDarState

CLASSIFIER_SYSTEM_PROMPT = """You are an intake classifier for a Pakistani consumer rights advisor.
Classify the consumer's complaint into exactly one of these categories:

- defective_product: physical goods that are broken, faulty, unsafe, or don't match specifications
- defective_service: a service (repair, contractor, professional) that was faulty, substandard, or unqualified
- unfair_deceptive_practice: false advertising, fake discounts, bait-and-switch, misleading claims
- pricing_receipt_disclosure: no price displayed, no receipt given, undisclosed return policy
- unclear: the complaint is too vague to classify confidently

Respond ONLY with valid JSON, no markdown, no preamble:
{"issue_type": "<category>", "confidence": "high" or "low", "clarifying_question": "<question if unclear, else null>"}
"""


def classify_complaint(state: HaqDarState) -> HaqDarState:
    complaint = state["complaint_text"]

    response = llm.invoke([
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=complaint),
    ])

    try:
        parsed = json.loads(response.content.strip().strip("```json").strip("```"))
    except json.JSONDecodeError:
        parsed = {"issue_type": "unclear", "confidence": "low",
                   "clarifying_question": "Could you describe what happened in more detail?"}

    return {
        **state,
        "issue_type": parsed.get("issue_type", "unclear"),
        "classification_confidence": parsed.get("confidence", "low"),
        "clarifying_question": parsed.get("clarifying_question"),
    }

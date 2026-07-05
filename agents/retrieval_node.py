"""
Node 2: Legal Retrieval (tool node)
Queries the ChromaDB knowledge base for sections relevant to the complaint.

IMPORTANT: retrieval is scoped by the classifier's issue_type BEFORE any
semantic search happens. scpa_dataset.json already contains a curated,
correct mapping of issue_type -> relevant_sections (see authority_routing
in the dataset) — e.g. "defective_product" maps only to act_s4-act_s10.
That curated list is the source of truth for *which sections are even
eligible to be cited*. Pure semantic (TF-IDF) search across the entire
Act — including Rules, filing procedure, and court-order sections like
s.26/s.29/s.32 — was previously being run with no issue_type filter,
which is how a "defective_product" complaint could surface s.32 (Order
of Consumer Court, a remedy-stage section) and get mis-cited by the
drafter as if it were the filing mechanism.

Semantic search is still used, but only (a) to rank/trim within the
curated candidate pool, and (b) as a fallback if the classifier was
"unclear" or low-confidence, in which case we search the full corpus
like before.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.retriever import retrieve_sections
from agents.state import HaqDarState
from config import DATASET_PATH

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    _dataset = json.load(f)

_ROUTING = _dataset["authority_routing"]
_ALL_SECTIONS_BY_ID = {s["id"]: s for s in _dataset["act_sections"]}
_ALL_SECTIONS_BY_ID.update({s["id"]: s for s in _dataset["rules_sections"]})

# Always eligible regardless of issue_type: the pre-suit notice requirement
# and the actual filing mechanism. These are procedural, not defect-type-specific,
# so every complaint that reaches the drafting stage needs them available —
# but tagged with their procedural role so the drafter doesn't conflate them.
_PROCEDURAL_SECTIONS = {
    "notice": "act_s29",   # Settlement of Claims — mandatory pre-suit notice, 15-day reply window
    "filing": "act_s26",   # Filing of Claims — this is how you actually file, NOT act_s32
    "remedy": "act_s32",   # Order of Consumer Court — what the court can order AFTER filing
}


def _section_with_role(section_id: str, role: str) -> dict | None:
    sec = _ALL_SECTIONS_BY_ID.get(section_id)
    if not sec:
        return None
    return {
        "section_no": sec["section_no"],
        "source": "Act" if section_id.startswith("act_") else "Rules",
        "title": sec["title"],
        "part": sec["part"],
        "text": sec["text"],
        "role": role,  # "liability" | "notice" | "filing" | "remedy"
    }


def retrieve_legal_sections(state: HaqDarState) -> HaqDarState:
    complaint = state["complaint_text"]
    issue_type = state.get("issue_type", "unclear")
    confidence = state.get("classification_confidence", "low")

    curated_ids = _ROUTING.get(issue_type, {}).get("relevant_sections", [])

    if curated_ids and confidence == "high":
        # Use the curated, issue_type-scoped pool as the liability sections.
        sections = [
            _section_with_role(sid, "liability")
            for sid in curated_ids
            if _section_with_role(sid, "liability")
        ]
    else:
        # Classifier was unclear/low-confidence — fall back to full-corpus
        # semantic search rather than guessing a curated pool.
        raw = retrieve_sections(complaint, top_k=4)
        sections = [{**s, "role": "liability"} for s in raw]

    # Always attach the three procedural sections with explicit roles, so the
    # drafter prompt can require "cite act_s26 for filing, never act_s32 for filing."
    for role, sid in _PROCEDURAL_SECTIONS.items():
        sec = _section_with_role(sid, role)
        if sec and not any(s["section_no"] == sec["section_no"] and s["role"] == role for s in sections):
            sections.append(sec)

    return {
        **state,
        "retrieved_sections": sections,
    }
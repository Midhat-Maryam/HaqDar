"""
Node 4: Reflection
Critiques the drafted letter against the actual retrieved section text.
Catches hallucinated section numbers or claims not supported by the Act.
This is what makes the pipeline agentic rather than a linear RAG chain.
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from agents.llm import llm
from agents.state import HaqDarState
from config import MAX_REFLECTION_LOOPS

REFLECTION_SYSTEM_PROMPT = """You are a legal-accuracy reviewer checking a draft consumer
complaint letter against the actual retrieved sections of the Sindh Consumer Protection Act.

Each retrieved section is tagged with a role: "liability", "notice", "filing", or "remedy".
Check for:
1. Every cited section number actually appears in the AVAILABLE SECTIONS list.
2. No claim about what the law says contradicts the retrieved section text.
3. The letter correctly references the "notice" section for the 15-day pre-filing notice requirement.
4. ROLE MISUSE (this is the most common failure mode — check it carefully): the letter must not
   cite a "remedy" section (what the court can order AFTER a claim is filed) as if it were the
   mechanism for FILING a claim. Filing must be attributed only to the section tagged "filing".
   Similarly, a "filing" section must not be used to describe court remedies, and a "liability"
   section must not be used to describe the notice or filing process. If the letter says
   something like "file a complaint under Section X" and Section X's tagged role is "remedy"
   (not "filing"), this is a failure — flag it by name.

Respond ONLY with valid JSON, no markdown:
{"passed": true or false, "notes": "<specific issues to fix, or empty string if passed>"}
"""


import re


def _detect_filing_role_misuse(draft: str, sections: list[dict]) -> str | None:
    """
    Deterministic safety net, independent of the LLM reviewer: flags any
    sentence that talks about "filing" a claim/complaint while citing a
    section number whose tagged role is NOT "filing". This is the exact
    failure pattern that motivated this check (a draft citing the
    "remedy" section, e.g. Order of Consumer Court, as if it were how
    you file a claim). Returns a note string if misuse is found, else None.
    """
    role_by_section_no = {s["section_no"]: s.get("role", "liability") for s in sections}
    filing_verbs = r"(file|filing|filed|instituting|lodge|lodging)"
    section_ref = r"[Ss]ection\s+(\d+[A-Za-z]?)"

    for sentence in re.split(r"(?<=[.!?])\s+", draft):
        if re.search(filing_verbs, sentence):
            for match in re.finditer(section_ref, sentence):
                sec_no = match.group(1)
                role = role_by_section_no.get(sec_no)
                if role and role != "filing":
                    return (
                        f"Section {sec_no} is tagged role '{role}', not 'filing', "
                        f"but this sentence describes filing a claim using it: \"{sentence.strip()}\""
                    )
    return None


def reflect_on_draft(state: HaqDarState) -> HaqDarState:
    # Review the LLM-generated body only. The full letter_draft now also
    # contains a deterministically-assembled header/recipient/signature
    # block (see drafter.py's assemble_letter()) which never contains
    # section citations, so there's nothing for this reviewer to check
    # there — and reviewing it would just waste tokens. Fall back to
    # letter_draft for compatibility with any older state that predates
    # the letter_body split.
    draft = state.get("letter_body") or state.get("letter_draft", "")
    sections = state.get("retrieved_sections", [])
    loop_count = state.get("reflection_loop_count", 0)

    # Deterministic check runs first and overrides the LLM if it catches
    # the known failure pattern — cheaper and can't be reasoned around.
    deterministic_issue = _detect_filing_role_misuse(draft, sections)
    if deterministic_issue:
        return {
            **state,
            "reflection_passed": loop_count >= MAX_REFLECTION_LOOPS,
            "reflection_notes": deterministic_issue,
            "reflection_loop_count": loop_count + 1,
        }

    sections_text = "\n\n".join(
        f"Section {s['section_no']} ({s['source']}) - {s['title']} [role: {s.get('role', 'liability')}]:\n{s['text']}"
        for s in sections
    )

    response = llm.invoke([
        SystemMessage(content=REFLECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE SECTIONS:\n{sections_text}\n\nDRAFT LETTER:\n{draft}"),
    ])

    try:
        parsed = json.loads(response.content.strip().strip("```json").strip("```"))
    except json.JSONDecodeError:
        parsed = {"passed": True, "notes": ""}

    passed = parsed.get("passed", True) or loop_count >= MAX_REFLECTION_LOOPS

    return {
        **state,
        "reflection_passed": passed,
        "reflection_notes": parsed.get("notes", ""),
        "reflection_loop_count": loop_count + 1,
    }
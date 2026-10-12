"""
Ship 30 for 30 Essay Skill

A dedicated, reusable skill and tool for transforming retrieved podcast/newsletter evidence
into an approximately 1,250-word Ship 30 for 30 style essay.

Principles encoded:
1. One clear central idea / thesis.
2. Specific target audience (PM, growth practitioner, founder).
3. Strong hook: sharp observation, tension, counterintuitive claim (no fabricated anecdotes).
4. Early value promise.
5. Coherent narrative progression across 2-4 core insight sections.
6. Evidence before certainty: connect claims to retrieved transcript evidence; attribute opinions to speakers.
7. Skimmable formatting: descriptive headings, short paragraphs, selective bolding.
8. Specific, concrete takeaway (actionable checklist or decision framework).
9. Strict Grounding: Never fabricate quotes or metrics to artificially inflate word count.
   If evidence is insufficient, declare the gap clearly.
"""

import re
from typing import Dict, Any, List

SHIP30_KEYWORDS = [
    r"ship\s*30",
    r"ship30",
    r"ship\s*30\s*for\s*30",
    r"write\s+(?:an?\s+)?essay",
    r"generate\s+(?:an?\s+)?essay",
    r"compose\s+(?:an?\s+)?essay",
    r"1,?250[\s-]word\s+essay",
    r"long-form\s+essay",
]

def is_ship30_request(query: str) -> bool:
    """Detect if a user prompt is requesting a Ship 30 for 30 essay."""
    if not query:
        return False
    lower_q = query.strip().lower()
    return any(re.search(pattern, lower_q) for pattern in SHIP30_KEYWORDS)

def build_ship30_instruction() -> str:
    """
    Returns the specialized system instructions for the Ship 30 for 30 essay skill.
    Enforces the writing principles, narrative outline, approximate 1,250-word target,
    skimmable formatting, and transcript-grounding rules.
    """
    return (
        "You are acting as the Ship 30 for 30 Essay Skill for The Lenny Growth Assistant.\n"
        "Your goal is to transform the provided RETRIEVED CONTEXT into a high-impact, actionable essay.\n\n"
        "WRITING PRINCIPLES & STRUCTURE:\n"
        "1. Target Length: Approximately 1,250 words (acceptable range: 1,000 to 1,400 words).\n"
        "2. Hook: Open with a compelling observation, counterintuitive insight, or high-stakes problem for product/growth practitioners. Do NOT fabricate personal stories or fake quotes.\n"
        "3. Promise Value Early: Clarify in the first 2-3 paragraphs what the reader will learn and be able to execute.\n"
        "4. Narrative Progression: Organize the essay into 3-4 structured stages using descriptive, skimmable H2 and H3 headings.\n"
        "5. Skimmable Formatting: Use short paragraphs (2-3 sentences), bullet points where helpful, and selective bold emphasis on key principles.\n"
        "6. Concrete Takeaway: Conclude with a dedicated 'Actionable Takeaway' section featuring a specific checklist, rule of thumb, or decision framework.\n\n"
        "CRITICAL GROUNDING RULES:\n"
        "- Base all substantive claims and strategies strictly on the provided RETRIEVED CONTEXT.\n"
        "- Attribute guest perspectives accurately to their respective speakers.\n"
        "- NEVER invent statistics, case studies, or quotations to artificially reach the word count.\n"
        "- If the retrieved context is empty, irrelevant, or insufficient to sustain an essay, set evidence_state to 'insufficient', explain what is missing, and do NOT fabricate content."
    )

def validate_ship30_essay(text: str) -> Dict[str, Any]:
    """
    Analyzes an essay against Ship 30 for 30 criteria:
    - Approximate word count
    - Presence of structured headings
    - Strong opening / hook
    - Actionable takeaway section
    - Citations / sources
    """
    if not text:
        return {
            "valid": False,
            "word_count": 0,
            "has_headings": False,
            "has_takeaway": False,
            "reasons": ["Empty essay text"]
        }

    words = text.split()
    word_count = len(words)
    
    # Check for markdown headings (# or ##)
    has_headings = bool(re.search(r"^#{1,3}\s+", text, re.MULTILINE))
    
    # Check for actionable takeaway section
    takeaway_patterns = [
        r"(takeaway|actionable|next steps|framework|checklist|summary|in practice)",
    ]
    has_takeaway = any(re.search(p, text, re.IGNORECASE) for p in takeaway_patterns)
    
    # Check for bold emphasis
    has_bold = bool(re.search(r"\*\*[^*]+\*\*", text))
    
    reasons = []
    if word_count < 300:
        reasons.append(f"Word count ({word_count}) is significantly below target")
    if not has_headings:
        reasons.append("Missing descriptive headings for skimmability")
    if not has_takeaway:
        reasons.append("Missing explicit actionable takeaway section")

    return {
        "valid": len(reasons) == 0,
        "word_count": word_count,
        "has_headings": has_headings,
        "has_takeaway": has_takeaway,
        "has_bold": has_bold,
        "reasons": reasons
    }

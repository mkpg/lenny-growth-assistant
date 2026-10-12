import re
from dataclasses import dataclass
from typing import List, Dict

# Mapping of smart quotes to straight quotes
SMART_QUOTE_MAP = {
    "\u201c": '"', "\u201d": '"',
    "\u2018": "'", "\u2019": "'",
    "\u00ab": '"', "\u00bb": '"',
    "\u201e": '"', "\u2022": '"',
}

def _normalize(text: str) -> str:
    """Normalize a string for quote matching.
    - Replace smart quotes with straight quotes.
    - Normalize escaped quotes (\\\" -> \").
    - Strip quotation marks so nested dialogue quotes don't break matching.
    - Collapse whitespace to a single space.
    - Lower‑case for case‑insensitive comparison.
    - Preserve all other punctuation (so we never merge words).
    """
    for src, dst in SMART_QUOTE_MAP.items():
        text = text.replace(src, dst)
    text = text.replace(r'\"', '"').replace(r"\'", "'")
    text = text.replace('"', '').replace("'", "")
    # Collapse any whitespace (including newlines) to a single space
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

@dataclass
class ValidationResult:
    verified_citations: List[Dict]
    unverified_citations: List[Dict]
    attribution_warnings: List[str]
    has_any_verified: bool

def validate_evidence(
    model_citations: List[Dict],
    retrieved_citations: List[Dict],
    model_answer: str,
) -> ValidationResult:
    """Validate the LLM‑generated citations against retrieved transcript chunks.

    Returns a ValidationResult that the caller can use to build the HTTP response.
    """
    # Index retrieved chunks by source_id for fast lookup
    retrieved_by_id = {c["source_id"]: c for c in retrieved_citations}

    verified: List[Dict] = []
    unverified: List[Dict] = []
    warnings: List[str] = []

    for cit in model_citations:
        src_id = cit.get("source_id")
        quote = cit.get("quote", "")
        speaker = cit.get("speaker")
        chunk = retrieved_by_id.get(src_id) if src_id else None
        norm_quote = _normalize(quote)
        matched_chunk = None

        if chunk and norm_quote and norm_quote in _normalize(chunk.get("content", "")):
            verified.append(chunk)
            matched_chunk = chunk
        elif norm_quote:
            # Try to recover the quote in *any* other retrieved chunk
            for other in retrieved_citations:
                if norm_quote in _normalize(other.get("content", "")):
                    matched_chunk = other
                    break
            if matched_chunk:
                verified.append(matched_chunk)
            else:
                unverified.append(cit)
        else:
            unverified.append(cit)

        # Attribution / speaker warning
        if speaker and matched_chunk:
            chunk_speaker = matched_chunk.get("guest") or matched_chunk.get("episode_title")
            if chunk_speaker and speaker.lower() != chunk_speaker.lower():
                warnings.append(
                    f"Speaker mismatch: model claimed '{speaker}' but chunk {matched_chunk.get('source_id', src_id)} is associated with '{chunk_speaker}'."
                )

    if unverified:
        unverified_details = []
        for u in unverified:
            q = u.get("quote")
            if q:
                snippet = q if len(q) <= 60 else q[:57] + "..."
                unverified_details.append(f"'{snippet}'")
        if unverified_details:
            warnings.append(
                f"{len(unverified)} citation(s) could not be verified against transcripts ({', '.join(unverified_details)}). Do not treat unverified metrics or quotes as transcript-backed."
            )
        else:
            warnings.append(
                f"{len(unverified)} citation(s) could not be verified against the retrieved transcripts."
            )

    return ValidationResult(
        verified_citations=verified,
        unverified_citations=unverified,
        attribution_warnings=warnings,
        has_any_verified=bool(verified),
    )

def validate_markdown_text(text: str, retrieved_citations: List[Dict]) -> ValidationResult:
    """
    Validates a plain markdown answer by scanning for direct quotes and substantial
    phrases matching retrieved transcript chunks.
    Only associates citations with the actual chunk that contains the matched text.
    """
    if not text or not retrieved_citations:
        return ValidationResult([], [], [], False)

    verified: List[Dict] = []
    unverified: List[Dict] = []
    warnings: List[str] = []

    # 1. Look for quoted phrases in markdown: "..." or “...”
    quotes = re.findall(r'["\u201c]([^"\u201d]{20,})["\u201d]', text)
    for q in quotes:
        norm_q = _normalize(q)
        matched = None
        for chunk in retrieved_citations:
            if norm_q in _normalize(chunk.get("content", "")):
                matched = chunk
                break
        if matched:
            if matched not in verified:
                verified.append(matched)
        else:
            unverified.append({"quote": q})

    # 2. If no quotation marks matched, scan for 6+ consecutive words from any chunk
    if not verified and not unverified:
        norm_text = _normalize(text)
        for chunk in retrieved_citations:
            content = chunk.get("content", "")
            norm_content = _normalize(content)
            words = norm_content.split()
            if len(words) >= 6:
                window_size = 6
                for i in range(len(words) - window_size + 1):
                    phrase = " ".join(words[i:i + window_size])
                    if phrase in norm_text:
                        if chunk not in verified:
                            verified.append(chunk)
                        break

    if unverified:
        warnings.append(
            f"{len(unverified)} quote(s) in the response could not be verified against the retrieved transcripts."
        )

    return ValidationResult(
        verified_citations=verified,
        unverified_citations=unverified,
        attribution_warnings=warnings,
        has_any_verified=bool(verified),
    )
def strip_unverified_quotes(answer: str, unverified_citations: List[Dict]) -> str:
    """
    Silently remove each unverified verbatim quotation from *answer*.

    Fabricated quotes are deleted from the answer text without any visible
    placeholder or warning tag. Surrounding prose and paraphrases are
    left untouched.

    Constraints / non-goals
    -----------------------
    * Does NOT attempt semantic verification – only exact string matching.
    * Does NOT touch claims that are not presented as direct quotations.
    * Does NOT modify anything when unverified_citations is empty.
    """
    if not unverified_citations:
        return answer

    for cit in unverified_citations:
        raw_quote = cit.get("quote", "")
        if not raw_quote:
            continue

        # Normalise smart quotes in the candidate quote for matching.
        norm_q = _normalize(raw_quote)
        # Skip very short fragments to avoid false-positive replacements.
        if len(norm_q) < 15:
            continue

        # Build a smart-quote normalised version of the raw quote.
        candidates = [raw_quote]
        normalised_raw = raw_quote
        for src, dst in SMART_QUOTE_MAP.items():
            normalised_raw = normalised_raw.replace(src, dst)
        if normalised_raw != raw_quote:
            candidates.append(normalised_raw)

        # Silently remove the unverified quote from the answer.
        for candidate in candidates:
            if candidate in answer:
                answer = answer.replace(candidate, "")
                break
            # Try case-insensitive match.
            lower_answer = answer.lower()
            lower_cand = candidate.lower()
            idx = lower_answer.find(lower_cand)
            if idx != -1:
                answer = answer[:idx] + answer[idx + len(candidate):]
                break

    # Clean up any double spaces or orphaned quotation marks left behind.
    import re
    answer = re.sub(r'"\s*"', '', answer)       # empty quoted spans
    answer = re.sub(r'\s{2,}', ' ', answer)     # double spaces
    return answer.strip()

def secure_artifact_html(html_str: str) -> str:
    """
    Ensures generated HTML artifacts include a strict Content Security Policy (CSP).
    Isolates untrusted scripts from network exfiltration, access to parent DOM,
    credentials, or storage, while allowing safe inline CSS and UI behavior.
    """
    if not html_str or not html_str.strip():
        return ""

    csp_meta = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; img-src data: https:; font-src data: https:;">'

    if "Content-Security-Policy" in html_str:
        return html_str

    if "<head>" in html_str:
        return html_str.replace("<head>", f"<head>\n    {csp_meta}", 1)
    elif "<head " in html_str:
        return re.sub(r'(<head[^>]*>)', rf'\1\n    {csp_meta}', html_str, count=1, flags=re.IGNORECASE)
    elif "<html>" in html_str:
        return html_str.replace("<html>", f"<html>\n<head>\n    {csp_meta}\n</head>", 1)
    else:
        return f"<head>{csp_meta}</head>\n{html_str}"




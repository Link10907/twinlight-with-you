"""Mechanical provenance checks. Semantic truth still requires source reading."""
from __future__ import annotations
from collections import defaultdict
from .common import ContractError, check, digest, privacy_findings, schema_check
from .history import assert_history

FACTUAL = {"achievement", "practice", "interest", "preference", "self_description"}


def verify(history: dict, analysis: dict, complete: bool = True) -> dict:
    assert_history(history)
    schema_check(history, "history.schema.json")
    schema_check(analysis, "analysis.schema.json")
    check(analysis["history_digest"] == history["history_digest"], "Analysis belongs to a different history snapshot")
    messages = {m["id"]: m for m in history["messages"]}
    facts = {}
    for fact in analysis["facts"]:
        check(fact["id"] not in facts, "Duplicate fact ID")
        facts[fact["id"]] = fact
        for ref in fact["evidence"]:
            msg = messages.get(ref["message_id"])
            check(msg is not None, f"Unknown evidence message in {fact['id']}")
            check(msg["role"] == "user", "Assistant/tool/system text cannot establish a personal fact")
            check(msg["text_sha256"] == ref["text_sha256"], "Stale quote hash")
            check(0 <= ref["start"] < ref["end"] <= len(msg["text"]), "Evidence offsets out of bounds")
            check(msg["text"][ref["start"]:ref["end"]] == ref["quote"], "Evidence must be an exact, contiguous quote at its offsets")
        if fact["kind"] in FACTUAL and fact["review"] == "accepted":
            check(fact["speech_context"] == "autobiographical", "Personal conclusions require autobiographical evidence, not roleplay or quoted text")
        if fact["kind"] == "plan":
            check(fact["status"] == "planned", "A plan cannot be compiled as an achieved/current fact")
        if fact["kind"] == "question":
            check(fact["status"] in ("uncertain", "planned"), "Asking is not evidence of achievement or proficiency")
        if fact["speech_context"] in ("third_party", "hypothetical", "quoted", "unknown"):
            check(fact["review"] != "accepted", "Ambiguous/third-party claims need review; do not publish as the user's life")
        if history["coverage"]["scope"] == "memory_only":
            check(fact["review"] != "accepted", "Memory-only summaries are leads, not verbatim history evidence; confirm with the user or actual records")
    superseded = set()
    for f in facts.values():
        for old_id in f["supersedes"]:
            check(old_id in facts and old_id != f["id"], "Invalid superseded fact reference")
            check(f["review"] == "accepted", "An unaccepted fact cannot supersede another fact")
            superseded.add(old_id)
    def visit(fid, path):
        check(fid not in path, "Cycle in supersedes graph")
        for nxt in facts[fid]["supersedes"]: visit(nxt, path | {fid})
    for fid in facts: visit(fid, set())
    active = {k:v for k,v in facts.items() if v["review"] == "accepted" and k not in superseded and v["sensitivity"] != "sensitive"}
    current_by_key = defaultdict(list)
    for fid, f in active.items():
        if f["conflict_key"] and f["status"] == "current": current_by_key[f["conflict_key"]].append(fid)
    for key, ids in current_by_key.items():
        check(len(ids) <= 1, f"Unresolved current-state conflict: {key}; use explicit supersedes, not silent overwrite")

    user_ids = {m["id"] for m in messages.values() if m["role"] == "user"}
    reviewed, disposition_facts = set(), set()
    for item in analysis["message_dispositions"]:
        mid = item["message_id"]
        check(mid in user_ids and mid not in reviewed, "Disposition must reference one unique user message")
        reviewed.add(mid)
        check((item["reason"] == "extracted") == bool(item["fact_ids"]), "extracted dispositions need facts; exclusions must have none")
        for fid in item["fact_ids"]:
            check(fid in facts, "Disposition references missing fact")
            check(any(r["message_id"] == mid for r in facts[fid]["evidence"]), "Disposition fact does not cite that message")
            disposition_facts.add(fid)
    if complete:
        check(reviewed == user_ids, f"Extraction coverage incomplete: {len(user_ids-reviewed)} user messages not accounted for")
        check(disposition_facts == set(facts), "Some facts are not reconciled into source-message dispositions")

    used, theme_ids, topic_ids = set(), set(), set()
    def require(ids, context):
        for fid in ids: check(fid in active, f"{context} cites unavailable/rejected/sensitive/superseded fact: {fid}")
        used.update(ids)
    for theme in analysis["themes"]:
        check(theme["id"] not in theme_ids, "Duplicate theme ID")
        theme_ids.add(theme["id"])
        require(theme["fact_ids"], theme["id"])
        for statement in [theme["headline"], theme["reflection"], *theme["paragraphs"]]:
            require(statement["fact_ids"], "Narrative")
            check(set(statement["fact_ids"]) <= set(theme["fact_ids"]), "Narrative cites facts outside its theme")
        for topic in theme["topics"]:
            key = (theme["id"], topic["id"])
            check(key not in topic_ids, "Duplicate topic ID within a theme")
            topic_ids.add(key)
            require(topic["fact_ids"], "Topic")
            check(set(topic["fact_ids"]) <= set(theme["fact_ids"]), "Topic facts must be in parent theme")
            require(topic["summary"]["fact_ids"], "Topic summary")
            check(set(topic["summary"]["fact_ids"]) <= set(topic["fact_ids"]), "Topic summary exceeds topic evidence")
    card = analysis["card"]
    if card:
        require(card["basis_fact_ids"], "Card persona")
        # A creative title is permitted; psychological diagnosis/ability rankings are not.
        for statement in [card["tagline"], card["reflection"], *card["keywords"], *card["symbols"]]:
            require(statement["fact_ids"], "Card text/symbol")
            check(set(statement["fact_ids"]) <= set(card["basis_fact_ids"]), "Card content not covered by persona basis")
        check(card["portrait_mode"] != "user_reference" or card["reference_consent"], "Photo-based likeness needs explicit consent")
    meta = analysis["summary_meta"]
    names = {"openai": "GPT", "anthropic": "Claude", "google": "Gemini", "deepseek": "DeepSeek"}
    if meta["provider"] in names:
        check(meta["display_name"] == names[meta["provider"]], "Summary author display name/provider mismatch")
    if meta["provider"] == "unknown":
        check(meta["display_name"] is None, "Unknown summary author must not silently become GPT")
    if meta["display_name"]:
        check(meta["attribution_source"] != "unknown", "Attribution needs explicit generation provenance")
    return {"ok": True, "analysis_digest": digest(analysis), "history_digest": history["history_digest"],
            "user_messages": len(user_ids), "accounted_user_messages": len(reviewed),
            "candidate_facts": len(facts), "active_publishable_facts": len(active), "cited_facts": len(used),
            "unused_active_facts": sorted(set(active)-used), "superseded": sorted(superseded),
            "needs_confirmation": sorted(f["id"] for f in facts.values() if f["review"] == "needs_confirmation"),
            "sensitive_excluded": sorted(f["id"] for f in facts.values() if f["sensitivity"] == "sensitive"),
            "extraction_coverage_complete": reviewed == user_ids and disposition_facts == set(facts),
            "semantic_truth_verified_by_code": False,
            "limitations": ["Exact anchoring and consistency are tested, not whether a paraphrase entails the source.",
                            "Public copy needs human review. No claim of complete account history."]}


def anchor(message: dict, quote: str, occurrence: int = 0) -> dict:
    check(bool(quote), "Empty quote")
    starts, pos = [], 0
    while True:
        idx = message["text"].find(quote, pos)
        if idx < 0: break
        starts.append(idx); pos = idx + max(1, len(quote))
    check(0 <= occurrence < len(starts), "Quote/occurrence absent from this message")
    start = starts[occurrence]
    return {"message_id": message["id"], "text_sha256": message["text_sha256"], "start": start,
            "end": start+len(quote), "quote": quote}

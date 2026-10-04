"""Mechanical provenance checks. Semantic truth still requires source reading."""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from .common import Collector, ContractError, check, digest, privacy_findings, schema_check, schema_errors
from .history import assert_history

FACTUAL = {"achievement", "practice", "interest", "preference", "self_description"}


def check_ref(need: Collector, messages: dict, ref: dict, path: str, owner: str) -> bool:
    msg = messages.get(ref["message_id"])
    if not need(msg is not None, f"Unknown evidence message in {owner}", path + ".message_id"):
        return False
    ok = need(msg["role"] == "user", "Assistant/tool/system text cannot establish a personal fact", path + ".message_id")
    ok &= need(msg["text_sha256"] == ref["text_sha256"], "Stale quote hash", path + ".text_sha256")
    if not need(0 <= ref["start"] < ref["end"] <= len(msg["text"]), "Evidence offsets out of bounds", path):
        return False
    return need(msg["text"][ref["start"]:ref["end"]] == ref["quote"], "Evidence must be an exact, contiguous quote at its offsets", path + ".quote") and ok


def verify(history: dict, analysis: dict, complete: bool = True, collect: bool = False) -> dict:
    """Raise at the first problem, or with collect=True return every problem with its JSON path."""
    need = Collector(collect)
    assert_history(history)
    schema_check(history, "history.schema.json")
    if collect:
        shape = schema_errors(analysis, "analysis.schema.json")
        if shape:
            # Later checks index into the structure; report shape problems alone rather than guess.
            return {"ok": False, "stage": "schema", "errors": shape, "semantic_truth_verified_by_code": False}
    else:
        schema_check(analysis, "analysis.schema.json")
    need(analysis["history_digest"] == history["history_digest"], "Analysis belongs to a different history snapshot", "history_digest")
    messages = {m["id"]: m for m in history["messages"]}
    facts, where = {}, {}
    for i, fact in enumerate(analysis["facts"]):
        fp = f"facts[{i}]"
        if not need(fact["id"] not in facts, "Duplicate fact ID", fp + ".id"):
            continue
        facts[fact["id"]] = fact; where[fact["id"]] = fp
        for j, ref in enumerate(fact["evidence"]):
            check_ref(need, messages, ref, f"{fp}.evidence[{j}]", fact["id"])
        if fact["kind"] in FACTUAL and fact["review"] == "accepted":
            need(fact["speech_context"] == "autobiographical", "Personal conclusions require autobiographical evidence, not roleplay or quoted text", fp + ".speech_context")
        if fact["kind"] == "plan":
            need(fact["status"] == "planned", "A plan cannot be compiled as an achieved/current fact", fp + ".status")
        if fact["kind"] == "question":
            need(fact["status"] in ("uncertain", "planned"), "Asking is not evidence of achievement or proficiency", fp + ".status")
        if fact["speech_context"] in ("third_party", "hypothetical", "quoted", "unknown"):
            need(fact["review"] != "accepted", "Ambiguous/third-party claims need review; do not publish as the user's life", fp + ".review")
        if history["coverage"]["scope"] == "memory_only":
            need(fact["review"] != "accepted", "Memory-only summaries are leads, not verbatim history evidence; confirm with the user or actual records", fp + ".review")
    superseded = set()
    for fid, f in facts.items():
        for old_id in f["supersedes"]:
            valid = need(old_id in facts and old_id != fid, "Invalid superseded fact reference", where[fid] + ".supersedes")
            need(f["review"] == "accepted", "An unaccepted fact cannot supersede another fact", where[fid] + ".review")
            if valid: superseded.add(old_id)
    color = dict.fromkeys(facts, 0)
    def visit(fid):
        color[fid] = 1
        for nxt in facts[fid]["supersedes"]:
            if nxt not in facts or nxt == fid: continue
            if color[nxt] == 1: need(False, "Cycle in supersedes graph", where[fid] + ".supersedes")
            elif color[nxt] == 0: visit(nxt)
        color[fid] = 2
    for fid in facts:
        if color[fid] == 0: visit(fid)
    active = {k:v for k,v in facts.items() if v["review"] == "accepted" and k not in superseded and v["sensitivity"] != "sensitive"}
    current_by_key = defaultdict(list)
    for fid, f in active.items():
        if f["conflict_key"] and f["status"] == "current": current_by_key[f["conflict_key"]].append(fid)
    for key, ids in current_by_key.items():
        need(len(ids) <= 1, f"Unresolved current-state conflict: {key}; use explicit supersedes, not silent overwrite", " + ".join(where[i] for i in ids))

    user_ids = {m["id"] for m in messages.values() if m["role"] == "user"}
    reviewed, disposition_facts = set(), set()
    for k, item in enumerate(analysis["message_dispositions"]):
        dp, mid = f"message_dispositions[{k}]", item["message_id"]
        if not need(mid in user_ids and mid not in reviewed, "Disposition must reference one unique user message", dp + ".message_id"):
            continue
        reviewed.add(mid)
        need((item["reason"] == "extracted") == bool(item["fact_ids"]), "extracted dispositions need facts; exclusions must have none", dp + ".reason")
        for fid in item["fact_ids"]:
            if not need(fid in facts, "Disposition references missing fact", dp + ".fact_ids"):
                continue
            need(any(r["message_id"] == mid for r in facts[fid]["evidence"]), "Disposition fact does not cite that message", dp + ".fact_ids")
            disposition_facts.add(fid)
    if complete:
        need(reviewed == user_ids, f"Extraction coverage incomplete: {len(user_ids-reviewed)} user messages not accounted for", "message_dispositions")
        need(disposition_facts == set(facts), "Some facts are not reconciled into source-message dispositions", "message_dispositions")

    used, theme_ids, topic_ids = set(), set(), set()
    def require(ids, context, path):
        for fid in ids: need(fid in active, f"{context} cites unavailable/rejected/sensitive/superseded fact: {fid}", path)
        used.update(ids)
    for t, theme in enumerate(analysis["themes"]):
        tp = f"themes[{t}]"
        need(theme["id"] not in theme_ids, "Duplicate theme ID", tp + ".id")
        theme_ids.add(theme["id"])
        require(theme["fact_ids"], theme["id"], tp + ".fact_ids")
        parts = [("headline", theme["headline"]), ("reflection", theme["reflection"])] + [(f"paragraphs[{n}]", s) for n, s in enumerate(theme["paragraphs"])]
        for name, statement in parts:
            require(statement["fact_ids"], "Narrative", f"{tp}.{name}.fact_ids")
            need(set(statement["fact_ids"]) <= set(theme["fact_ids"]), "Narrative cites facts outside its theme", f"{tp}.{name}.fact_ids")
        for n, topic in enumerate(theme["topics"]):
            pp, key = f"{tp}.topics[{n}]", (theme["id"], topic["id"])
            need(key not in topic_ids, "Duplicate topic ID within a theme", pp + ".id")
            topic_ids.add(key)
            require(topic["fact_ids"], "Topic", pp + ".fact_ids")
            need(set(topic["fact_ids"]) <= set(theme["fact_ids"]), "Topic facts must be in parent theme", pp + ".fact_ids")
            require(topic["summary"]["fact_ids"], "Topic summary", pp + ".summary.fact_ids")
            need(set(topic["summary"]["fact_ids"]) <= set(topic["fact_ids"]), "Topic summary exceeds topic evidence", pp + ".summary.fact_ids")
    card = analysis["card"]
    if card:
        require(card["basis_fact_ids"], "Card persona", "card.basis_fact_ids")
        # A creative title is permitted; psychological diagnosis/ability rankings are not.
        parts = [("tagline", card["tagline"]), ("reflection", card["reflection"])] + \
                [(f"keywords[{n}]", s) for n, s in enumerate(card["keywords"])] + [(f"symbols[{n}]", s) for n, s in enumerate(card.get("symbols", []))]
        for name, statement in parts:
            require(statement["fact_ids"], "Card text/symbol", f"card.{name}.fact_ids")
            need(set(statement["fact_ids"]) <= set(card["basis_fact_ids"]), "Card content not covered by persona basis", f"card.{name}.fact_ids")
        need(card.get("portrait_mode", "original_character") != "user_reference" or card.get("reference_consent", False), "Photo-based likeness needs explicit consent", "card.reference_consent")
    meta = analysis["summary_meta"]
    names = {"openai": "GPT", "anthropic": "Claude", "google": "Gemini", "deepseek": "DeepSeek"}
    if meta["provider"] in names:
        need(meta["display_name"] == names[meta["provider"]], "Summary author display name/provider mismatch", "summary_meta.display_name")
    if meta["provider"] == "unknown":
        need(meta["display_name"] is None, "Unknown summary author must not silently become GPT", "summary_meta.display_name")
    if meta["display_name"]:
        need(meta["attribution_source"] != "unknown", "Attribution needs explicit generation provenance", "summary_meta.attribution_source")
    extra = {"errors": need.errors} if collect else {}
    return {"ok": not need.errors, **extra, "analysis_digest": digest(analysis), "history_digest": history["history_digest"],
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


def _occurrences(text: str, quote: str) -> list[int]:
    starts, pos = [], 0
    while (idx := text.find(quote, pos)) >= 0:
        starts.append(idx); pos = idx + 1
    return starts


def anchor_document(history: dict, doc: dict) -> dict:
    """Fill text_sha256/start/end for every evidence ref from message_id + quote (+ optional 0-based
    `occurrence`). The model only has to copy the quote; offsets are computed, never guessed.
    Returns every problem at once; the document is only usable when errors is empty."""
    assert_history(history)
    messages = {m["id"]: m for m in history["messages"]}
    out = deepcopy(doc)
    errors, changed, total = [], 0, 0
    facts = out.get("facts") if isinstance(out, dict) else None
    if not isinstance(facts, list):
        return {"ok": False, "errors": [{"path": "facts", "message": "Expected an analysis or chunk result with a facts array"}], "document": None}
    for i, fact in enumerate(facts):
        refs = fact.get("evidence") if isinstance(fact, dict) else None
        if not isinstance(refs, list):
            errors.append({"path": f"facts[{i}].evidence", "message": "Expected an evidence array"}); continue
        for j, ref in enumerate(refs):
            path = f"facts[{i}].evidence[{j}]"
            total += 1
            if not isinstance(ref, dict) or not isinstance(ref.get("message_id"), str) or not isinstance(ref.get("quote"), str) or not ref.get("quote"):
                errors.append({"path": path, "message": "Each evidence item needs message_id and a non-empty quote"}); continue
            msg = messages.get(ref["message_id"])
            if msg is None:
                errors.append({"path": path + ".message_id", "message": "Unknown message_id"}); continue
            if msg["role"] != "user":
                errors.append({"path": path + ".message_id", "message": "Only user messages can be evidence"}); continue
            quote, starts = ref["quote"], _occurrences(msg["text"], ref["quote"])
            if not starts:
                squash = lambda s: "".join(s.split())
                hint = " (it matches after removing whitespace: copy the exact characters, including spaces and line breaks)" \
                    if squash(quote) and squash(quote) in squash(msg["text"]) else ""
                errors.append({"path": path + ".quote", "message": "Quote not found verbatim in that message" + hint}); continue
            occ = ref.get("occurrence")
            if occ is not None:
                if not isinstance(occ, int) or isinstance(occ, bool) or not 0 <= occ < len(starts):
                    errors.append({"path": path + ".occurrence", "message": f"occurrence must be 0–{len(starts)-1}"}); continue
                start = starts[occ]
            elif len(starts) == 1:
                start = starts[0]
            elif ref.get("start") in starts:
                start = ref["start"]
            else:
                errors.append({"path": path + ".quote", "message": f"Quote occurs {len(starts)} times in that message; add \"occurrence\": 0–{len(starts)-1} or quote more context"}); continue
            new = {"message_id": msg["id"], "text_sha256": msg["text_sha256"], "start": start, "end": start + len(quote), "quote": quote}
            if new != ref: changed += 1
            refs[j] = new
    return {"ok": not errors, "errors": errors, "evidence_refs": total, "changed": changed, "document": out if not errors else None}

#!/usr/bin/env python3
"""Reproducible review probes; fictional inputs only, no model/network calls.

Run with Python 3.10+ and the project's requirements installed:
  python verification/review-2026-10-03/experiments.py

These probes describe observed limitations. They deliberately do not assert that
mechanical validation can establish semantic truth. Generated inputs stay in a
TemporaryDirectory; only the result summary is retained beside this script.
"""
from __future__ import annotations

import copy
import json
import platform
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from twinlight_core.common import ContractError, load, save
from twinlight_core.history import normalize, make_chunks
from twinlight_core.evidence import anchor, verify
from twinlight_core.extraction import merge_chunks
from twinlight_core.compiler import compile_profile, review_markdown
from twinlight_core.layout import make_layout


def draft(history):
    result = load(ROOT / "examples/demo/analysis.json")
    result.update(history_digest=history["history_digest"], facts=[],
                  message_dispositions=[], themes=[], card=None)
    return result


def fact(fid, message, quote, statement, kind="self_description", key=None):
    return {"id": fid, "statement": statement, "kind": kind,
            "speech_context": "autobiographical", "status": "current",
            "evidence": [anchor(message, quote)], "sensitivity": "personal",
            "review": "accepted", "supersedes": [], "conflict_key": key}


def chunk_results(history, manifest, chunks, out, factory):
    out.mkdir()
    for i, entry in enumerate(manifest["chunks"]):
        chunk = load(chunks / entry["path"])
        ids = {s["message_id"] for s in chunk["segments"] if s["role"] == "user"}
        selected = [m for m in history["messages"] if m["id"] in ids]
        facts = [factory(m) for m in selected]
        save(out / f"result-{i:04d}.json", {
            "chunk_path": entry["path"], "chunk_sha256": entry["sha256"],
            "history_digest": history["history_digest"], "facts": facts,
            "message_dispositions": [{"message_id": m["id"],
                "fact_ids": [f["id"]], "reason": "extracted"}
                for m, f in zip(selected, facts)]})


def run():
    probes = []
    with tempfile.TemporaryDirectory(prefix="twinlight-review-") as td:
        tmp = Path(td)

        # Source order is known even when event/message dates are unknown.
        path = tmp / "order.json"
        source = [{"id": f"m{i}", "conversation_id": "one-thread",
                   "role": "user", "text": f"第{i}条对话", "timestamp": None}
                  for i in range(1, 11)]
        save(path, {"messages": source})
        history = normalize(path, "generic")
        observed = [m["native_id"] for m in history["messages"]]
        expected = [m["id"] for m in source]
        probes.append({"id": "missing_timestamp_order", "category": "defect",
            "reproduced": observed != expected, "source_order": expected,
            "normalized_order": observed,
            "retains_explicit_sequence_field": any("sequence" in m or "parent_id" in m
                                                     for m in history["messages"])})

        # ChatGPT's active path also contains ordering information without dates.
        nodes = {"root": {"parent": None, "message": None}}
        parent = "root"
        for i in range(1, 11):
            mid = f"m{i}"
            nodes[mid] = {"parent": parent, "message": {"id": mid,
                "author": {"role": "user"}, "content": {"parts": [f"第{i}条对话"]}}}
            parent = mid
        save(path, [{"id": "one-thread", "current_node": parent, "mapping": nodes}])
        history = normalize(path, "chatgpt")
        observed = [m["native_id"] for m in history["messages"]]
        probes.append({"id": "chatgpt_parent_order", "category": "defect",
            "reproduced": observed != expected, "parent_path_order": expected,
            "normalized_order": observed})

        # Merge is supposed to precede reconciliation of changed current identity.
        path = tmp / "jobs.json"
        rows = [{"id": name, "conversation_id": "jobs", "role": "user",
                 "text": text + "。" * (1000-len(text)), "timestamp": stamp}
                for name, text, stamp in [
                    ("old", "我现在是设计师", "2025-01-01T00:00:00Z"),
                    ("new", "更正，我现在是教师", "2025-02-01T00:00:00Z")]]
        save(path, {"messages": rows})
        history = normalize(path, "generic")
        def job(m):
            quote = "我现在是设计师" if m["native_id"] == "old" else "更正，我现在是教师"
            return fact("job-"+m["native_id"], m, quote, quote, key="occupation")
        chunks = tmp / "jobs-chunks"
        manifest = make_chunks(history, chunks, 1000)
        results = tmp / "jobs-results"
        chunk_results(history, manifest, chunks, results, job)
        try:
            merge_chunks(history, draft(history), chunks/"manifest.json", results)
            merge_error = None
        except ContractError as exc:
            merge_error = str(exc)
        repaired = draft(history)
        repaired["facts"] = [job(m) for m in history["messages"]]
        next(f for f in repaired["facts"] if f["id"] == "job-new")["supersedes"] = ["job-old"]
        repaired["message_dispositions"] = [{"message_id": m["id"],
            "fact_ids": ["job-"+m["native_id"]], "reason": "extracted"}
            for m in history["messages"]]
        probes.append({"id": "merge_before_reconcile", "category": "defect",
            "reproduced": bool(merge_error), "chunks": len(manifest["chunks"]),
            "merge_error": merge_error, "valid_after_explicit_supersedes": verify(history, repaired)["ok"]})

        # A recurring preference across nine chunks exceeds the evidence cap.
        path = tmp / "repeat.json"
        quote = "我喜欢保留过程记录"
        save(path, {"messages": [{"id": f"m{i}", "conversation_id": "repeat",
            "role": "user", "text": quote + "。" * (1000-len(quote)),
            "timestamp": f"2025-01-{i+1:02d}T00:00:00Z"} for i in range(9)]})
        history = normalize(path, "generic")
        chunks = tmp / "repeat-chunks"
        manifest = make_chunks(history, chunks, 1000)
        results = tmp / "repeat-results"
        chunk_results(history, manifest, chunks, results,
                      lambda m: fact("process-preference", m, quote, quote, kind="preference"))
        try:
            merge_chunks(history, draft(history), chunks/"manifest.json", results)
            merge_error = None
        except ContractError as exc:
            merge_error = str(exc)
        probes.append({"id": "nine_repeated_evidences", "category": "scaling_limit",
            "reproduced": bool(merge_error), "chunks": len(manifest["chunks"]),
            "merge_error": merge_error})

        # This checks the explicitly documented boundary, not an NLI guarantee.
        history = load(ROOT / "examples/demo/history.json")
        analysis = load(ROOT / "examples/demo/analysis.json")
        bad = copy.deepcopy(analysis)
        theme = next(t for t in bad["themes"] if "fact-motion-plan" in t["fact_ids"])
        theme["headline"] = {"text": "你已经掌握网页动画并完成作品。",
                             "fact_ids": ["fact-motion-plan"]}
        audit = verify(history, bad)
        profile, _, _ = compile_profile(history, bad)
        probes.append({"id": "true_quote_false_narrative", "category": "semantic_boundary",
            "reproduced": audit["ok"] and any(c["headline"] == theme["headline"]["text"]
                                                for c in profile["chapters"]),
            "source": next(f for f in bad["facts"] if f["id"] == "fact-motion-plan")["evidence"][0]["quote"],
            "compiled_claim": theme["headline"]["text"], "mechanical_verify_ok": audit["ok"],
            "semantic_truth_verified_by_code": audit["semantic_truth_verified_by_code"]})

        excluded = draft(history)
        excluded["message_dispositions"] = [{"message_id": m["id"], "fact_ids": [],
                                             "reason": "not_personal"}
                                            for m in history["messages"] if m["role"] == "user"]
        audit = verify(history, excluded)
        probes.append({"id": "all_excluded_coverage", "category": "semantic_boundary",
            "reproduced": audit["extraction_coverage_complete"],
            "accounted_messages": audit["accounted_user_messages"],
            "user_messages": audit["user_messages"], "facts": audit["candidate_facts"],
            "note": "This is message disposition coverage, not fact recall; an empty theme build remains blocked."})

        reviewed = copy.deepcopy(analysis)
        reviewed["card"]["keywords"][0]["label"] = "独有关键词"
        text = review_markdown(history, reviewed)
        excluded_ids = [d["message_id"] for d in reviewed["message_dispositions"] if not d["fact_ids"]]
        probes.append({"id": "review_omits_required_items", "category": "review_gap",
            "reproduced": "独有关键词" not in text and all(mid not in text for mid in excluded_ids),
            "card_keyword_present": "独有关键词" in text,
            "excluded_message_ids_present": [mid for mid in excluded_ids if mid in text],
            "source_unknown_dates": history["coverage"]["unknown_dates"],
            "unknown_dates_explicitly_reported": "未知日期" in text or "unknown_dates" in text})

        # Missing per-evidence dispositions can be masked by message exclusions.
        mixed = copy.deepcopy(analysis)
        f = mixed["facts"][0]
        other = next(m for m in history["messages"] if m["role"] == "user" and "朋友完成" in m["text"])
        f["evidence"].append(anchor(other, other["text"]))
        audit = verify(history, mixed)
        probes.append({"id": "evidence_disposition_bidirectional_binding", "category": "validation_gap",
            "reproduced": audit["ok"], "mechanical_verify_ok": audit["ok"],
            "note": "A fact can cite a message whose disposition says excluded; verify only checks disposition -> evidence."})

        # Retaining one topic should leave room in the seven removed orbit slots.
        churn = copy.deepcopy(analysis)
        churn["themes"] = churn["themes"][:1]
        sample = copy.deepcopy(churn["themes"][0]["topics"][0])
        churn["themes"][0]["topics"] = [{**copy.deepcopy(sample), "id": f"old-{i}"} for i in range(8)]
        lock = make_layout(churn, history)
        retained = churn["themes"][0]["topics"][:1]
        churn["themes"][0]["topics"] = retained + [{**copy.deepcopy(sample), "id": f"new-{i}"} for i in range(7)]
        try:
            make_layout(churn, history, lock)
            layout_error = None
        except ContractError as exc:
            layout_error = str(exc)
        probes.append({"id": "layout_lock_topic_churn", "category": "incremental_limit",
            "reproduced": bool(layout_error), "before_topics": 8, "after_topics": 8,
            "retained_topics": 1, "vacated_slots": 7, "error": layout_error})

    result = {"review_date": "2026-10-03", "fictional_inputs_only": True,
              "python": platform.python_version(),
              "dependencies": {n: version(n) for n in ["jsonschema", "Pillow"]},
              "probes": probes, "unexpected_runtime_failures": 0,
              "semantic_accuracy_estimated": False}
    save(Path(__file__).with_name("results.json"), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()

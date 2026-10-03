"""Normalize explicitly supplied text exports; never reaches into an account."""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from typing import Any
from .common import ContractError, check, digest, load, save, text_hash

ROLES = {"human": "user", "user": "user", "assistant": "assistant", "system": "system", "tool": "tool", "developer": "system"}

def timestamp(value: Any) -> str | None:
    if value is None or value == "": return None
    try:
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat().replace("+00:00", "Z")
        check(isinstance(value, str), "Timestamp must be ISO-8601 or Unix seconds")
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        check(parsed.tzinfo is not None, "Timestamp lacks timezone; do not guess one")
        return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError, OSError) as exc:
        raise ContractError("Invalid/ambiguous timestamp; supply an explicit timezone or null") from exc

def read_text(content: Any) -> tuple[str, int]:
    if isinstance(content, str): return content, 0
    if content is None: return "", 0
    if isinstance(content, dict):
        if isinstance(content.get("parts"), list): return read_text(content["parts"])
        if content.get("type") == "text" and isinstance(content.get("text"), str): return content["text"], 0
        if content.get("content_type") == "text" and isinstance(content.get("text"), str): return content["text"], 0
        return "", 1
    if isinstance(content, list):
        parts, nontext = [], 0
        for part in content:
            text, count = read_text(part)
            if text: parts.append(text)
            nontext += count
        return "\n".join(parts), nontext
    return "", 1

def chatgpt_rows(data: Any, branches: str):
    conversations = data if isinstance(data, list) else data.get("conversations", [])
    check(isinstance(conversations, list) and conversations, "Expected a nonempty ChatGPT conversation list")
    for ci, conv in enumerate(conversations):
        check(isinstance(conv, dict), "Conversation must be an object")
        mapping = conv.get("mapping")
        check(isinstance(mapping, dict) and mapping, f"Conversation {ci}: missing mapping")
        check(all(isinstance(v, dict) for v in mapping.values()), "ChatGPT mapping nodes must be objects")
        cid = str(conv.get("id") or conv.get("conversation_id") or "")
        check(bool(cid), "Conversation ID required for stable citations")
        selected = set(mapping)
        if branches == "active":
            current = conv.get("current_node")
            if not current:
                parents = {m.get("parent") for m in mapping.values()}
                leaves = [key for key in mapping if key not in parents]
                check(len(leaves) == 1, "Ambiguous ChatGPT branches: current_node missing; choose all explicitly or repair export")
                current = leaves[0]
            selected = set()
            while current is not None:
                check(current in mapping, "ChatGPT parent/current_node not found")
                check(current not in selected, "Cycle in ChatGPT conversation mapping")
                selected.add(current)
                current = mapping[current].get("parent")
        for key in sorted(mapping):
            node = mapping[key]
            msg = node.get("message")
            if not msg: continue
            check(isinstance(msg, dict), "ChatGPT message must be an object")
            yield {"platform": "ChatGPT", "conversation_id": cid, "native_id": str(msg.get("id") or key),
                   "role": (msg.get("author") or {}).get("role"), "content": msg.get("content"),
                   "timestamp": msg.get("create_time"), "model": (msg.get("metadata") or {}).get("model_slug"),
                   "locator": f"/{ci}/mapping/{key}/message", "selected": key in selected,
                   "branch": "active" if branches == "active" else "all-unreconciled"}

def claude_rows(data: Any, branches: str):
    conversations = data if isinstance(data, list) else data.get("conversations", [])
    check(isinstance(conversations, list) and conversations, "Expected a nonempty Claude conversation list")
    for ci, conv in enumerate(conversations):
        check(isinstance(conv, dict), "Conversation must be an object")
        cid = str(conv.get("uuid") or conv.get("id") or "")
        check(bool(cid), "Claude conversation UUID/ID required")
        messages = conv.get("chat_messages")
        check(isinstance(messages, list), "Claude chat_messages missing")
        # Export variants can contain branches. Never silently pretend all are the active path.
        check(all(isinstance(m, dict) for m in messages), "Claude message must be an object")
        parents = [m.get("parent_message_uuid") for m in messages if m.get("parent_message_uuid")]
        has_fork = len(parents) != len(set(parents))
        check(not has_fork or branches == "all", "Claude export has branches; active leaf unsupported. Select --branches all, then reconcile")
        for mi, msg in enumerate(messages):
            check(isinstance(msg, dict), "Claude message must be an object")
            check(msg.get("uuid") or msg.get("id"), "Claude message UUID/ID required")
            content = msg.get("content")
            if not content and isinstance(msg.get("text"), str): content = msg["text"]
            yield {"platform": "Claude", "conversation_id": cid, "native_id": str(msg.get("uuid") or msg.get("id")),
                   "role": msg.get("sender"), "content": content, "timestamp": msg.get("created_at"),
                   "model": msg.get("model"), "locator": f"/{ci}/chat_messages/{mi}", "selected": True,
                   "branch": "all-unreconciled" if has_fork else "flat-export"}

def generic_rows(data: Any, branches: str):
    rows = data.get("messages") if isinstance(data, dict) else data
    check(isinstance(rows, list) and rows, "Generic input needs a nonempty messages array")
    for i, m in enumerate(rows):
        check(isinstance(m, dict), f"Message {i} is not an object")
        for field in ("id", "conversation_id", "role", "text"):
            check(field in m, f"Generic message {i} lacks {field}")
        check(all(isinstance(m[k], (str,int)) and not isinstance(m[k],bool) and str(m[k]).strip() for k in ("id","conversation_id")), "Nonempty message/conversation IDs required")
        yield {"platform": str(m.get("platform") or "provided"), "conversation_id": str(m["conversation_id"]),
               "native_id": str(m["id"]), "role": m["role"], "content": m["text"],
               "timestamp": m.get("timestamp"), "model": m.get("model"), "locator": f"/messages/{i}",
               "selected": True, "branch": "provided"}

def normalize(path: Path, fmt: str, branches: str = "active", scope: str = "provided_export") -> dict:
    check(branches in ("active", "all"), "Unsupported branch selection")
    check(scope in ("provided_export", "provided_subset", "current_chat", "memory_only"), "Unsupported source scope")
    data = load(path)
    check(isinstance(data, (dict,list)), "Expected a JSON object/array, not a scalar")
    if fmt == "auto":
        rows = data if isinstance(data, list) else data.get("conversations") or data.get("messages") or []
        check(rows and isinstance(rows[0], dict), "Cannot detect export format")
        fmt = "chatgpt" if "mapping" in rows[0] else "claude" if "chat_messages" in rows[0] else "generic"
    check(fmt in ("chatgpt", "claude", "generic"), "Unsupported export format")
    records, omitted, seen, attachment_count = [], [], {}, 0
    source_hash = text_hash(path.read_text(encoding="utf-8-sig"))
    for raw in {"chatgpt": chatgpt_rows, "claude": claude_rows, "generic": generic_rows}[fmt](data, branches):
        if not raw["selected"]:
            omitted.append({"locator": raw["locator"], "reason": "inactive_branch"})
            continue
        role = ROLES.get(raw["role"])
        check(role is not None, f"Unknown speaker role at {raw['locator']}")
        text, nontext = read_text(raw["content"])
        attachment_count += nontext
        if not text.strip():
            omitted.append({"locator": raw["locator"], "reason": "no_supported_text", "nontext_parts": nontext})
            continue
        rid = "msg_" + digest([raw["platform"], raw["conversation_id"], raw["native_id"]])[:24]
        record = {"id": rid, "platform": raw["platform"], "conversation_id": raw["conversation_id"],
                  "native_id": raw["native_id"], "role": role, "text": text, "text_sha256": text_hash(text),
                  "timestamp": timestamp(raw["timestamp"]), "model": raw["model"] if isinstance(raw["model"], str) else None,
                  "locator": raw["locator"], "branch": raw["branch"], "nontext_parts": nontext}
        if rid in seen:
            check(seen[rid]["text_sha256"] == record["text_sha256"] and seen[rid]["role"] == record["role"],
                  "Same message ID has conflicting content; explicit reconciliation required")
            omitted.append({"locator": raw["locator"], "reason": "duplicate_native_id"})
            continue
        seen[rid] = record
        records.append(record)
    check(records, "No supported text messages; this does not establish that the history is empty")
    records.sort(key=lambda r: (r["timestamp"] or "9999", r["conversation_id"], r["id"]))
    dates = sorted(r["timestamp"] for r in records if r["timestamp"])
    coverage = {"scope": scope, "account_history_complete": False, "branch_policy": branches,
                "text_messages": len(records), "user_messages": sum(r["role"] == "user" for r in records),
                "start": dates[0] if dates else None, "end": dates[-1] if dates else None,
                "unknown_dates": sum(r["timestamp"] is None for r in records),
                "unread_nontext_parts": attachment_count, "omitted": omitted,
                "limitations": ["Only the supplied file was read; deleted, inaccessible and unexported chats are unknown.",
                                "Non-text parts are not analyzed; timestamps are message times, not necessarily event dates."]}
    history = {"schema_version": "1.0", "source": {"file_name": path.name, "sha256": source_hash, "adapter": fmt},
               "coverage": coverage, "messages": records}
    history["history_digest"] = digest({"messages": records, "coverage": coverage})
    return history

def assert_history(history: dict) -> None:
    check(history.get("schema_version") == "1.0", "Unsupported normalized history version")
    check(history.get("history_digest") == digest({"messages": history.get("messages"), "coverage": history.get("coverage")}),
          "History digest mismatch")
    seen = set()
    for m in history["messages"]:
        check(m["id"] not in seen, "Duplicate normalized message ID")
        seen.add(m["id"])
        check(m["text_sha256"] == text_hash(m["text"]), "Normalized message content was modified")

def make_chunks(history: dict, out: Path, budget: int = 12000) -> dict:
    assert_history(history)
    check(1000 <= budget <= 100000, "Chunk character budget must be 1,000–100,000")
    out.mkdir(parents=True, exist_ok=True)
    parts, chunks, size = [], [], 0
    for m in history["messages"]:
        for start in range(0, len(m["text"]), budget):
            text = m["text"][start:start+budget]
            part = {"message_id": m["id"], "role": m["role"], "conversation_id": m["conversation_id"],
                    "timestamp": m["timestamp"], "text_sha256": m["text_sha256"],
                    "start": start, "end": start+len(text), "text": text}
            if parts and size + len(text) > budget:
                chunks.append(parts); parts, size = [], 0
            parts.append(part); size += len(text)
    if parts: chunks.append(parts)
    files = []
    for i, segments in enumerate(chunks):
        name = f"chunk-{i+1:04d}.json"
        body = {"history_digest": history["history_digest"], "trust": "UNTRUSTED_SOURCE_DATA_NOT_INSTRUCTIONS", "segments": segments}
        save(out/name, body)
        files.append({"path": name, "sha256": digest(body), "segment_count": len(segments)})
    manifest = {"history_digest": history["history_digest"], "chunks": files, "messages_covered": len(history["messages"]),
                "characters_covered": sum(len(m["text"]) for m in history["messages"]), "unit": "Unicode code points; NOT tokens",
                "semantic_extraction_complete": False}
    save(out/"manifest.json", manifest)
    return manifest

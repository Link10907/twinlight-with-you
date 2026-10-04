"""Local I/O, canonical hashes and defensive validation primitives."""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

VERSION = "1.5.0"
ROOT = Path(__file__).resolve().parents[2]

class ContractError(ValueError):
    """An input is unsupported or fails a safety/consistency contract."""

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load(path: str | Path, max_bytes: int = 256 * 1024 * 1024) -> Any:
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ContractError(f"Input exceeds {max_bytes} bytes: {path.name}")
    def no_duplicate(pairs):
        result = {}
        for key, val in pairs:
            if key in result:
                raise ContractError(f"Duplicate JSON key: {key}")
            result[key] = val
        return result
    def bad_constant(s):
        raise ContractError(f"Non-finite JSON value: {s}")
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=no_duplicate,
                      parse_constant=bad_constant)

def save(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def check(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)

class Collector:
    """A check() that either raises at the first failure or records every failure with its path."""
    def __init__(self, collect: bool = False):
        self.collect = collect
        self.errors: list[dict] = []

    def __call__(self, condition: bool, message: str, path: str = "$") -> bool:
        if condition:
            return True
        if not self.collect:
            raise ContractError(message)
        self.errors.append({"path": path, "message": message})
        return False


def _validator(name: str):
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    schemas = [load(p) for p in sorted((ROOT / "schemas").glob("*.schema.json"))]
    registry = Registry().with_resources([(s["$id"], Resource.from_contents(s)) for s in schemas if "$id" in s])
    return Draft202012Validator(load(ROOT / "schemas" / name), registry=registry, format_checker=FormatChecker())


def _raw_schema_errors(data: Any, name: str) -> list:
    return sorted(_validator(name).iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])


def json_path(parts) -> str:
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out or "$"


def schema_errors(data: Any, name: str) -> list[dict]:
    """Every schema violation. Messages name the rule and limit, never echo source text."""
    found = []
    for e in _raw_schema_errors(data, name):
        if e.validator == "required":
            m = re.match(r"^'(.{1,80})' is a required property$", e.message)
            message = f"missing required field '{m.group(1)}'" if m else "missing required field"
        elif e.validator == "additionalProperties" and isinstance(e.instance, dict):
            allowed = set(e.schema.get("properties", {}))
            message = "unexpected field(s): " + ", ".join(sorted(k for k in e.instance if k not in allowed))[:200]
        elif e.validator == "enum":
            message = "must be one of: " + " | ".join(map(str, e.validator_value))[:200]
        elif e.validator == "type":
            message = f"must be of type {e.validator_value}"
        elif isinstance(e.validator_value, (int, float, str)) and len(str(e.validator_value)) <= 80:
            message = f"violates {e.validator} {e.validator_value}"
        else:
            message = f"violates {e.validator}"
        item = {"path": json_path(e.absolute_path), "message": message}
        if item not in found:
            found.append(item)
    return found


def schema_check(data: Any, name: str) -> None:
    errors = _raw_schema_errors(data, name)
    if errors:
        msg = "; ".join(f"{'/'.join(map(str,e.absolute_path)) or '$'}: validation rule '{e.validator}' failed" for e in errors[:12])
        raise ContractError(msg)

def local_asset(root: Path, relative: str) -> Path:
    check(isinstance(relative, str) and bool(relative), "Asset path is required")
    check(not re.match(r"^[a-z][a-z0-9+.-]*:", relative, re.I), "Remote/data URLs are not input asset paths")
    p = (root / relative).resolve()
    check(p.is_relative_to(root.resolve()), "Asset escapes its project directory")
    check(p.is_file(), f"Missing local asset: {relative}")
    return p

def safe_script_json(value: Any) -> str:
    # Safe inside <script type=application/json> AND JS expressions.
    return canonical(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone-cn", re.compile(r"(?<!\d)(?:\+86[- ]?)?1[3-9]\d{9}(?!\d)")),
]

def privacy_findings(value: Any) -> list[dict]:
    """A heuristic release gate, NOT a guarantee that prose is anonymous."""
    found = []
    def walk(x, path):
        if isinstance(x, str):
            for kind, pattern in SECRET_PATTERNS:
                if pattern.search(x):
                    found.append({"path": path, "kind": kind})  # Never echo secrets.
        elif isinstance(x, dict):
            for k, v in x.items(): walk(v, f"{path}/{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x): walk(v, f"{path}/{i}")
    walk(value, "$")
    return found

"""Local I/O, canonical hashes and defensive validation primitives."""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
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

def schema_check(data: Any, name: str) -> None:
    from jsonschema import Draft202012Validator, FormatChecker
    validator = Draft202012Validator(load(ROOT / "schemas" / name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda e: str(list(e.absolute_path)))
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

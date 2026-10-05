#!/usr/bin/env python3
"""Inspect hash-bound art evidence or prepare UNAPPROVED review targets, locally."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from PIL import Image
from twinlight_core.art_quality import (REVIEW_CHECKS, ArtEvidenceError, check_evidence, read_json,
                                       snapshot, _manifest_assets, sha256)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "review-template", "composite"))
    parser.add_argument("--layers", type=Path, required=True)
    parser.add_argument("--persona-digest", required=True)
    parser.add_argument("--stage", choices=tuple(REVIEW_CHECKS), default="final")
    parser.add_argument("--front", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = check_evidence(args.layers, args.persona_digest, stage=args.stage, front=args.front, preview=args.preview)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 2 if result["status"].startswith("needs_") else 1
        if args.out is None:
            parser.error("--out is required for this command")
        root = args.layers.resolve().parent
        # Never overwrite sources or existing review records. Updating a review is an explicit host action.
        if args.out.exists():
            raise ValueError("Output already exists; do not overwrite an input or an existing review")
        if args.command == "composite":
            manifest = read_json(args.layers)
            if manifest.get("persona_digest") != args.persona_digest:
                raise ValueError("Manifest belongs to another persona")
            _, layers = _manifest_assets(root, manifest)
            result = layers["background"].copy()
            for role in ("spirit", "subject", "effects"):
                result = Image.alpha_composite(result, layers[role])
            if args.out.suffix.lower() != ".png":
                raise ValueError("Composite must be a PNG")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            result.save(args.out)
            print(json.dumps({"out": str(args.out), "sha256": sha256(args.out), "reviewed": False}))
        else:
            targets, _, _, _ = snapshot(args.layers, args.persona_digest, stage=args.stage, front=args.front, preview=args.preview)
            draft = {"stage": args.stage, "targets": targets[args.stage], "observer": None, "observed_at": None,
                     "decision": "pending", "checks": {key: {"passed": False, "observation": ""} for key in REVIEW_CHECKS[args.stage]},
                     "capture": None}
            if args.stage == "final":
                draft["views"] = {"left": None, "right": None, "mobile": None}
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"out": str(args.out), "decision": "pending", "automatic_approval": False}))
        return 0
    except (ArtEvidenceError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

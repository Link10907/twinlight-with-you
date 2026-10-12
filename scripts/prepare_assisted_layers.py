#!/usr/bin/env python3
"""Portable fallback: preserve a native illustration using real masks and a clean background."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from twinlight_core.cardgen import read_card_data
from twinlight_core.common import load
from twinlight_core.portable_layers import prepare_assisted
from prepare_card_layers import font_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'prototype', 'background', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    for role in ('subject', 'effects'):
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument('--' + role, type=Path)
        g.add_argument('--' + role + '-mask', type=Path)
    p.add_argument('--font', type=Path); p.add_argument('--composition', type=Path)
    a = p.parse_args()
    try:
        r = prepare_assisted(read_card_data(a.data), a.prototype, a.background, a.out, font_path(a.font),
                             subject=a.subject, subject_mask=a.subject_mask,
                             effects=a.effects, effects_mask=a.effects_mask,
                             composition=load(a.composition) if a.composition else None)
        print(json.dumps(r, ensure_ascii=False, indent=2)); return 0
    except (OSError, ValueError, KeyError) as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False)); return 2

if __name__ == '__main__': raise SystemExit(main())

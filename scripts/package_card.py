#!/usr/bin/env python3
"""Make one portable native-layer card file for the offline viewer; no image processing."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from twinlight_core.art import validate_layers
from twinlight_core.common import check, load, local_asset, save
from twinlight_core.lite import check_text, to_profile
from twinlight_core.site import uri


def package(layers: Path, out: Path, data: Path | None = None) -> dict:
    expected = None
    if data:
        parsed = check_text(data.read_text(encoding='utf-8'))
        check(parsed['ok'], '请先修正当前用户的数据')
        expected = to_profile(parsed['data'], generated_at='2000-01-01T00:00:00Z')['persona']['persona_digest']
    report = validate_layers(layers, expected)
    manifest = load(layers)
    card = {'twinlight_card': 'layers-1', 'persona_digest': manifest['persona_digest'],
            'canvas': report['size'], 'art_status': manifest['art_status'], 'depths': manifest['depths'],
            'layers': {role: uri(local_asset(layers.parent, path)) for role, path in manifest['assets'].items()}}
    if 'composition' in manifest:
        card['composition'] = manifest['composition']
    save(out, card)
    return {'ok': True, 'out': str(out), 'canvas': report['size'], 'bytes': out.stat().st_size,
            'persona_digest': manifest['persona_digest']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layers', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--data', type=Path)
    a = p.parse_args()
    print(json.dumps(package(a.layers, a.out, a.data), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

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
from twinlight_core.cardgen import read_card_data
from twinlight_core.lite import persona_digest
from twinlight_core.site import uri


def package(layers: Path, out: Path, data: Path | None = None) -> dict:
    expected = None
    if data:
        expected = persona_digest(read_card_data(data))
    report = validate_layers(layers, expected)
    manifest = load(layers)
    card = {'twinlight_card': 'layers-1', 'persona_digest': manifest['persona_digest'],
            'canvas': report['size'], 'art_status': manifest['art_status'], 'depths': manifest['depths'],
            'layers': {role: uri(local_asset(layers.parent, path)) for role, path in manifest['assets'].items()}}
    if 'canvas_mapping' in manifest:
        card['canvas_mapping'] = manifest['canvas_mapping']
    if 'composition' in manifest:
        card['composition'] = manifest['composition']
    from twinlight_core.card_handoff import renderer_contract
    card['renderer'] = renderer_contract()
    save(out, card)
    return {'ok': True, 'out': str(out), 'canvas': report['size'], 'bytes': out.stat().st_size,
            'persona_digest': manifest['persona_digest'],
            'mechanical_verified': True, 'quality_verified': False, 'browser_verified': False,
            'generation_provenance_verified': False,
            'scope': 'Native-layer packaging only; actual image-tool provenance, visual quality and interaction require separate evidence.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layers', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--data', type=Path)
    a = p.parse_args()
    print(json.dumps(package(a.layers, a.out, a.data), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Preview a completed native card independently with the same depth and foil renderer."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twinlight_core.art import validate_layers
from twinlight_core.cardgen import read_card_data
from twinlight_core.common import ROOT, check, load, local_asset, safe_script_json
from twinlight_core.lite import persona_digest
from twinlight_core.site import fill, uri


def preview(layers: Path, out: Path, data: Path | None = None) -> dict:
    content = read_card_data(data) if data else None
    expected = persona_digest(content) if content else None
    report = validate_layers(layers, expected)
    manifest = load(layers)
    persona = dict(content['card'], name=content['name'], summarizer=content['summarizer']) if content else {'title': '专属闪卡'}
    persona.update(ready=True, art_status=manifest['art_status'], art_mode='layered')
    values = {'CARD_DATA': safe_script_json(persona),
              'CARD_LAYERS': safe_script_json({role: uri(local_asset(layers.parent, path)) for role, path in manifest['assets'].items()}),
              **{'DEPTH_' + token: str(manifest['depths'][role]) for role, token in
                 [('background', 'BG'), ('subject', 'SUBJECT'), ('effects', 'EFFECTS')]}}
    src = ROOT / 'assets/card-preview'
    bootstrap = fill((src / 'bootstrap.js').read_text(encoding='utf-8'), values)
    renderer = fill((ROOT / 'assets/template/src/holo-card.js').read_text(encoding='utf-8'), values)
    check(not re.search(r'</script', bootstrap + renderer, re.I), 'Preview scripts contain a closing script tag')
    parts = {'STYLE': (src / 'style.css').read_text(encoding='utf-8'), 'BOOTSTRAP': bootstrap, 'RENDERER': renderer}
    html = re.sub(r'__(STYLE|BOOTSTRAP|RENDERER)__', lambda m: parts[m[1]], (src / 'page.html').read_text(encoding='utf-8'))
    sources = [layers, *(local_asset(layers.parent, path) for path in manifest['assets'].values())]
    check(all(out.resolve() != source.resolve() and not (out.exists() and out.samefile(source)) for source in sources),
          'Preview cannot replace source card assets')
    check(data is None or (out.resolve() != data.resolve() and not (out.exists() and out.samefile(data))),
          'Preview cannot replace card content')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    return {'ok': True, 'out': str(out), 'bytes': out.stat().st_size, 'persona_digest': manifest['persona_digest'],
            'canvas': report['size'], 'browser_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layers', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--data', type=Path)
    args = parser.parse_args()
    print(json.dumps(preview(args.layers, args.out, args.data), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

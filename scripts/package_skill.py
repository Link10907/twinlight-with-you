#!/usr/bin/env python3
"""Package maintained skill resources; never includes private runs or Git data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ('SKILL.md', 'README.md', 'START_HERE.txt', 'LICENSE',
              'THIRD-PARTY-NOTICES.md', 'requirements.txt', 'requirements-dev.txt', '.gitignore')
RESOURCE_DIRS = ('scripts', 'references', 'prompts', 'schemas', 'assets', 'agents')
SUFFIXES = {'.py', '.md', '.txt', '.json', '.js', '.css', '.html', '.svg',
            '.png', '.jpg', '.jpeg', '.webp', '.mp3', '.yaml', '.yml'}


def resource_files(root: Path) -> list[Path]:
    root = root.resolve()
    files = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for directory in RESOURCE_DIRS:
        folder = root / directory
        if folder.is_symlink():
            raise ValueError('Resource directory cannot be a symlink: ' + directory)
        if not folder.exists():
            continue
        for path in folder.rglob('*'):
            relative = path.relative_to(root)
            if any(part.startswith('.') or part == '__pycache__' for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError('Resource cannot be a symlink: ' + relative.as_posix())
            if path.is_file() and path.suffix.lower() in SUFFIXES:
                files.append(path)
    # The maintained fictional demo is runnable. The smoke-test answer stays out.
    files.extend(root / 'examples/demo' / name for name in (
        'README.md', 'history-input.json', 'history.json', 'analysis.json',
        'profile.json', 'layout.lock.json'))
    files.append(root / 'examples/layers.example.json')
    files.append(root / 'examples/smoke/history.txt')
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Missing/unsafe maintained resource: ' + path.relative_to(root).as_posix())
    if root / 'SKILL.md' not in files:
        raise ValueError('SKILL.md is required')
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def package(root: Path, out: Path) -> dict:
    root = root.resolve()
    files = resource_files(root)
    if out.resolve() in {p.resolve() for p in files}:
        raise ValueError('Archive cannot replace a skill resource')
    out.parent.mkdir(parents=True, exist_ok=True)
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with ZipFile(out, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, 'twinlight-with-you/' + path.relative_to(root).as_posix())
        archive.writestr('twinlight-with-you/package-manifest.json', json.dumps({
            'schema_version': '1.0', 'files_sha256': hashes,
            'scope': 'Maintained skill files and fictional fixtures only; no private history or grading answers.'
        }, ensure_ascii=False, indent=2))
    return {'ok': True, 'out': str(out.resolve()), 'resource_files': len(files),
            'bytes': out.stat().st_size, 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs/twinlight-with-you.zip')
    args = parser.parse_args()
    try:
        print(json.dumps(package(ROOT, args.out), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, 'Twinlight package: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())

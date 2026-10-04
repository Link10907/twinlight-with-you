#!/usr/bin/env python3
"""Package maintained skill resources; never includes private runs or Git data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ('SKILL.md', 'AGENT.md', 'PROMPT.md', 'CARD.md', 'README.md', 'START_HERE.txt', 'LICENSE',
              'THIRD-PARTY-NOTICES.md', 'requirements.txt', 'requirements-dev.txt', '.gitignore')
RESOURCE_DIRS = ('scripts', 'references', 'prompts', 'schemas', 'assets', 'agents')
# The Pages viewer is built and tested from the repository (needs examples and test fixtures).
MAINTAINER_ONLY = {'scripts/build_viewer.py', 'scripts/verify_viewer.py'}
SUFFIXES = {'.py', '.md', '.txt', '.json', '.js', '.css', '.html', '.svg',
            '.png', '.jpg', '.jpeg', '.webp', '.mp3', '.yaml', '.yml'}
EXCLUDED_PARTS = {'__pycache__', 'node_modules', 'private', 'runs', 'outputs',
                  'exports', 'local', 'verification', 'venv'}


def is_hidden_or_private(relative: Path) -> bool:
    return any(part.startswith('.') or part in EXCLUDED_PARTS for part in relative.parts)


def maintained_tree(root: Path, directory: str) -> list[Path]:
    """Read only a named maintained subtree; never traverse personal directories."""
    folder = root / directory
    if folder.is_symlink():
        raise ValueError('Resource directory cannot be a symlink: ' + directory)
    if not folder.exists():
        return []
    result = []
    for path in folder.rglob('*'):
        relative = path.relative_to(root)
        if is_hidden_or_private(relative):
            continue
        if path.is_symlink():
            raise ValueError('Resource cannot be a symlink: ' + relative.as_posix())
        if path.is_file() and path.suffix.lower() in SUFFIXES:
            result.append(path)
    return result


def resource_files(root: Path, include_demo: bool = False) -> list[Path]:
    root = root.resolve()
    files = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for directory in RESOURCE_DIRS:
        for path in maintained_tree(root, directory):
            relative = path.relative_to(root)
            if relative.as_posix() == 'prompts/06-smoke-test.txt' and not include_demo:
                continue
            if relative.as_posix() in MAINTAINER_ONLY or relative.parts[:2] == ('assets', 'viewer'):
                continue
            files.append(path)
    # Personal runs receive no example biography or prewritten interpretation.
    # Fictional fixtures are opt-in, and the grading answer always stays out.
    if include_demo:
        files.extend(root / 'examples/demo' / name for name in (
            'README.md', 'history-input.json', 'history.json', 'analysis.json',
            'profile.json', 'layout.lock.json'))
        files.append(root / 'examples/smoke/history.txt')
        files.append(root / 'examples/lite/example.json')
        files.extend(maintained_tree(root, 'examples/generated-demo'))
    files.append(root / 'examples/layers.example.json')
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Missing/unsafe maintained resource: ' + path.relative_to(root).as_posix())
    if root / 'SKILL.md' not in files:
        raise ValueError('SKILL.md is required')
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def package(root: Path, out: Path, include_demo: bool = False) -> dict:
    root = root.resolve()
    files = resource_files(root, include_demo)
    if out.resolve() in {p.resolve() for p in files}:
        raise ValueError('Archive cannot replace a skill resource')
    out.parent.mkdir(parents=True, exist_ok=True)
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with ZipFile(out, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, 'twinlight-with-you/' + path.relative_to(root).as_posix())
        archive.writestr('twinlight-with-you/package-manifest.json', json.dumps({
            'schema_version': '1.0', 'files_sha256': hashes,
            'mode': 'fictional_demo' if include_demo else 'personal_use',
            'contains_fictional_history': include_demo,
            'contains_author_showcase': False,
            'contains_generated_fictional_art': any(
                p.relative_to(root).parts[:2] == ('examples', 'generated-demo') and
                p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'} for p in files),
            'scope': ('Maintained skill files and opt-in fictional fixtures; no private history or grading answers.'
                      if include_demo else 'Skill resources only; no example history, prewritten personal analysis, or grading answers.')
        }, ensure_ascii=False, indent=2))
    return {'ok': True, 'out': str(out.resolve()), 'resource_files': len(files),
            'bytes': out.stat().st_size, 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs/twinlight-with-you.zip')
    parser.add_argument('--include-demo', action='store_true', help='Explicitly include fictional history and smoke-test inputs for demonstration')
    args = parser.parse_args()
    try:
        print(json.dumps(package(ROOT, args.out, args.include_demo), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, 'Twinlight package: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())

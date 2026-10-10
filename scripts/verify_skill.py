#!/usr/bin/env python3
"""Verify the delivered skill itself. Unit tests use SYNTHETIC data, never art approvals."""
from __future__ import annotations
import argparse,ast,datetime as dt,io,json,re,sys,unittest
from pathlib import Path
from bootstrap import check_root
from package_skill import resource_files


def verify(root: Path, tests: bool=False) -> tuple[dict,str]:
    root=root.resolve();resources=check_root(root)
    syntax_errors=[]
    for p in (root/'scripts').rglob('*.py'):
        try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        except (SyntaxError,UnicodeError) as exc:syntax_errors.append({'file':str(p.relative_to(root)),'error':str(exc)})
    broken=[]
    for name in ('SKILL.md','AGENT.md','CARD.md','HTML.md','REVIEWER.md','README.md'):
        source=root/name
        if not source.is_file():continue
        for dest in re.findall(r'\]\(([^)]+)\)',source.read_text(encoding='utf-8')):
            dest=dest.split('#')[0]
            if not dest or '://' in dest or dest.startswith('mailto:'):continue
            if not (source.parent/dest).exists():broken.append({'file':name,'target':dest})
    files=resource_files(root)
    from twinlight_core.navigation import manifest
    navigation_lock=manifest(root/'assets/navigation')
    forbidden=[str(p.relative_to(root)) for p in files if p.suffix.lower() in ('.ttf','.ttc','.otf','.woff','.woff2')]
    report={'version':'skill-verification-2','verified_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'resource_complete':resources['resource_complete'],'package_manifest_verified':resources['package_manifest_verified'],
            'template_lock':resources['template_lock'],'navigation_lock':navigation_lock,'runtime':resources['runtime'],
            'missing_resources':resources['missing_resources'],'syntax_errors':syntax_errors,'broken_entry_links':broken,
            'forbidden_distributed_fonts':forbidden,'resource_file_count':len(files),
            'tests':{'executed':False},'real_image_generation_performed':False,
            'real_independent_reviewer_invoked':False,'new_artwork_approved':False,
            'scope':'Skill integrity and synthetic regression tests, not end-to-end artistic acceptance or host/provider certification.'}
    log=''
    if tests:
        sys.path.insert(0,str(root/'scripts'))
        suite=unittest.defaultTestLoader.discover(str(root/'tests/quality'),pattern='test_*.py')
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);log=stream.getvalue()
        report['tests']={'executed':True,'run':result.testsRun,'failures':len(result.failures),
                         'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),
                         'fixture_scope':'SYNTHETIC ONLY; fake test receipts cannot be reused for delivery.'}
    report['ok']=resources['ok'] and not syntax_errors and not forbidden and not broken and (not tests or report['tests']['passed'])
    return report,log


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--tests',action='store_true');p.add_argument('--out',type=Path)
    a=p.parse_args(argv)
    try:
        r,log=verify(a.root,a.tests)
        if a.out:
            a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            if log:a.out.with_suffix('.log').write_text(log,encoding='utf-8')
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['ok'] else 2
    except (OSError,ValueError,ImportError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));return 2

if __name__=='__main__':raise SystemExit(main())

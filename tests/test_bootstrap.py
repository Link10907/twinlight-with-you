"""Acquisition must fail explicitly rather than permit a substitute design."""
import io
import hashlib
import json
import stat
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bootstrap

SHA = 'a' * 40


def archive(extra=(), omit=()):
    stream = io.BytesIO()
    template_files = {name: hashlib.sha256(b'maintained resource').hexdigest()
                      for name in bootstrap.REQUIRED
                      if name.startswith('assets/template/') and not name.endswith('template-lock.json')}
    lock = {'schema_version': 'template-lock-1', 'builder_version': 'test',
            'source_files_sha256': template_files, 'assembled_template_sha256': '0' * 64}
    with zipfile.ZipFile(stream, 'w') as zipped:
        for name in bootstrap.REQUIRED:
            if name not in omit:
                content = ('maintained resource' if name != 'assets/template/template-lock.json'
                           else json.dumps(lock))
                if name == 'scripts/twinlight_core/template_lock.py':
                    content = (ROOT / name).read_text()
                zipped.writestr('twinlight-with-you-' + SHA + '/' + name, content)
        for name, content in extra:
            zipped.writestr(name, content)
    return stream.getvalue()


class ResourceBootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'resources'

    def test_resolves_branch_once_then_uses_immutable_revision(self):
        with patch.object(bootstrap, 'fetch', return_value=json.dumps({'sha': SHA}).encode()) as fetch:
            self.assertEqual(bootstrap.resolve_revision(None), SHA)
            self.assertIn('/commits/main', fetch.call_args.args[0])
        for invalid in ('main', '../main', '', 'https://example.com/archive'):
            with self.assertRaises(ValueError):
                bootstrap.resolve_revision(invalid)

    def test_complete_acquisition_and_resource_hashes(self):
        bootstrap.unpack(archive(), self.out, SHA)
        with patch.object(bootstrap.importlib, 'import_module', return_value=types.SimpleNamespace(__version__='test')):
            result = bootstrap.check_root(self.out)
        self.assertTrue(result['ok'])
        self.assertEqual(set(result['required_files_sha256']), set(bootstrap.REQUIRED))
        self.assertFalse(list(self.out.rglob('*.html'))[0].read_bytes().startswith(b'<!doctype'))

    def test_missing_fixed_template_rejected_before_any_writes(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            bootstrap.unpack(archive(omit=('assets/template/src/v10.js',)), self.out, SHA)
        self.assertFalse(self.out.exists())

    def test_archive_escape_and_symlink_rejected_before_any_writes(self):
        for name in ('../escape', '/absolute', 'bad\\name'):
            payload = archive(extra=[('twinlight-with-you-' + SHA + '/' + name, 'bad')])
            with self.assertRaises(ValueError):
                bootstrap.unpack(payload, self.out, SHA)
            self.assertFalse(self.out.exists())
        info = zipfile.ZipInfo('twinlight-with-you-' + SHA + '/symlink')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        stream = io.BytesIO(archive())
        with zipfile.ZipFile(stream, 'a') as zipped:
            zipped.writestr(info, 'elsewhere')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            bootstrap.unpack(stream.getvalue(), self.out, SHA)
        self.assertFalse(self.out.exists())

    def test_preserves_existing_work_on_incomplete_acquisition(self):
        self.out.mkdir()
        original = self.out / 'personal.html'
        original.write_text('keep this')
        with self.assertRaisesRegex(ValueError, 'new or empty'):
            bootstrap.unpack(archive(), self.out, SHA)
        self.assertEqual(original.read_text(), 'keep this')

    def test_runtime_and_package_mismatch_do_not_claim_ready(self):
        bootstrap.unpack(archive(), self.out, SHA)
        with patch.object(bootstrap.importlib, 'import_module', side_effect=ImportError('unavailable')):
            result = bootstrap.check_root(self.out)
        self.assertTrue(result['resource_complete'])
        self.assertFalse(result['ok'])
        self.assertEqual(result['runtime']['missing_dependencies'], ['jsonschema', 'PIL', 'playwright'])
        (self.out / 'package-manifest.json').write_text(json.dumps({'files_sha256': {'PROMPT.md': '0' * 64}}))
        with patch.object(bootstrap.importlib, 'import_module', return_value=types.SimpleNamespace(__version__='test')):
            result = bootstrap.check_root(self.out)
        self.assertFalse(result['ok'])
        self.assertFalse(result['package_manifest_verified'])

    def test_modified_template_rejected_before_any_personal_build(self):
        bootstrap.unpack(archive(), self.out, SHA)
        (self.out / 'assets/template/src/v10.css').write_text('different local design')
        result = bootstrap.check_root(self.out)
        self.assertTrue(result['resource_complete'])
        self.assertFalse(result['template_lock']['ok'])
        self.assertFalse(result['ok'])
        self.assertIn('locked_template_source_changed',
                      {error['code'] for error in result['template_lock']['errors']})

    def test_missing_visual_anchor_rejected_before_any_writes(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            bootstrap.unpack(archive(omit=('assets/art-references/twinlight-collector/prototype.png',)), self.out, SHA)
        self.assertFalse(self.out.exists())

    def test_browser_preflight_honors_an_unavailable_explicit_executable(self):
        with patch.dict(bootstrap.os.environ, {'TWINLIGHT_BROWSER': str(self.out / 'missing-browser')}):
            result = bootstrap.browser_preflight()
        self.assertFalse(result['executable_available'])
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('--browser', result['next'])


if __name__ == '__main__':
    unittest.main()

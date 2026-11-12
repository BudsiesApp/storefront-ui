import importlib.util
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('preview', ROOT / 'scripts/preview-packages.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)
publisher = preview.load('publish-release')


class FakeGitHub:
    def __init__(self, assets=None, exists=False, tag_sha=None):
        self.assets = dict(assets or {})
        self.exists, self.tag_sha, self.writes = exists, tag_sha, []

    def commit(self, ref):
        return self.tag_sha if ref.startswith('package-preview-') else ref

    def existing_commit(self, tag): return self.tag_sha
    def release(self, tag):
        return {'assets': [{'name': name, 'id': name} for name in self.assets]} if self.exists else None
    def download(self, asset): return self.assets[asset['id']]
    def create(self, tag, target): self.writes.append('create'); self.exists = True; self.tag_sha = target
    def upload(self, tag, path): self.writes.append(path.name); self.assets[path.name] = path.read_bytes()


class PreviewTests(unittest.TestCase):
    def test_missing_tag_uses_reference_endpoint(self):
        result = subprocess.CompletedProcess([], 1, b'', b'gh: Not Found (HTTP 404)')
        with patch.object(publisher, 'run', return_value=result) as call:
            self.assertIsNone(publisher.GitHub().existing_commit('package-preview-' + 'a' * 64))
            self.assertIn('/git/ref/tags/', call.call_args.args[2])

    def test_selected_commit_preparation(self):
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        source = {'shared': sha, 'vue': sha}
        value = preview.identity(sha, source, {'python': 'test', 'zlib': 'test'})
        tag = preview.tag_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            preview.load('package-release').prepare(path, tag, {'sharedRevision': sha, 'vueRevision': sha}, value)
            metadata = json.loads((path / 'release-manifest.json').read_text())
            self.assertEqual(metadata['previewIdentity'], value)
            self.assertTrue(all(package['sourceRevision'] == sha for package in metadata['packages']))
            with tarfile.open(path / 'storefront-ui-vue.tgz') as archive:
                manifest = json.load(archive.extractfile('package/package.json'))
            self.assertEqual(manifest['dependencies']['@storefront-ui/shared'],
                             f'https://github.com/{preview.REPOSITORY}/releases/download/{tag}/storefront-ui-shared.tgz')

    def test_identity_and_resolution(self):
        value = preview.identity('a' * 40, {'shared': 'b' * 40, 'vue': 'c' * 40}, {'python': '3.11', 'zlib': '1.2'})
        self.assertEqual(preview.tag_for(value), preview.tag_for(json.loads(json.dumps(value))))
        for key, changed in [('packagingRevision', 'd' * 40), ('sources', {'shared': 'e' * 40, 'vue': 'c' * 40}),
                             ('toolchain', {'python': '3.12', 'zlib': '1.2'})]:
            self.assertNotEqual(preview.tag_for(value), preview.tag_for({**value, key: changed}))
        calls = []
        def fake_git(*args):
            calls.append(args)
            return 'a' * 40 if args[0] == 'rev-parse' else ''
        with patch.object(preview, 'git', fake_git):
            self.assertEqual(preview.resolve('feature/foo'), 'a' * 40)
            self.assertEqual(sum(call[0] == 'fetch' for call in calls), 1)
            with self.assertRaises(ValueError): preview.resolve('--upload-pack=bad')
        with patch.object(preview, 'resolve', return_value='a' * 40) as resolver:
            self.assertEqual(preview.resolve_sources('same', 'same'), {'shared': 'a' * 40, 'vue': 'a' * 40})
            resolver.assert_called_once_with('same')

    def test_publication_reuse_conflicts_and_partial(self):
        tag, sha = 'package-preview-' + 'a' * 64, 'b' * 40
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in publisher.ASSETS: (directory / name).write_bytes(name.encode())
            (directory / 'release-manifest.json').write_text(json.dumps({'releaseTag': tag, 'packagingRevision': sha}))
            expected = {name: (directory / name).read_bytes() for name in publisher.ASSETS}
            for initial, exists, oldsha in (({}, False, None), (expected, True, sha),
                                            ({publisher.ASSETS[0]: expected[publisher.ASSETS[0]]}, True, sha)):
                fake = FakeGitHub(initial, exists, oldsha)
                publisher.publish(fake, tag, directory, preview=True)
                self.assertEqual(fake.assets, expected)
                if initial == expected: self.assertEqual(fake.writes, [])
            for initial, oldsha in (({'SHA256SUMS': b'bad'}, sha), ({}, 'c' * 40)):
                fake = FakeGitHub(initial, bool(initial), oldsha)
                with self.assertRaises(ValueError): publisher.publish(fake, tag, directory, preview=True)
                self.assertEqual(fake.assets, initial)
                self.assertEqual(fake.writes, [])
            for stage in ('create', 'upload'):
                fake = FakeGitHub()
                with patch.object(fake, stage, side_effect=RuntimeError('race')):
                    with self.assertRaises(RuntimeError): publisher.publish(fake, tag, directory, preview=True)


if __name__ == '__main__': unittest.main()

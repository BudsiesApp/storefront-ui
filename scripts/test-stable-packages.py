import importlib.util
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('stable', ROOT / 'scripts/publish-stable.py')
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)
publisher = stable.load('publish-release')
package = stable.load('package-release')


class FakeGitHub:
    def __init__(self, sha, assets=None, tag_sha=None, release=False, prerelease=False):
        self.sha, self.assets, self.tag_sha = sha, dict(assets or {}), tag_sha
        self.exists, self.prerelease, self.writes = release, prerelease, []

    def commit(self, ref): return self.tag_sha if ref.startswith('stable-packages-') else ref
    def existing_commit(self, tag): return self.tag_sha
    def release(self, tag):
        return {'draft': False, 'prerelease': self.prerelease,
                'assets': [{'name': k, 'id': k} for k in self.assets]} if self.exists else None
    def download(self, asset): return self.assets[asset['id']]
    def create_stable(self, tag, target): self.writes.append('create'); self.exists = True; self.tag_sha = target
    def upload(self, tag, path): self.writes.append(path.name); self.assets[path.name] = path.read_bytes()


class StableTests(unittest.TestCase):
    def test_trigger_and_exact_checkout(self):
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        env = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/optimuspro', 'GITHUB_SHA': sha}
        self.assertEqual(stable.selected_commit(env), sha)
        for replacement in ({'GITHUB_REF': 'refs/heads/feature'}, {'GITHUB_EVENT_NAME': 'pull_request'},
                            {'GITHUB_SHA': 'a' * 40}, {'GITHUB_SHA': 'short'}):
            with self.assertRaises(ValueError): stable.selected_commit({**env, **replacement})
        workflow = (ROOT / '.github/workflows/publish-stable-packages.yml').read_text()
        self.assertIn('branches:\n      - optimuspro', workflow)
        self.assertIn('ref: ${{ github.sha }}', workflow)
        self.assertIn('python scripts/publish-stable.py', workflow)

    def test_each_selected_commit_and_archive(self):
        for ref in ('HEAD', 'HEAD^'):
            sha = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
            tag = 'stable-packages-' + sha
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                package.prepare(path, tag, {'sharedRevision': sha, 'vueRevision': sha})
                metadata = json.loads((path / 'release-manifest.json').read_text())
                self.assertEqual([p['sourceRevision'] for p in metadata['packages']], [sha, sha])
                for item in metadata['packages']:
                    source = subprocess.check_output(['git', 'archive', sha, item['sourcePath']], cwd=ROOT)
                    with tarfile.open(fileobj=io.BytesIO(source)) as original, tarfile.open(path / item['asset']) as archive:
                        expected = {m.name[len(item['sourcePath']) + 1:]: original.extractfile(m).read()
                                    for m in original if m.isfile() and m.name.startswith(item['sourcePath'] + '/')}
                        actual = {m.name.removeprefix('package/'): archive.extractfile(m).read() for m in archive if m.isfile()}
                    if item['sourcePath'] == 'packages/vue':
                        old = json.loads(expected.pop('package.json')); new = json.loads(actual.pop('package.json'))
                        old['scripts'].pop('postinstall', None); old['scripts'].pop('prepublish', None)
                        old['dependencies']['@storefront-ui/shared'] = f'https://github.com/BudsiesApp/storefront-ui/releases/download/{tag}/storefront-ui-shared.tgz'
                        self.assertEqual(old, new)
                        actual.pop('index.js'); actual.pop('storiesOf.js')
                    self.assertEqual(expected, actual)

    def test_reuse_partial_and_collisions(self):
        sha = 'a' * 40; tag = 'stable-packages-' + sha
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for name in publisher.ASSETS: (path / name).write_bytes(name.encode())
            (path / 'release-manifest.json').write_text(json.dumps({'releaseTag': tag, 'packagingRevision': sha, 'packages': [{'sourceRevision': sha}]}))
            expected = {name: (path / name).read_bytes() for name in publisher.ASSETS}
            for assets, exists, oldsha in (({}, False, None), (expected, True, sha), ({publisher.ASSETS[0]: expected[publisher.ASSETS[0]]}, True, sha)):
                fake = FakeGitHub(sha, assets, oldsha, exists)
                publisher.publish(fake, tag, path, stable=True)
                self.assertEqual(fake.assets, expected)
                if assets == expected: self.assertEqual(fake.writes, [])
            for fake in (FakeGitHub(sha, {'SHA256SUMS': b'bad'}, sha, True),
                         FakeGitHub(sha, {}, 'b' * 40), FakeGitHub(sha, {}, sha, True, True)):
                with self.assertRaises(ValueError): publisher.publish(fake, tag, path, stable=True)
                self.assertEqual(fake.writes, [])
            (path / 'release-manifest.json').write_text(json.dumps({'releaseTag': tag, 'packagingRevision': sha, 'packages': [{'sourceRevision': 'b' * 40}]}))
            fake = FakeGitHub(sha)
            with self.assertRaises(ValueError): publisher.publish(fake, tag, path, stable=True)
            self.assertEqual(fake.writes, [])


if __name__ == '__main__': unittest.main()

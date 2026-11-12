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
    def __init__(self, sha, assets=None, tag_sha=None, release=False, prerelease=False, title=None, draft=False):
        self.sha, self.assets, self.tag_sha = sha, dict(assets or {}), tag_sha
        self.exists, self.prerelease, self.title, self.draft, self.writes = release, prerelease, title, draft, []

    def commit(self, ref): return self.tag_sha if ref.startswith('optimuspro_') else ref
    def existing_commit(self, tag): return self.tag_sha
    def release(self, tag):
        return {'draft': self.draft, 'prerelease': self.prerelease, 'name': self.title if self.title is not None else tag,
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

    def test_main_uses_branch_and_seven_commit_characters(self):
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        env = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/optimuspro', 'GITHUB_SHA': sha}
        with patch.dict('os.environ', env), patch.object(package, 'prepare') as prepare, \
             patch.object(publisher, 'GitHub') as github, patch.object(publisher, 'publish') as publish, \
             patch.object(stable, 'load', side_effect=[package, publisher]):
            stable.main()
        tag = 'optimuspro_' + sha[:7]
        self.assertEqual(prepare.call_args.args[1:], (tag, {'sharedRevision': sha, 'vueRevision': sha}))
        self.assertEqual(publish.call_args.args[:2], (github.return_value, tag))
        self.assertEqual(publish.call_args.kwargs, {'stable': True})

    def test_stable_release_title(self):
        with patch.object(publisher, 'run') as run:
            publisher.GitHub().create_stable('optimuspro_3ce1230', '3ce1230' + 'a' * 33)
        args = run.call_args.args
        self.assertEqual(args[args.index('--title') + 1], 'optimuspro_3ce1230')

    def test_arbitrary_explicit_package_tag_is_not_treated_as_stable(self):
        sha = 'a' * 40
        class ExplicitGitHub(FakeGitHub):
            def commit(self, ref): return sha
            def create(self, tag): self.writes.append('create'); self.exists = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for name in publisher.ASSETS: (path / name).write_bytes(name.encode())
            for tag in ('packages-test', 'packages-optimuspro_aaaaaaa', 'packages-stable-packages-' + sha):
                (path / 'release-manifest.json').write_text(json.dumps({'releaseTag': tag, 'packagingRevision': sha, 'packages': [{'sourceRevision': 'b' * 40}]}))
                fake = ExplicitGitHub(sha)
                publisher.publish(fake, tag, path)
                self.assertEqual(fake.writes, ['create', *publisher.ASSETS])

    def test_each_selected_commit_and_archive(self):
        for ref in ('HEAD', 'HEAD^'):
            sha = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
            tag = 'optimuspro_' + sha[:7]
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
        sha = 'a' * 40; tag = 'optimuspro_' + sha[:7]
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
                         FakeGitHub(sha, {}, 'a' * 7 + 'b' * 33),
                         FakeGitHub(sha, {}, 'a' * 7 + 'b' * 33, True),
                         FakeGitHub(sha, {}, sha, True, True),
                         FakeGitHub(sha, {}, sha, True, title='wrong'),
                         FakeGitHub(sha, {}, sha, True, draft=True)):
                with self.assertRaises(ValueError): publisher.publish(fake, tag, path, stable=True)
                self.assertEqual(fake.writes, [])
            (path / 'release-manifest.json').write_text(json.dumps({'releaseTag': tag, 'packagingRevision': sha, 'packages': [{'sourceRevision': 'b' * 40}]}))
            fake = FakeGitHub(sha)
            with self.assertRaises(ValueError): publisher.publish(fake, tag, path, stable=True)
            self.assertEqual(fake.writes, [])
            for revision, invalid_tag in ((sha, 'optimuspro_' + sha[:8]), ('a' * 7, 'optimuspro_' + sha[:7]),
                                          (sha, 'stable-packages-' + sha)):
                (path / 'release-manifest.json').write_text(json.dumps({'releaseTag': invalid_tag, 'packagingRevision': revision, 'packages': [{'sourceRevision': revision}]}))
                fake = FakeGitHub(sha)
                with self.assertRaises(ValueError): publisher.publish(fake, invalid_tag, path, stable=True)
                self.assertEqual(fake.writes, [])


if __name__ == '__main__': unittest.main()

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('branch_preview', ROOT / 'scripts/publish-branch-preview.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)
cleaner = preview.load('preview-cleanup')


class BranchPreviewTests(unittest.TestCase):
    def test_workflow_uses_push_commit_and_waits_for_cleanup_support(self):
        workflow = (ROOT / '.github/workflows/publish-branch-preview.yml').read_text()
        self.assertIn('ref: ${{ github.sha }}', workflow)
        self.assertIn("'!preview-cleanup/**'", workflow)
        self.assertIn('BRANCH_PREVIEW_FORMAT = 1', workflow)
        self.assertIn("steps.cleanup_support.outputs.enabled == 'true'", workflow)
        self.assertIn('group: preview-cleanup-${{ github.repository }}', workflow)
        self.assertIn('queue: max', workflow)

    def test_exact_push_and_exclusions(self):
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        env = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/fix/example', 'GITHUB_SHA': sha}
        self.assertEqual(preview.selected_push(env, 'develop', cleaner), ('fix/example', sha))
        for ref in ('refs/heads/optimuspro', 'refs/heads/develop', 'refs/heads/preview-cleanup/registry', 'refs/tags/v1'):
            with self.assertRaises(ValueError):
                preview.selected_push({**env, 'GITHUB_REF': ref}, 'develop', cleaner)
        for change in ({'GITHUB_EVENT_NAME': 'pull_request'}, {'GITHUB_SHA': 'bad'}, {'GITHUB_SHA': 'a' * 40}):
            with self.assertRaises(ValueError):
                preview.selected_push({**env, **change}, 'develop', cleaner)

    def test_publication_tracks_branch_and_encodes_asset_url(self):
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        env = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/fix/example', 'GITHUB_SHA': sha}
        package, publisher = preview.load('package-release'), preview.load('publish-release')
        class Tracking:
            def __init__(self): self.rel, self.registry, self.protection = None, None, False
            def repository(self): return {'full_name': preview.REPOSITORY, 'default_branch': 'develop'}
            def lock(self, anchor): return contextlib.nullcontext()
            def protection_if_present(self, name): return self.protection
            def read_registry(self): return ({'version': 1, 'repository': preview.REPOSITORY, 'previews': {}}, None)
            def release(self, tag): return self.rel
            def ref(self, tag): return None
            def write_registry(self, registry, parent, anchor): self.registry = registry
        tracking = Tracking(); stdout = io.StringIO(); captured = {}
        def publish(api, tag, path, **kwargs):
            captured['kwargs'] = kwargs
            with tarfile.open(path / 'storefront-ui-vue.tgz') as archive:
                captured['shared'] = json.load(archive.extractfile('package/package.json'))['dependencies']['@storefront-ui/shared']
            tracking.rel = {'id': 42, 'tag_name': tag, 'name': tag, 'draft': False, 'prerelease': True}
        def load(name): return {'package-release': package, 'publish-release': publisher, 'preview-cleanup': cleaner}[name]
        with patch.dict(os.environ, env), patch.object(preview, 'load', load), \
             patch.object(cleaner, 'GitHub', return_value=tracking), patch.object(publisher, 'GitHub'), \
             patch.object(publisher, 'publish', side_effect=publish), contextlib.redirect_stdout(stdout):
            preview.main()
        result = json.loads(stdout.getvalue())
        self.assertEqual(result['releaseTag'], 'fix/example_' + sha[:7])
        self.assertTrue(result['cleanupTracked'])
        self.assertEqual(result['identity']['sources'], {'shared': sha, 'vue': sha})
        self.assertIn('/fix%2Fexample_', result['manifestUrl'])
        self.assertEqual(captured['shared'], result['packages'][0]['url'])
        self.assertEqual(captured['kwargs'], {'preview': True})
        record = tracking.registry['previews'][result['releaseTag']]
        self.assertEqual(record['branches'], {'fix/example': None})
        self.assertFalse(record['pinned'])
        for protection in (True, None):
            tracking.rel, tracking.registry, tracking.protection = None, None, protection
            with patch.dict(os.environ, env), patch.object(preview, 'load', load), \
                 patch.object(cleaner, 'GitHub', return_value=tracking), patch.object(publisher, 'GitHub'), \
                 patch.object(publisher, 'publish', side_effect=publish), contextlib.redirect_stdout(io.StringIO()):
                preview.main()
            self.assertTrue(tracking.registry['previews'][result['releaseTag']]['pinned'])


if __name__ == '__main__': unittest.main()

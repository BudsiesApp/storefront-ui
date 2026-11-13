import hashlib
import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('cleanup', ROOT / 'scripts/preview-cleanup.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)
NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)
SHA = 'a' * 40


class FakeGitHub:
    def __init__(self):
        self.identity = {'repository': cleanup.REPOSITORY, 'packagingRevision': SHA, 'sources': {'a': SHA}}
        self.tag = 'package-preview-' + hashlib.sha256(json.dumps(self.identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.manifest = {'previewIdentity': self.identity, 'releaseTag': self.tag, 'packagingRevision': SHA}
        self.rel = {'id': 123, 'tag_name': self.tag, 'name': self.tag, 'draft': False, 'prerelease': True,
                    'assets': [{'name': 'release-manifest.json', 'id': 10}]}
        self.branches, self.deletes, self.saves = {}, [], 0
    def repository(self): return {'full_name': cleanup.REPOSITORY, 'default_branch': 'develop'}
    def release(self, tag): return self.rel if tag == self.tag else None
    def ref(self, tag): return {'object': {'type': 'commit', 'sha': SHA}}
    def asset(self, ident): return json.dumps(self.manifest).encode()
    def protected(self, name): return False
    def branch(self, name):
        value = self.branches.get(name, False)
        if isinstance(value, Exception): raise value
        if isinstance(value, list): return value.pop(0)
        return value
    def delete_release(self, ident): self.deletes.append(ident)
    def save(self): self.saves += 1
    def registry(self, branches=None, pinned=False):
        return {'version': 1, 'repository': cleanup.REPOSITORY, 'previews': {
            self.tag: {'release_id': 123, 'packaging': SHA, 'pinned': pinned,
                       'branches': dict(branches or {'feature/a': None})}}}


class CleanupTests(unittest.TestCase):
    def test_repository_endpoint_has_no_trailing_slash(self):
        self.assertEqual(cleanup.GitHub().path(''), 'repos/' + cleanup.REPOSITORY)

    def test_encoded_tag_and_deleted_branch_protection(self):
        api = cleanup.GitHub()
        with patch.object(api, 'call', return_value=None) as call:
            self.assertIsNone(api.release('feature/a_aaaaaaa'))
            self.assertTrue(call.call_args.args[1].endswith('/releases/tags/feature%2Fa_aaaaaaa'))
            self.assertIsNone(api.protection_if_present('feature/a'))
            with self.assertRaises(ValueError): api.protected('feature/a')
        with patch.object(api, 'call', return_value={'protected': True}):
            self.assertTrue(api.protection_if_present('feature/a'))
        with patch.object(api, 'call', return_value={}):
            with self.assertRaises(ValueError): api.protection_if_present('feature/a')

    def test_registry_commit_uses_parent_tree_and_fast_forward(self):
        api = cleanup.GitHub(); calls = []
        def call(method, path, data=None, **kwargs):
            calls.append((method, path, data))
            if method == 'GET': return {'tree': {'sha': 'base'}}
            if path.endswith('/git/trees'): return {'sha': 'tree'}
            if path.endswith('/git/commits'): return {'sha': 'commit'}
            return None
        registry = {'version': 1, 'repository': cleanup.REPOSITORY, 'previews': {}}
        with patch.object(api, 'call', side_effect=call):
            self.assertEqual(api.write_registry(registry, None, SHA), 'commit')
            self.assertEqual(calls[1][2]['base_tree'], 'base')
            self.assertEqual(calls[2][2]['parents'], [SHA])
            self.assertEqual(calls[3][2]['ref'], 'refs/heads/' + cleanup.REGISTRY)
            calls.clear()
            api.write_registry(registry, 'parent', SHA)
            self.assertEqual(calls[2][2]['parents'], ['parent'])
            self.assertEqual(calls[3][0], 'PATCH')
            self.assertFalse(calls[3][2]['force'])

    def test_associations_and_defaults(self):
        self.assertEqual(cleanup.associations(('feature/a', SHA), (False, True), 'develop'), ({'feature/a'}, False))
        self.assertEqual(cleanup.associations(('refs/heads/feature/a', 'feature/b'), (False, False), 'develop'), ({'feature/a', 'feature/b'}, False))
        self.assertEqual(cleanup.associations(('feature/a', SHA), (False, False), 'develop'), ({'feature/a'}, True))
        for ref in ('optimuspro', 'develop', 'master', 'main', 'preview-cleanup/registry', SHA, 'refs/tags/example'):
            self.assertTrue(cleanup.associations((ref,), (False,), 'develop')[1])
        for ref in ('release/v1', 'next', '0.10.9'):
            self.assertEqual(cleanup.associations((ref,), (False,), 'develop'), ({ref}, False))
        self.assertEqual(cleanup.associations(('37220-example',), (False,), 'develop'), ({'37220-example'}, False))

    def test_registration_preserves_unknown_and_pins_commit_reuse(self):
        api = FakeGitHub(); registry = {'version': 1, 'repository': cleanup.REPOSITORY, 'previews': {}}
        self.assertFalse(cleanup.register(registry, api.tag, api.rel, SHA, {'feature/a'}, False, True))
        self.assertEqual(registry['previews'], {})
        self.assertTrue(cleanup.register(registry, api.tag, api.rel, SHA, {'feature/a'}, False, False))
        self.assertTrue(cleanup.register(registry, api.tag, api.rel, SHA, {'feature/b'}, False, True))
        self.assertEqual(set(registry['previews'][api.tag]['branches']), {'feature/a', 'feature/b'})
        self.assertTrue(cleanup.register(registry, api.tag, api.rel, SHA, set(), True, True))
        self.assertTrue(registry['previews'][api.tag]['pinned'])
        self.assertFalse(cleanup.register(registry, api.tag, api.rel, SHA, set(), True, True))
        with self.assertRaises(ValueError): cleanup.register(registry, api.tag, {**api.rel, 'id': 124}, SHA, set(), False, True)
        self.assertTrue(cleanup.register(registry, api.tag, {**api.rel, 'id': 124}, SHA, {'feature/c'}, False, False))
        self.assertTrue(registry['previews'][api.tag]['pinned'])
        self.assertEqual(set(registry['previews'][api.tag]['branches']), {'feature/a', 'feature/b', 'feature/c'})

    def test_branch_becoming_protected_pins_preview(self):
        api = FakeGitHub(); registry = api.registry({'feature/a': None})
        api.branches['feature/a'] = True
        api.protected = lambda name: True
        cleanup.cleanup(api, registry, NOW, api.save)
        self.assertTrue(registry['previews'][api.tag]['pinned'])
        self.assertEqual(api.saves, 1)

    def test_all_branches_must_be_deleted_and_aged(self):
        api = FakeGitHub(); registry = api.registry({'feature/a': None, 'feature/b': None})
        api.branches = {'feature/a': False, 'feature/b': True}
        cleanup.cleanup(api, registry, NOW, api.save)
        self.assertEqual(registry['previews'][api.tag]['branches']['feature/a'], NOW.isoformat())
        self.assertEqual(api.deletes, [])
        api.branches['feature/b'] = False
        cleanup.cleanup(api, registry, NOW + timedelta(days=10), api.save)
        cleanup.cleanup(api, registry, NOW + timedelta(days=30), api.save)
        self.assertEqual(api.deletes, [])
        cleanup.cleanup(api, registry, NOW + timedelta(days=40), api.save)
        self.assertEqual(api.deletes, [123])

    def test_reappearance_resets_age_including_final_check(self):
        api = FakeGitHub(); old = (NOW - timedelta(days=31)).isoformat()
        registry = api.registry({'feature/a': old})
        api.branches = {'feature/a': [False, True]}
        cleanup.cleanup(api, registry, NOW, api.save)
        self.assertIsNone(registry['previews'][api.tag]['branches']['feature/a'])
        self.assertEqual(api.deletes, [])
        api.branches = {'feature/a': False}
        cleanup.cleanup(api, registry, NOW + timedelta(days=1), api.save)
        cleanup.cleanup(api, registry, NOW + timedelta(days=30), api.save)
        self.assertEqual(api.deletes, [])
        cleanup.cleanup(api, registry, NOW + timedelta(days=31), api.save)
        self.assertEqual(api.deletes, [123])

    def test_error_pins_and_release_checks_fail_safe(self):
        api = FakeGitHub(); old = (NOW - timedelta(days=31)).isoformat()
        registry = api.registry({'feature/a': old})
        api.branches['feature/a'] = RuntimeError('unavailable')
        with self.assertRaises(RuntimeError): cleanup.cleanup(api, registry, NOW, api.save)
        self.assertEqual(api.deletes, [])
        api.branches['feature/a'] = False
        for changes in ({'prerelease': False}, {'draft': True}, {'name': 'different'}, {'id': 124}):
            original = api.rel; api.rel = {**original, **changes}
            cleanup.cleanup(api, registry, NOW, api.save)
            self.assertEqual(api.deletes, []); api.rel = original
        api.manifest['previewIdentity']['repository'] = 'other'
        cleanup.cleanup(api, registry, NOW, api.save)
        self.assertEqual(api.deletes, [])
        api = FakeGitHub()
        for registry in (api.registry({'feature/a': old}, True), api.registry({'optimuspro': old})):
            cleanup.cleanup(api, registry, NOW, api.save)
            self.assertEqual(api.deletes, [])

    def test_dry_run_does_not_delete_or_save(self):
        api = FakeGitHub(); registry = api.registry({'feature/a': (NOW - timedelta(days=31)).isoformat()})
        cleanup.cleanup(api, registry, NOW, api.save, dry_run=True)
        self.assertEqual(api.deletes, []); self.assertEqual(api.saves, 0)

    def test_branch_named_preview_requires_matching_provenance(self):
        api = FakeGitHub(); branch = 'feature/a'; api.tag = branch + '_' + SHA[:7]
        api.identity = {'formatVersion': 1, 'repository': cleanup.REPOSITORY, 'packagingRevision': SHA, 'branch': branch,
                        'sources': {'shared': SHA, 'vue': SHA}}
        api.manifest = {'repository': cleanup.REPOSITORY, 'previewIdentity': api.identity, 'releaseTag': api.tag,
                        'packagingRevision': SHA, 'packages': [{'name': '@storefront-ui/shared', 'sourceRevision': SHA},
                                                               {'name': '@storefront-ui/vue', 'sourceRevision': SHA}]}
        api.rel.update(tag_name=api.tag, name=api.tag)
        registry = api.registry({branch: (NOW - timedelta(days=31)).isoformat()})
        cleanup.validate_registry(registry)
        api.identity['sources']['vue'] = 'b' * 40
        cleanup.cleanup(api, registry, NOW, api.save)
        self.assertEqual(api.deletes, [])
        api.identity['sources']['vue'] = SHA
        cleanup.cleanup(api, registry, NOW, api.save)
        self.assertEqual(api.deletes, [123])

    def test_lock_contention_fails_without_stealing(self):
        api = cleanup.GitHub(); held = set(); calls = []
        def call(method, path, data=None, **kwargs):
            calls.append(method)
            if method == 'POST':
                if held: raise RuntimeError('already locked')
                held.add('lock')
            elif method == 'DELETE': held.clear()
        with patch.object(api, 'call', side_effect=call):
            with api.lock(SHA):
                with self.assertRaises(RuntimeError):
                    with api.lock(SHA): self.fail('lock stolen')
                self.assertTrue(held)
        self.assertEqual(calls, ['POST', 'POST', 'DELETE'])

    def test_failed_publication_leaves_lock_for_safe_recovery(self):
        api = cleanup.GitHub(); calls = []
        with patch.object(api, 'call', side_effect=lambda method, *args, **kwargs: calls.append(method)):
            with self.assertRaises(RuntimeError):
                with api.lock(SHA): raise RuntimeError('registry update failed')
        self.assertEqual(calls, ['POST'])


if __name__ == '__main__': unittest.main()

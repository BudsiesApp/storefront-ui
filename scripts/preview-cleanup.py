#!/usr/bin/env python3
"""Track preview associations and retire eligible releases without touching tags."""
import base64
import hashlib
import json
import re
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

REPOSITORY = 'BudsiesApp/storefront-ui'
LOCK = 'package-preview-cleanup-lock'
REGISTRY = 'preview-cleanup/registry'
TAG = re.compile(r'package-preview-[0-9a-f]{64}\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
RETENTION = timedelta(days=30)


class GitHub:
    def call(self, method, path, data=None, missing=False, binary=False):
        args = ['gh', 'api', '--method', method, path]
        if binary:
            args += ['-H', 'Accept: application/octet-stream']
        if data is not None:
            args += ['--input', '-']
        result = subprocess.run(args, input=None if data is None else json.dumps(data).encode(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            if missing and b'HTTP 404' in result.stderr:
                return None
            raise RuntimeError(result.stderr.decode(errors='replace'))
        return result.stdout if binary else json.loads(result.stdout or b'null')

    def path(self, suffix): return f'repos/{REPOSITORY}' + ('/' + suffix if suffix else '')
    def repository(self): return self.call('GET', self.path(''))
    def ref(self, tag): return self.call('GET', self.path('git/ref/tags/' + tag), missing=True)
    def release(self, tag): return self.call('GET', self.path('releases/tags/' + tag), missing=True)
    def branch(self, branch):
        return self.call('GET', self.path('git/ref/heads/' + quote(branch, safe='/')), missing=True) is not None
    def protected(self, branch):
        info = self.call('GET', self.path('branches/' + quote(branch, safe='')), missing=True)
        if info is None or type(info.get('protected')) is not bool:
            raise ValueError('branch protection could not be verified: ' + branch)
        return info['protected']
    def delete_release(self, release_id): self.call('DELETE', self.path(f'releases/{release_id}'))
    def asset(self, asset_id): return self.call('GET', self.path(f'releases/assets/{asset_id}'), binary=True)

    @contextmanager
    def lock(self, commit):
        # GitHub creates a ref atomically. Never break a stale lock automatically.
        self.call('POST', self.path('git/refs'), {'ref': 'refs/tags/' + LOCK, 'sha': commit})
        try:
            yield
        except BaseException:
            # A partial publish or registry write must not permit cleanup to race ahead.
            raise
        else:
            self.call('DELETE', self.path('git/refs/tags/' + LOCK))

    def read_registry(self):
        ref = self.call('GET', self.path('git/ref/heads/' + REGISTRY), missing=True)
        if ref is None:
            return {'version': 1, 'repository': REPOSITORY, 'previews': {}}, None
        commit = ref['object']['sha']
        tree = self.call('GET', self.path('git/commits/' + commit))['tree']['sha']
        entries = self.call('GET', self.path('git/trees/' + tree))['tree']
        blobs = [x for x in entries if x['path'] == 'registry.json' and x['type'] == 'blob']
        if len(blobs) != 1:
            raise ValueError('invalid preview registry tree')
        blob = self.call('GET', self.path('git/blobs/' + blobs[0]['sha']))
        registry = json.loads(base64.b64decode(blob['content']))
        validate_registry(registry)
        return registry, commit

    def write_registry(self, registry, parent, anchor):
        validate_registry(registry)
        text = json.dumps(registry, sort_keys=True, indent=2) + '\n'
        base = self.call('GET', self.path('git/commits/' + (parent or anchor)))['tree']['sha']
        tree = self.call('POST', self.path('git/trees'), {'base_tree': base, 'tree': [
            {'path': 'registry.json', 'mode': '100644', 'type': 'blob', 'content': text}]})['sha']
        commit = self.call('POST', self.path('git/commits'), {'message': 'Update preview cleanup registry',
                           'tree': tree, 'parents': [parent or anchor]})['sha']
        if parent is None:
            self.call('POST', self.path('git/refs'), {'ref': 'refs/heads/' + REGISTRY, 'sha': commit})
        else:
            # A fast-forward update also rejects an unexpected concurrent writer.
            self.call('PATCH', self.path('git/refs/heads/' + REGISTRY), {'sha': commit, 'force': False})
        return commit


def validate_registry(registry):
    if (not isinstance(registry, dict) or registry.get('version') != 1 or
            registry.get('repository') != REPOSITORY or not isinstance(registry.get('previews'), dict)):
        raise ValueError('invalid preview cleanup registry')
    for tag, record in registry['previews'].items():
        if (not TAG.fullmatch(tag) or not isinstance(record, dict) or type(record.get('release_id')) is not int or
                type(record.get('pinned')) is not bool or not isinstance(record.get('branches'), dict) or
                not SHA.fullmatch(record.get('packaging', ''))):
            raise ValueError('invalid preview cleanup record')
        for branch, deleted in record['branches'].items():
            if not isinstance(branch, str) or not branch or branch.startswith('-'):
                raise ValueError('invalid tracked branch')
            subprocess.run(['git', 'check-ref-format', 'refs/heads/' + branch], check=True, stdout=subprocess.DEVNULL)
            if deleted is not None:
                parsed = datetime.fromisoformat(deleted)
                if parsed.tzinfo is None:
                    raise ValueError('branch deletion timestamp must have a timezone')


def eligible_branch(branch, default_branch):
    if branch in {default_branch, 'optimuspro', 'main', 'master', 'develop'}:
        return False
    return bool(re.fullmatch(r'(?:feature|feat)[/-].+|[0-9]+-[a-zA-Z].+', branch))


def associations(refs, defaults, default_branch):
    """Only omitted historical defaults are exempt from explicit SHA pinning."""
    branches, pinned = set(), False
    for ref, omitted in zip(refs, defaults):
        if omitted:
            continue
        if SHA.fullmatch(ref):
            pinned = True
            continue
        branch = ref.removeprefix('refs/heads/')
        if ref.startswith('refs/') and not ref.startswith('refs/heads/'):
            pinned = True
            continue
        subprocess.run(['git', 'check-ref-format', 'refs/heads/' + branch], check=True, stdout=subprocess.DEVNULL)
        # Main, maintained and release branches are never eligible for cleanup.
        if not eligible_branch(branch, default_branch):
            pinned = True
        else:
            branches.add(branch)
    if not branches:
        pinned = True
    return branches, pinned


def register(registry, tag, release, packaging, branches, pinned, existed):
    """Never adopt an existing release whose association history is unknown."""
    records = registry['previews']
    old = records.get(tag)
    if old is None and existed:
        return False
    if (not TAG.fullmatch(tag) or not release or release.get('draft') is not False or release.get('prerelease') is not True or
            release.get('tag_name') != tag or release.get('name') != tag or type(release.get('id')) is not int):
        raise ValueError('unexpected preview release')
    if old is None:
        records[tag] = {'release_id': release['id'], 'packaging': packaging,
                        'pinned': bool(pinned), 'branches': {name: None for name in sorted(branches)}}
        return True
    if old['packaging'] != packaging:
        raise ValueError('preview packaging identity changed')
    if old['release_id'] != release['id']:
        if existed:
            raise ValueError('preview release identity changed')
        old['release_id'] = release['id']
        old['pinned'] = old['pinned'] or pinned
        old['branches'] = {name: None for name in old['branches'].keys() | branches}
        return True
    before = json.dumps(old, sort_keys=True)
    old['pinned'] = old['pinned'] or pinned
    for branch in branches:
        old['branches'][branch] = None
    return before != json.dumps(old, sort_keys=True)


def valid_release(api, tag, record):
    release = api.release(tag)
    if (not release or release.get('id') != record['release_id'] or release.get('tag_name') != tag or
            release.get('name') != tag or release.get('draft') is not False or release.get('prerelease') is not True):
        return None
    ref = api.ref(tag)
    if not ref or ref['object'].get('type') != 'commit' or ref['object'].get('sha') != record['packaging']:
        return None
    matches = [a for a in release['assets'] if a['name'] == 'release-manifest.json']
    if len(matches) != 1:
        return None
    manifest = json.loads(api.asset(matches[0]['id']))
    identity = manifest.get('previewIdentity')
    canonical = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()
    if (not isinstance(identity, dict) or identity.get('repository') != REPOSITORY or
            identity.get('packagingRevision') != record['packaging'] or manifest.get('releaseTag') != tag or
            manifest.get('packagingRevision') != record['packaging'] or
            'package-preview-' + hashlib.sha256(canonical).hexdigest() != tag):
        return None
    return release


def cleanup(api, registry, now, save, dry_run=False):
    validate_registry(registry)
    repository = api.repository()
    if repository.get('full_name', '').lower() != REPOSITORY.lower():
        raise ValueError('repository could not be verified')
    for tag, record in sorted(registry['previews'].items()):
        if (record['pinned'] or not record['branches'] or
                any(not eligible_branch(branch, repository['default_branch']) for branch in record['branches'])):
            continue
        if not valid_release(api, tag, record):
            continue
        updated = False
        for branch, old in record['branches'].items():
            present = api.branch(branch)
            if present and api.protected(branch):
                record['pinned'] = True
                updated = True
            if present and old is not None:
                record['branches'][branch] = None
                updated = True
            elif not present and old is None:
                record['branches'][branch] = now.isoformat()
                updated = True
        if updated and not dry_run:
            save()
        if record['pinned']:
            continue
        ages = [datetime.fromisoformat(value) if value is not None else None for value in record['branches'].values()]
        if any(value is None or now - value < RETENTION for value in ages):
            continue
        # Check again while the publication lock is held. Direct Git pushes are not locked.
        latest = {branch: api.branch(branch) for branch in record['branches']}
        if any(latest.values()):
            for branch, present in latest.items():
                if present:
                    record['branches'][branch] = None
                    if api.protected(branch):
                        record['pinned'] = True
            if not dry_run:
                save()
            continue
        if not valid_release(api, tag, record):
            continue
        if dry_run:
            print(f'would delete eligible preview {tag}')
        else:
            api.delete_release(record['release_id'])
            print(f'deleted eligible preview {tag}; tag retained')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    api = GitHub()
    anchor = subprocess.check_output(['git', 'rev-parse', 'HEAD^{commit}'], text=True).strip()
    def run():
        registry, parent = api.read_registry()
        def save():
            nonlocal parent
            parent = api.write_registry(registry, parent, anchor)
        cleanup(api, registry, datetime.now(timezone.utc), save, args.dry_run)
    if args.dry_run:
        run()
    else:
        with api.lock(anchor): run()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Publish an immutable preview of the exact branch-push commit."""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = 'BudsiesApp/storefront-ui'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_push(env, default_branch, cleaner):
    ref, sha = env.get('GITHUB_REF', ''), env.get('GITHUB_SHA', '')
    if env.get('GITHUB_EVENT_NAME') != 'push' or not ref.startswith('refs/heads/'):
        raise ValueError('preview publication requires a branch push')
    branch = ref.removeprefix('refs/heads/')
    subprocess.run(['git', 'check-ref-format', ref], check=True, stdout=subprocess.DEVNULL)
    if not cleaner.eligible_branch(branch, default_branch):
        raise ValueError('maintained or internal branch is excluded')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('GITHUB_SHA must be a full commit SHA')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD^{commit}'], cwd=ROOT, text=True).strip()
    if head != sha:
        raise ValueError('checkout does not match triggering commit')
    return branch, sha


def main():
    cleaner = load('preview-cleanup')
    tracking = cleaner.GitHub()
    repository = tracking.repository()
    if repository.get('full_name', '').lower() != REPOSITORY.lower():
        raise ValueError('repository could not be verified')
    branch, sha = selected_push(os.environ, repository['default_branch'], cleaner)
    tag = f'{branch}_{sha[:7]}'
    identity = {'formatVersion': 1, 'repository': REPOSITORY, 'packagingRevision': sha,
                'branch': branch, 'sources': {'shared': sha, 'vue': sha},
                'toolchain': {'python': sys.version.split()[0], 'zlib': zlib.ZLIB_RUNTIME_VERSION}}
    with tracking.lock(sha):
        pinned = tracking.protection_if_present(branch) is not False
        registry, parent = tracking.read_registry()
        existed = tracking.release(tag) is not None
        unknown_tag = not existed and tag not in registry['previews'] and tracking.ref(tag) is not None
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            load('package-release').prepare(path, tag, {'sharedRevision': sha, 'vueRevision': sha}, identity)
            publisher = load('publish-release')
            publisher.publish(publisher.GitHub(), tag, path, preview=True)
            manifest = json.loads((path / 'release-manifest.json').read_text())
        release = tracking.release(tag)
        if cleaner.register(registry, tag, release, sha, {branch}, pinned, existed or unknown_tag):
            tracking.write_registry(registry, parent, sha)
    base = f'https://github.com/{REPOSITORY}/releases/download/{quote(tag, safe="")}/'
    print(json.dumps({'releaseTag': tag, 'identity': identity, 'cleanupTracked': tag in registry['previews'],
                      'packages': [{**package, 'url': base + package['asset']} for package in manifest['packages']],
                      'manifestUrl': base + 'release-manifest.json', 'checksumsUrl': base + 'SHA256SUMS'}))


if __name__ == '__main__':
    main()

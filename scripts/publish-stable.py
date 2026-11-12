#!/usr/bin/env python3
"""Publish the exact stable-branch push commit as a stable package release."""
import importlib.util
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_commit(env):
    sha = env.get('GITHUB_SHA', '')
    if env.get('GITHUB_EVENT_NAME') != 'push' or env.get('GITHUB_REF') != 'refs/heads/optimuspro':
        raise ValueError('stable publication requires a push to optimuspro')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('GITHUB_SHA must be a full commit SHA')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD^{commit}'], cwd=ROOT, text=True).strip()
    if head != sha:
        raise ValueError('checkout does not match triggering commit')
    return sha


def main():
    sha = selected_commit(os.environ)
    tag = 'stable-packages-' + sha
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        load('package-release').prepare(path, tag, {'sharedRevision': sha, 'vueRevision': sha})
        publisher = load('publish-release')
        publisher.publish(publisher.GitHub(), tag, path, stable=True)
    print(f'https://github.com/BudsiesApp/storefront-ui/releases/tag/{tag}')


if __name__ == '__main__':
    main()

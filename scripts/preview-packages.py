#!/usr/bin/env python3
"""Publish a source-selected immutable Storefront UI preview."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = "BudsiesApp/storefront-ui"


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE).decode().strip()


def resolve(ref):
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        if ref.startswith('-') or not re.fullmatch(r"[A-Za-z0-9_./-]+", ref):
            raise ValueError("invalid source ref")
        check = ref if ref.startswith('refs/') else 'refs/heads/' + ref
        git("check-ref-format", check)
        ref = check
    git("fetch", "--no-tags", "origin", ref)
    return git("rev-parse", "--verify", "FETCH_HEAD^{commit}")


def identity(packaging, sources, toolchain):
    return {"formatVersion": 1, "repository": REPOSITORY, "packagingRevision": packaging,
            "sources": sources, "toolchain": toolchain}


def tag_for(value):
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return 'package-preview-' + hashlib.sha256(canonical).hexdigest()


def resolve_sources(shared_ref, vue_ref):
    resolved = {}
    for ref in (shared_ref, vue_ref):
        if ref not in resolved:
            resolved[ref] = resolve(ref)
    return {'shared': resolved[shared_ref], 'vue': resolved[vue_ref]}


def main():
    defaults = json.loads((ROOT / 'scripts/package-release.json').read_text())
    parser = argparse.ArgumentParser(description='Publish an immutable paired package preview')
    parser.add_argument('--shared-ref', default=defaults['sharedRevision'], help='shared source ref (default: %(default)s)')
    parser.add_argument('--vue-ref', default=defaults['vueRevision'], help='Vue source ref (default: %(default)s)')
    args = parser.parse_args()
    if git('status', '--porcelain', '--', 'scripts/package-release.py', 'scripts/package-release.json',
           'scripts/publish-release.py', 'scripts/preview-packages.py'):
        raise ValueError('publishing inputs must be committed')
    packaging = git('rev-parse', 'HEAD^{commit}')
    sources = resolve_sources(args.shared_ref, args.vue_ref)
    value = identity(packaging, sources, {'python': sys.version.split()[0], 'zlib': zlib.ZLIB_RUNTIME_VERSION})
    tag = tag_for(value)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        load('package-release').prepare(path, tag, {'sharedRevision': sources['shared'], 'vueRevision': sources['vue']}, value)
        publisher = load('publish-release')
        publisher.publish(publisher.GitHub(), tag, path, preview=True)
        manifest = json.loads((path / 'release-manifest.json').read_text())
    base = f'https://github.com/{REPOSITORY}/releases/download/{tag}/'
    print(json.dumps({'releaseTag': tag, 'identity': value,
                      'packages': [{**package, 'url': base + package['asset']} for package in manifest['packages']],
                      'manifestUrl': base + 'release-manifest.json', 'checksumsUrl': base + 'SHA256SUMS'}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Publish missing release assets only after checking all existing assets."""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "BudsiesApp/storefront-ui"
ASSETS = ("storefront-ui-shared.tgz", "storefront-ui-vue.tgz", "release-manifest.json", "SHA256SUMS")


def run(*args, check=True):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


class GitHub:
    def commit(self, tag):
        return json.loads(run("gh", "api", f"repos/{REPO}/commits/{tag}").stdout)["sha"]

    def existing_commit(self, tag):
        result = run("gh", "api", f"repos/{REPO}/git/ref/tags/{tag}", check=False)
        if result.returncode:
            if b"HTTP 404" in result.stderr:
                return None
            raise RuntimeError(result.stderr.decode())
        return self.commit(tag)

    def release(self, tag):
        result = run("gh", "api", f"repos/{REPO}/releases/tags/{tag}", check=False)
        if result.returncode:
            if b"HTTP 404" in result.stderr:
                return None
            raise RuntimeError(result.stderr.decode())
        return json.loads(result.stdout)

    def download(self, asset):
        return run("gh", "api", "-H", "Accept: application/octet-stream",
                   f"repos/{REPO}/releases/assets/{asset['id']}").stdout

    def create(self, tag, target=None):
        mode = ["--verify-tag"] if target is None else ["--target", target, "--prerelease", "--latest=false"]
        run("gh", "release", "create", tag, "--repo", REPO, *mode,
            "--title", tag, "--notes", "Package sources and packaging revision are recorded in release-manifest.json; archive checksums are in SHA256SUMS.")

    def create_stable(self, tag, target):
        run("gh", "release", "create", tag, "--repo", REPO, "--target", target,
            "--title", tag, "--notes", "Package sources and packaging revision are recorded in release-manifest.json; archive checksums are in SHA256SUMS.")

    def upload(self, tag, path):
        run("gh", "release", "upload", tag, str(path), "--repo", REPO)


def publish(api, tag, directory, preview=False, stable=False):
    directory = Path(directory)
    metadata = json.loads((directory / "release-manifest.json").read_text())
    if metadata["releaseTag"] != tag:
        raise ValueError("tag and packaging provenance do not match")
    candidates = {name: (directory / name).read_bytes() for name in ASSETS}
    release = api.release(tag)
    if preview and stable:
        raise ValueError("preview and stable modes are mutually exclusive")
    if stable and (not tag.startswith("stable-packages-") or tag != "stable-packages-" + metadata["packagingRevision"] or
                   any(package["sourceRevision"] != metadata["packagingRevision"] for package in metadata["packages"])):
        raise ValueError("stable tag and sources must identify the packaging commit")
    if release is not None and stable and (release.get("draft") or release.get("prerelease")):
        raise ValueError("existing stable release is a draft or prerelease")
    if preview or stable:
        if api.commit(metadata["packagingRevision"]) != metadata["packagingRevision"]:
            raise ValueError("packaging commit is not available on GitHub")
        tag_commit = api.existing_commit(tag)
        if tag_commit is not None and tag_commit != metadata["packagingRevision"]:
            raise ValueError("existing tag points to a different commit")
    if release is not None or not (preview or stable):
        if api.commit(tag) != metadata["packagingRevision"]:
            raise ValueError("tag and packaging provenance do not match")
    existing = {} if release is None else {asset["name"]: asset for asset in release["assets"]}
    for name in ASSETS:
        if name in existing and api.download(existing[name]) != candidates[name]:
            raise ValueError(f"existing asset conflicts: {name}")
    if release is None:
        if preview or stable:
            if stable:
                api.create_stable(tag, metadata["packagingRevision"])
            else:
                api.create(tag, metadata["packagingRevision"])
            if api.commit(tag) != metadata["packagingRevision"]:
                raise ValueError("created tag and packaging provenance do not match")
        else:
            api.create(tag)
    for name in ASSETS:
        if name not in existing:
            api.upload(tag, directory / name)
    final = api.release(tag)
    if stable and (final.get("draft") or final.get("prerelease")):
        raise ValueError("published stable release is a draft or prerelease")
    assets = {asset["name"]: asset for asset in final["assets"]}
    for name in ASSETS:
        if name not in assets or api.download(assets[name]) != candidates[name]:
            raise ValueError(f"missing or mismatched published asset: {name}")


if __name__ == "__main__":
    publish(GitHub(), os.environ["GITHUB_REF_NAME"], sys.argv[1])

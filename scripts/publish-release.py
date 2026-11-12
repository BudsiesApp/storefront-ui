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

    def create(self, tag):
        run("gh", "release", "create", tag, "--repo", REPO, "--verify-tag",
            "--title", tag, "--notes", "Package sources and packaging revision are recorded in release-manifest.json; archive checksums are in SHA256SUMS.")

    def upload(self, tag, path):
        run("gh", "release", "upload", tag, str(path), "--repo", REPO)


def publish(api, tag, directory):
    directory = Path(directory)
    metadata = json.loads((directory / "release-manifest.json").read_text())
    if metadata["releaseTag"] != tag or api.commit(tag) != metadata["packagingRevision"]:
        raise ValueError("tag and packaging provenance do not match")
    candidates = {name: (directory / name).read_bytes() for name in ASSETS}
    release = api.release(tag)
    existing = {} if release is None else {asset["name"]: asset for asset in release["assets"]}
    for name in ASSETS:
        if name in existing and api.download(existing[name]) != candidates[name]:
            raise ValueError(f"existing asset conflicts: {name}")
    if release is None:
        api.create(tag)
    for name in ASSETS:
        if name not in existing:
            api.upload(tag, directory / name)
    final = api.release(tag)
    assets = {asset["name"]: asset for asset in final["assets"]}
    for name in ASSETS:
        if name not in assets or api.download(assets[name]) != candidates[name]:
            raise ValueError(f"missing or mismatched published asset: {name}")


if __name__ == "__main__":
    publish(GitHub(), os.environ["GITHUB_REF_NAME"], sys.argv[1])

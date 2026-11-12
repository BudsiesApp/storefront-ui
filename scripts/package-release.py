#!/usr/bin/env python3
"""Prepare pinned Storefront UI package sources without installing the monorepo."""
import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = "BudsiesApp/storefront-ui"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def sources(revision, path):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source revision must be a full commit SHA")
    if git("rev-parse", "--verify", revision + "^{commit}").decode().strip() != revision:
        raise ValueError("source revision is not the selected commit")
    with tarfile.open(fileobj=io.BytesIO(git("archive", revision, path))) as archive:
        entries = [m for m in archive if m.isfile() and m.name.startswith(path + "/")]
        return {m.name[len(path) + 1:]: (archive.extractfile(m).read(), m.mode) for m in entries}


def generate(files):
    pattern = re.compile(r"src/components/[^/]+/[^/]+/(Sf[^/]+)\.vue$")
    components = [(name.removeprefix("src/components/"), pattern.fullmatch(name).group(1))
                  for name in sorted(files) if pattern.fullmatch(name)]
    imports = [f'import {name} from "./src/components/{path}";' for path, name in components]
    exports = ["  " + name for _, name in components]
    index = ("// Auto-generated file by create-index-files.js. Do not edit manually\n" +
             "\n".join(imports) + "\n\nexport {\n" + ",\n".join(exports) + "\n};\n")
    stories = index.replace("import", "const").replace(" from ", " = require(").replace(
        '.vue";', '.stories.js");').replace("export", "module.exports =")
    files["index.js"] = (index.encode(), 0o644)
    files["storiesOf.js"] = (stories.encode(), 0o644)


def prepare(output, tag):
    config = json.loads((ROOT / "scripts/package-release.json").read_text())
    packaging = git("rev-parse", "HEAD^{commit}").decode().strip()
    output.mkdir(parents=True, exist_ok=True)
    packages = []
    for key, path, asset in (("sharedRevision", "packages/shared", "storefront-ui-shared.tgz"),
                             ("vueRevision", "packages/vue", "storefront-ui-vue.tgz")):
        revision = config[key]
        files = sources(revision, path)
        manifest = json.loads(files["package.json"][0])
        if key == "vueRevision":
            generate(files)
            manifest["scripts"].pop("postinstall", None)
            manifest["scripts"].pop("prepublish", None)
            manifest["dependencies"]["@storefront-ui/shared"] = (
                f"https://github.com/{REPOSITORY}/releases/download/{tag}/storefront-ui-shared.tgz")
            files["package.json"] = ((json.dumps(manifest, indent=2) + "\n").encode(), files["package.json"][1])
        target = output / asset
        with target.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for name, (data, mode) in sorted(files.items()):
                    info = tarfile.TarInfo("package/" + name)
                    info.size, info.mode, info.mtime = len(data), mode, 0
                    archive.addfile(info, io.BytesIO(data))
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        packages.append({"name": manifest["name"], "version": manifest["version"],
                         "sourceRevision": revision, "sourcePath": path, "asset": asset, "sha256": digest})
    metadata = {"repository": REPOSITORY, "releaseTag": tag, "packagingRevision": packaging, "packages": packages}
    (output / "release-manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "SHA256SUMS").write_text("".join(f"{p['sha256']}  {p['asset']}\n" for p in packages))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    prepare(args.output, args.tag)

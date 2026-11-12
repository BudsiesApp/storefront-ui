#!/usr/bin/env python3
import hashlib
import importlib.util
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish-release.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PackageReleaseTest(unittest.TestCase):
    def test_archive_contents_and_provenance(self):
        tag = "packages-37220-v1"
        revisions = {"packages/shared": "3ff374628936ba579a9bbb2a634c6c3ce9db6ac5",
                     "packages/vue": "b345b9cb261dabf1c105f4e6007fe7332ec8b6a4"}
        with tempfile.TemporaryDirectory() as tmp:
            outputs = [Path(tmp) / "first", Path(tmp) / "second"]
            for output in outputs:
                subprocess.run(["python3", str(ROOT / "scripts/package-release.py"),
                                "--output", str(output), "--tag", tag], check=True)
            for name in publisher.ASSETS:
                self.assertEqual((outputs[0] / name).read_bytes(), (outputs[1] / name).read_bytes())
            metadata = json.loads((outputs[0] / "release-manifest.json").read_text())
            self.assertEqual(metadata["releaseTag"], tag)
            self.assertEqual(metadata["packagingRevision"], subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
            for package in metadata["packages"]:
                path, revision, asset = package["sourcePath"], package["sourceRevision"], package["asset"]
                self.assertEqual(revision, revisions[path])
                archive_file = outputs[0] / asset
                digest = hashlib.sha256(archive_file.read_bytes()).hexdigest()
                self.assertEqual(package["sha256"], digest)
                self.assertIn(f"{digest}  {asset}\n", (outputs[0] / "SHA256SUMS").read_text())
                source = subprocess.check_output(["git", "archive", revision, path], cwd=ROOT)
                with tarfile.open(fileobj=io.BytesIO(source)) as original, tarfile.open(archive_file) as archive:
                    expected = {m.name[len(path) + 1:]: original.extractfile(m).read()
                                for m in original if m.isfile() and m.name.startswith(path + "/")}
                    actual = {m.name.removeprefix("package/"): archive.extractfile(m).read()
                              for m in archive if m.isfile()}
                old_manifest, manifest = json.loads(expected.pop("package.json")), json.loads(actual.pop("package.json"))
                self.assertEqual((manifest["name"], manifest["version"]), (package["name"], package["version"]))
                if path.endswith("vue"):
                    old_manifest["scripts"].pop("postinstall")
                    old_manifest["scripts"].pop("prepublish")
                    old_manifest["dependencies"]["@storefront-ui/shared"] = (
                        f"https://github.com/BudsiesApp/storefront-ui/releases/download/{tag}/storefront-ui-shared.tgz")
                    index, stories = actual.pop("index.js").decode(), actual.pop("storiesOf.js").decode()
                    components = [p for p in expected if __import__("re").fullmatch(
                        r"src/components/[^/]+/[^/]+/Sf[^/]+\.vue", p)]
                    self.assertTrue(components)
                    for component in components:
                        self.assertIn('"./' + component + '"', index)
                        self.assertIn('"./' + component.removesuffix('.vue') + '.stories.js"', stories)
                        self.assertIn(component.removesuffix('.vue') + '.stories.js', expected)
                self.assertEqual(manifest, old_manifest)
                self.assertEqual(actual, expected)

    def test_publisher_conflicts_and_partial_recovery(self):
        class FakeGitHub:
            def __init__(self, assets, exists=True, sha="a" * 40):
                self.assets, self.exists, self.sha, self.writes = dict(assets), exists, sha, []
            def commit(self, tag): return self.sha
            def release(self, tag):
                return {"assets": [{"name": k, "id": k} for k in self.assets]} if self.exists else None
            def download(self, asset): return self.assets[asset["id"]]
            def create(self, tag): self.writes.append("create"); self.exists = True
            def upload(self, tag, path): self.writes.append(path.name); self.assets[path.name] = path.read_bytes()

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in publisher.ASSETS:
                (directory / name).write_bytes(name.encode())
            (directory / "release-manifest.json").write_text(json.dumps(
                {"releaseTag": "packages-test", "packagingRevision": "a" * 40}))
            expected = {name: (directory / name).read_bytes() for name in publisher.ASSETS}
            for initial, exists, count in (({}, False, 5), (expected, True, 0),
                                           ({"storefront-ui-vue.tgz": expected["storefront-ui-vue.tgz"]}, True, 3)):
                fake = FakeGitHub(initial, exists)
                publisher.publish(fake, "packages-test", directory)
                self.assertEqual(fake.assets, expected)
                self.assertEqual(len(fake.writes), count)
            for initial, sha in (({"SHA256SUMS": b"conflict"}, "a" * 40), ({}, "b" * 40)):
                fake = FakeGitHub(initial, sha=sha)
                with self.assertRaises(ValueError): publisher.publish(fake, "packages-test", directory)
                self.assertEqual(fake.assets, initial)
                self.assertEqual(fake.writes, [])


if __name__ == "__main__": unittest.main()

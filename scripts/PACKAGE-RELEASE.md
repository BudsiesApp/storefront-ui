# Storefront UI package releases

The full Git commits in `package-release.json` select shared and Vue sources
independently. The release tag points to the separate packaging commit. The
initial commits are `3ff374628936ba579a9bbb2a634c6c3ce9db6ac5` for shared and
`b345b9cb261dabf1c105f4e6007fe7332ec8b6a4` for Vue.

With Python 3.11.11 and Git, run:

```sh
python scripts/test-package-release.py
python scripts/package-release.py --output /tmp/storefront-ui-packages --tag packages-37220-v1
(cd /tmp/storefront-ui-packages && sha256sum -c SHA256SUMS)
```

The output contains `storefront-ui-shared.tgz`, `storefront-ui-vue.tgz`,
`release-manifest.json` and `SHA256SUMS`. Packaging runs no dependency install
or standalone library build. It generates Vue's entry files, removes its two
generation hooks, and changes its shared dependency to this release's shared
asset; no source checkout is modified. Shared retains its existing deep-import
tree and its unused, absent root main file.

For feature testing, first check out and push the committed publishing tools,
and push the source branch or commit to this repository's `origin`.
Run `python3 scripts/preview-packages.py --vue-ref <feature-branch>` or use
`--shared-ref <feature-branch>` independently. Omitted refs default to the
corresponding full source pins in `package-release.json`; `--help` displays
them. Python 3.11+, Git, authenticated `gh` and repository write access are
required. The JSON contains both package URLs, source and packaging SHAs,
Python/zlib versions, and manifest/checksum URLs. Verify those before updating
both UI URLs and the lock. For another commit, rerun against the advanced
branch; after merge, pass the actual merged SHA. No publishing configuration
edits or manual tag are needed. Previews are public and immutable.

For the separate explicit-release workflow, update the source SHA(s) and
baseline test assertions, commit, and run the tests. Once authorized, push a new unused
`packages-*` tag pointing to the packaging commit. The workflow publishes all
four assets. A rerun reuses identical assets and fills missing ones; a conflict
fails without replacement. Investigate conflicts and use a new tag rather than
moving tags or clobbering assets. Retain old releases and GitPkg URLs for
historical consumers.

Download the assets anonymously from
`https://github.com/BudsiesApp/storefront-ui/releases/download/<tag>/`, verify
`sha256sum -c SHA256SUMS`, and inspect the source and packaging revisions in
the manifest. Update both direct shared and Vue URLs in each UI app line to
the matching assets, regenerate each Yarn 4 lock in the UI container, and
verify the packaged Vue manifest uses that same shared URL. Run immutable
installs and the maintained brand checks before changing consumers.

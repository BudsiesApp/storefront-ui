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

Every push to the maintained `optimuspro` branch automatically publishes a
non-prerelease release with tag and title `optimuspro_<first-seven-push-SHA>`.
Both shared and Vue are taken from that exact triggering commit, independently
of the historical pins in `package-release.json`. The checkout, packaging revision and release
tag must agree with that commit. The Vue manifest points to the matching
shared asset in the same release. Check the Actions run, manifest and
`SHA256SUMS` before selecting these URLs in a consumer. An identical rerun
reuses assets; conflicting assets or a tag at a different commit fail without
replacement, including when different commits share the same seven-character
prefix. The manifest records the full source and packaging SHA. Older stable,
explicit-tag and preview releases retain their existing names and assets.
Publication does not update consumers or deploy applications.

For feature testing, pushes to non-maintained branches containing the branch
preview workflow publish a public prerelease named `<branch>_<first-seven-SHA>`.
Both packages use the exact pushed commit. Find the URLs and checksums in the
workflow summary; URL-encode `/` in branch names when constructing asset URLs.
The default, maintained and `preview-cleanup/` branches are excluded. Existing
branches must first include the workflow, for example by merging `optimuspro`.
Publication does not change consumers or deploy applications.
Pushes made with a workflow's `GITHUB_TOKEN` do not trigger push workflows.

For an on-demand preview, first check out and push the committed publishing tools,
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

New branch previews are tracked outside their immutable assets. A
scheduled workflow checks every recorded branch; only after all are observed
deleted for 30 days may it delete the prerelease and its assets. The Git tag
is retained, but the preview download URLs stop working. Reusing a preview
adds each selected feature branch to its associations. An explicitly selected
commit, tag, maintained branch, or protected branch permanently pins
the preview; the omitted historical companion does not. Older previews whose
association history is unknown are never adopted or deleted. The registry is
stored on the `preview-cleanup/registry` branch, with no changes to release
assets. The scheduler lives on the repository default branch and checks out
`optimuspro`; manual workflow dispatch runs a read-only dry run.
Any non-maintained, non-internal branch qualifies; protected branches remain
pinned. A branch already absent at publication is pinned because its protection
cannot be checked. Existing pinned previews remain pinned when these rules change.

The 30-day clock starts when deletion is detected, not when a preview is made.
An observed reappearance resets that branch's clock. The final branch check is
immediately before deletion, but a brief reappearance between checks or a
branch created after the final check may be missed. GitHub schedules can be
delayed or disabled; they never shorten the retention interval.

Publication and cleanup share a repository-wide Git ref lock. Concurrent work
fails rather than stealing the lock. A failed or interrupted operation leaves
the lock in place: inspect the workflow/publisher and registry, confirm no
operation is active and that any partially published preview is safe, then
resolve the lock with an authorized maintainer. Never automatically clear it.
The branch publication and default-branch scheduler workflows also share an
Actions concurrency group with `queue: max`. Update the scheduler workflow on
the default branch before enabling branch previews, because scheduled workflows
run from that branch. Branch previews are skipped until cleanup support reaches
`optimuspro`; the old cleanup cannot read their registry entries.
GitHub queues at most 100 pending runs in a concurrency group; additional runs
are canceled and must be rerun. The local preview command is outside that queue
and still fails on lock contention rather than taking over an active lock.

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

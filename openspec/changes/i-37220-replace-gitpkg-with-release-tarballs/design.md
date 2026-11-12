# Design

## Context

See `proposal.md` for motivation. The maintained fork branch is `optimuspro`; remote default `develop` does not contain the current Vue pin. The packaging feature starts at `b345b9cb261dabf1c105f4e6007fe7332ec8b6a4`. This repository had no OpenSpec root; a minimal `spec-driven` root was initialized with approval.

`packages/vue/package.json` exposes root `index.js`, source files and `styles.scss`, not standalone build output. Its `postinstall` and `prepublish` generate root `index.js` and `storiesOf.js` with `scripts/create-index-files.js`; the generator uses Node built-ins and root devDependency `glob`. Root/workspace installation would pull the obsolete development stack, including `node-sass`. Shared and Vue are both version `0.7.11`, but their consumer pins differ. Shared has style/icon/variable files and no runtime dependencies; its advertised `index.js` does not exist at the pinned commit, and consumers use deep imports.

## Goals / Non-Goals

**Goals:** Separate source selection, package preparation and authenticated publication; generate install-ready source archives while preserving each package's actual baseline; provide the UI a stable transport contract.

**Non-Goals:** Repairing shared's unused main entry, introducing a binary library, installing the legacy monorepo, publishing to npm, adding signing/cleanup infrastructure, or altering source component behavior.

## Decisions

### Release-tag interface and independent revision inputs

Add `.github/workflows/publish-packages.yml` for pushes of `packages-*` tags. A tracked release configuration, `scripts/package-release.json`, explicitly selects full `sharedRevision` and `vueRevision` commits; the initial values are the two pins in the spec. The tag points to the packaging commit, whose full SHA is recorded separately. Future releases update the configuration and use a new tag; a rerun uses the same tagged packaging revision. No required manual-dispatch interface is added.

This paragraph describes the retained explicit-release interface, not a prerequisite for on-demand previews. The preview command below supplies resolved revisions directly without modifying this configuration or its initial-pin regression assertions.

This meets the ticket's tag-trigger alternative without requiring the workflow to be installed on stale `develop` before it can run. It is preferable here to `workflow_dispatch`, which needs default-branch workflow availability. Source ref selection is data, not shell code: pass arguments/environment safely and resolve package trees via Git, not shell interpolation. Keep workflow/script execution from the packaging checkout; do not execute arbitrary lifecycle scripts from selected source commits.

### Isolated source preparation

Use `git archive` of each selected commit/subdirectory into separate temporary staging directories. Never copy the working tree or extract both packages from one commit. Keep the original monorepo manifests and source files unchanged. Packaging modifications happen only in staging:

1. Generate Vue's root entry files with the same component-discovery/export semantics as the pinned generator (`src/components/*/*/Sf*.vue`). The implemented Python standard-library generator avoids installing `glob` and the root workspace; sort discovery for stable output and test output/export equivalence against the baseline semantics.
2. Remove the staged Vue `postinstall` and `prepublish` generation hooks. Do not use a consumer-wide ignore-scripts switch, because unrelated application dependencies retain their lifecycle requirements.
3. Replace only staged Vue's `@storefront-ui/shared` URL with the shared asset for this release. Preserve other runtime dependencies, peer dependencies, package names/versions, entry fields and side-effect declarations.
4. Pack staged directories with lifecycle execution disabled, preserving npm-compatible `package/` archive layout. Keep the explicit workflow's pinned runtime; the preview path below records its exact runtime in its identity. Normalize ordering/archive metadata as needed for repeatable bytes. No root/workspace dependency installation or standalone `build` command occurs.

Respect the Vue files contract, including generated entries, component/story sources, utilities, `src/css`, `styles.scss` and `config/storybook/decorators.js`; shared needs its style/icon/variable tree. Focused archive checks compare extracted files against their respective Git trees, allowing only generated entries and the documented manifest edits. Do not invent a shared `index.js` or upgrade its sources to make an unused field look complete.

### Release asset contract

Use release tag `packages-37220-v1` for the proposed first release, unless it is already occupied (choose a new unused `packages-*` tag; never repurpose it). Publish `storefront-ui-shared.tgz`, `storefront-ui-vue.tgz`, `release-manifest.json` and `SHA256SUMS` under that tag. URLs have the form:

`https://github.com/BudsiesApp/storefront-ui/releases/download/<release-tag>/storefront-ui-shared.tgz`

The Vue URL changes only the asset basename. Its packaged shared dependency must equal that shared URL exactly. Metadata records repository, release tag, full packaging commit and an entry per package with name, version, source commit, source subdirectory, asset name and SHA-256. `SHA256SUMS` covers the archive assets; keep metadata deterministic, without timestamps/run IDs that change on rerun. Release notes explain source versus packaging revision and link these metadata assets.

### Non-overwriting publication

For the explicit tag workflow, authenticate writes with the repository token and `contents: write`; package downloads stay anonymous. Serialize that workflow's publications by repository/tag with cancellation disabled. Before uploads, compare every existing corresponding archive/metadata asset against the candidate bytes and confirm the tag/provenance identifies the same packaging revision. Reuse exact matches. Reject conflicts before altering any existing asset. Upload only missing assets without a clobber/delete path; an upload race/error must fail or verify identical existing bytes, never replace them. Rerun an interrupted upload to add only missing matching assets. Mark success only after the full required set exists and agrees with its metadata.

GitHub-provided repository source archives and Actions run artifacts are not consumer dependencies. No automatic release deletion or tag movement is introduced.

### Local checks versus acceptance

The implementer adds focused packaging/contract tests and a no-network publication test double for absent/identical/conflicting/partial existing asset sets. Existing-asset conflict handling is required by the ticket and protects real external release I/O; no speculative retry/fallback policy is added. The tester separately proves actual workflow publication, anonymous download/checksum agreement, cache-empty UI installs with GitPkg unavailable, maintained brand builds/tests and rendering. Local archives alone do not satisfy publication acceptance.

## Risks / Trade-offs

- Historical source contents are intentionally retained, including the unused shared main field and legacy library limitations → acceptance covers existing consumer imports; do not repair or upgrade unrelated library behavior.
- GitHub release assets remain mutable by repository administrators → this publication path never overwrites/deletes; maintainers must retain consumed tags/assets. No signing or external retention service is added.
- Packaging tool drift can change archive bytes → pin packaging tools and make output repeatable; reject a conflict and publish a new tag rather than replace a consumed asset.
- Publication is external work outside this role → lead obtains authorization/access before pushing a release tag; absent approval remains an open acceptance check, not permission to fake a successful release.

## Migration Plan

Implement and review the packaging workflow, scripts and tests on `37220-replace-gitpkg-with-release-tarballs`, based on `optimuspro`. With separately authorized publication, tag the approved packaging revision and publish both source pins. Verify anonymous URLs and checksums before the companion UI commits lock the real URLs. UI changes cover both `petsies-theme` and `bulkorders-theme`; the API/Amazon Pay pair can proceed independently. Never delete the old GitPkg service or historical release assets. A later authorized consumer rollback can use its previous dependency commit without altering any artifact; this design itself authorizes no rollout or rollback.

## Approved on-demand preview extension

### Current baseline and runnable mechanism

The original migration is implemented, published as `packages-37220-v1` and accepted within its scope (D18–D21). Current PR #24 head is `9bec5d80b`; packaging and upload are Python scripts using Git and `gh`, and the workflow pins Python 3.11.11. Keep that acceptance/provenance and the original tag/assets unchanged. This extension is pending, not another claim that the original migration must be redone.

Add `scripts/preview-packages.py`, invoked from the source-repository checkout containing the committed preview implementation, using existing Python 3.11+, Git and authenticated GitHub CLI. Example: `python3 scripts/preview-packages.py --vue-ref <feature-branch>`; `--shared-ref <branch-or-full-commit>` selects shared independently. An omitted package ref visibly defaults to its existing `package-release.json` full source pin. `--help` and the returned handoff document those defaults; they never come from whichever source branch happens to be checked out.

The packaging revision is the full committed HEAD from which these tools execute. Do not label dirty versioned publishing code as that commit: require committed publishing inputs before publication. A maintainer fetches/checks out the packaging feature branch once and pushes its committed implementation so GitHub can target that SHA; selecting or advancing package feature branches does not require switching this packaging checkout or editing it. No publishing-configuration/test commit is needed per iteration.

This local-command surface deliberately avoids `workflow_dispatch`: source defaults remain stale and manual workflow availability on them is not assumed. `gh release create --help` explicitly supports automatic missing-tag creation at `--target <full-commit>` instead of the default branch. Thus one usable command is technically available before merge, without installing a second interface on default branches. No new account, credential or host installation is part of the change; missing tool access is reported to the lead.

Feasibility check: this environment exposes Python 3.12.3 as `python3`, Git 2.55.0 and GitHub CLI 2.45.0; no `python3.11` executable or managed 3.11.11 interpreter was found. Both current source suites pass using `python3` (two tests each). The preview command therefore uses available supported Python rather than assuming an unavailable host executable. The explicit workflow keeps Python 3.11.11. Include exact Python and zlib runtime versions in the preview key/provenance so different compression runtimes cannot masquerade as one packaging identity.

### Resolve once and prepare selected trees

Fetch each distinct selected ref from `BudsiesApp/storefront-ui` once, resolve the fetched object to a full commit, and cache that mapping for the invocation. Two equal shared/Vue input refs therefore cannot resolve to different moments of one moving branch. Full commit inputs are fetched/verified as needed. Validate selections as branch names, full refs or full commit SHAs, not arbitrary Git options/revision expressions. Use subprocess argument arrays and the existing Git-tree reader; do not check out or execute source scripts. Fail clearly on an unresolvable selection without fallback, and finish resolving/checking both packages before external publication.

Refactor `package-release.py` to accept explicit resolved revision inputs while retaining configuration-backed behavior for the existing release workflow. Reuse its deterministic in-memory archive generator, Vue hook removal, entry generation and paired shared URL rewrite. Generic source/archive tests compare artifacts to the requested source trees and permitted manifest changes; dedicated initial-pin regression tests still assert the original three source baselines across the two publishers. No invocation rewrites those assertions or tracked configuration.

### Identity, automatic tag creation and output

Compute the preview key as SHA-256 of a canonical JSON object with format version `1`, repository, full packaging revision, logical source mapping `{shared: <full SHA>, vue: <full SHA>}` and toolchain mapping `{python: <exact version>, zlib: <runtime version>}`. Canonical serialization uses sorted keys and no insignificant whitespace. Use the entire digest in `package-preview-<digest>`. Do not key on branch spelling, run time, working-tree contents or archive digest (Vue embeds its own release's shared URL, so archive hashing cannot define that URL without a cycle). Persist these identity fields in provenance; input spelling can appear in output, not volatile release metadata that prevents identical reuse.

Prepare/check all candidate assets with that final tag before any public write. For a new identity, use `gh release create` with the exact packaging `--target` SHA and mark the release as prerelease/not latest; this manages its own tag, not a maintainer-prepared tag. The packaging SHA must already be reachable in this repository on GitHub. For an existing tag/release, verify its target and candidate provenance/bytes before writing. The `package-preview-*` namespace does not match the retained workflow's `packages-*` push filter, so it cannot start a competing config-backed publication.

Reuse `publish-release.py` preflight/final verification, with an explicit preview creation mode rather than weakening the explicit workflow's `--verify-tag` contract. Complete identical previews return the same URLs with no asset writes. Missing matching assets can be added on rerun; conflicts fail without overwrite/delete. Concurrent commands rely on no-clobber creation/uploads: an already-exists race can fail clearly and be rerun after inspecting state; no retry loop or claim of partial success is required.

After complete remote verification, print one machine-readable handoff containing release tag, packaging SHA/toolchain, each resolved source SHA/name/version/exact `.tgz` URL, `release-manifest.json` URL and `SHA256SUMS` URL. Human progress goes separately from the successful JSON output. Invalid selections/conflicts/incomplete publication exit nonzero rather than returning a usable-success handoff. Both returned package URLs share this tag, and the archived Vue manifest's shared URL must equal the returned shared URL exactly.

### Iteration, consumer separation and acceptance

The same command selects unmerged commits, later branch heads and a final explicit merged SHA. Any changed source, packaging SHA or recorded toolchain produces a new identity, even for similar file trees; identical resolved identities can reuse a preview through another ref spelling. Keep all earlier release and preview assets. No moving branch alias, automatic PR/push preview, cleanup policy, new hosting or automatic VSF update is added.

Update `scripts/PACKAGE-RELEASE.md` to make this the no-edit feature-testing/post-merge path and remove the instruction that routine new selections require baseline-test edits. Keep configuration-driven explicit releases documented separately. UI documentation/checks in both app lines accept preview tags, but manifests/locks still change explicitly in the intended testing graph, with the shared pair aligned. Do not replace accepted final UI pins with arbitrary preview sources.

Implementation checks cover ref/commit/default selection, one-resolution behavior, arbitrary selected-tree packaging, deterministic identity/reuse, changed source/packaging keys, conflict preservation, partial completion and exact pair handoff. Tester proves actual command publication and anonymous checksum downloads for both publishers, branch advancement without config/test commits or manually prepared tags, explicit-commit selection and targeted VSF consumption. Retain prior five-brand acceptance and rerun only checks affected by the new diff/selected preview; report baseline caveats separately.

Input-4 authorization remains limited to its explicit release-tag/workflow scope. Input-10 now authorizes command-managed `package-preview-*` tags/releases and package/manifest/checksum uploads in both source repositories after source checks pass, preserving existing assets. Execution belongs to implementer/tester, not this spec revision. A missing repository write permission still needs lead assistance; no merge, application deployment, archive or issue transition is authorized.

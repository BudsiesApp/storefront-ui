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

This meets the ticket's tag-trigger alternative without requiring the workflow to be installed on stale `develop` before it can run. It is preferable here to `workflow_dispatch`, which needs default-branch workflow availability. Source ref selection is data, not shell code: pass arguments/environment safely and resolve package trees via Git, not shell interpolation. Keep workflow/script execution from the packaging checkout; do not execute arbitrary lifecycle scripts from selected source commits.

### Isolated source preparation

Use `git archive` of each selected commit/subdirectory into separate temporary staging directories. Never copy the working tree or extract both packages from one commit. Keep the original monorepo manifests and source files unchanged. Packaging modifications happen only in staging:

1. Generate Vue's root entry files with the same component-discovery/export semantics as the pinned generator (`src/components/*/*/Sf*.vue`). A small Node built-in implementation avoids installing `glob` and the root workspace; sort discovery for stable output and test output/export equivalence against the baseline semantics.
2. Remove the staged Vue `postinstall` and `prepublish` generation hooks. Do not use a consumer-wide ignore-scripts switch, because unrelated application dependencies retain their lifecycle requirements.
3. Replace only staged Vue's `@storefront-ui/shared` URL with the shared asset for this release. Preserve other runtime dependencies, peer dependencies, package names/versions, entry fields and side-effect declarations.
4. Pack staged directories with lifecycle execution disabled, preserving npm-compatible `package/` archive layout. Use a pinned packaging runtime/tool version, and normalize ordering/archive metadata as needed for repeatable bytes. No root/workspace dependency installation or standalone `build` command occurs.

Respect the Vue files contract, including generated entries, component/story sources, utilities, `src/css`, `styles.scss` and `config/storybook/decorators.js`; shared needs its style/icon/variable tree. Focused archive checks compare extracted files against their respective Git trees, allowing only generated entries and the documented manifest edits. Do not invent a shared `index.js` or upgrade its sources to make an unused field look complete.

### Release asset contract

Use release tag `packages-37220-v1` for the proposed first release, unless it is already occupied (choose a new unused `packages-*` tag; never repurpose it). Publish `storefront-ui-shared.tgz`, `storefront-ui-vue.tgz`, `release-manifest.json` and `SHA256SUMS` under that tag. URLs have the form:

`https://github.com/BudsiesApp/storefront-ui/releases/download/<release-tag>/storefront-ui-shared.tgz`

The Vue URL changes only the asset basename. Its packaged shared dependency must equal that shared URL exactly. Metadata records repository, release tag, full packaging commit and an entry per package with name, version, source commit, source subdirectory, asset name and SHA-256. `SHA256SUMS` covers the archive assets; keep metadata deterministic, without timestamps/run IDs that change on rerun. Release notes explain source versus packaging revision and link these metadata assets.

### Non-overwriting publication

Authenticate writes with the workflow's repository token and `contents: write`; package downloads stay anonymous. Serialize this workflow's publications by repository/tag with cancellation disabled. Before uploads, compare every existing corresponding archive/metadata asset against the candidate bytes and confirm the tag/provenance identifies the same packaging revision. Reuse exact matches. Reject conflicts before altering any existing asset. Upload only missing assets without a clobber/delete path; an upload race/error must fail or verify identical existing bytes, never replace them. Rerun an interrupted upload to add only missing matching assets. Mark success only after the full required set exists and agrees with its metadata.

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

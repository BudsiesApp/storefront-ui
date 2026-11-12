# Tasks

## 1. Isolated source packaging

- [x] 1.1 Add explicit shared/Vue source configuration and isolated Git-tree staging; verify focused tests extract the two initial commits independently and preserve names, versions and runtime dependencies.
- [x] 1.2 Add lightweight Vue entry generation and staged hook/shared-URL edits; verify focused tests cover the baseline component/export discovery, both generated files, unchanged non-shared runtime dependencies and absence of generation hooks/GitPkg URLs in packaged manifests.
- [x] 1.3 Produce repeatable npm-compatible archives with lifecycle scripts disabled and pinned tooling; verify archive tests cover referenced components/stories, styles, utilities, shared deep-import trees, documented source differences and identical repeated outputs without root/workspace installs or standalone builds.
- [x] 1.4 Document local preparation, source-versus-packaging revisions and allowed staged edits alongside the packaging command; verify every documented input/output matches the script and focused test invocation.

## 2. Traceable non-overwriting publication

- [x] 2.1 Add deterministic release metadata and SHA256SUMS for the two named archives; verify focused tests recompute archive hashes and match source paths/commits, package identities, packaging SHA, release tag and asset filenames.
- [x] 2.2 Add the `packages-*` tag workflow and publication code with tag-scoped serialization, required token permission and no-clobber preflight/upload behavior; verify no-network publication tests cover absent, identical, conflicting and partial existing assets and prove conflicting existing bytes/provenance are never replaced or deleted.
- [x] 2.3 Document authorized tag publication, real anonymous URLs, reruns/conflicts, later-source selection, direct/indirect UI dependency updates and retention; verify the procedure names every required asset and never recommends tag movement, clobber uploads or historical cleanup.

## 3. On-demand previews

- [x] 3.1 Add the local preview command's independent ref/full-commit inputs and visible unchanged-companion defaults; verify focused tests resolve each distinct selected remote ref once, preserve its immutable SHA after branch movement and fail clearly without fallback on unresolvable input.
- [x] 3.2 Refactor preparation to accept resolved preview sources without tracked-config mutation; verify generic archive/source tests exercise arbitrary selected revisions and both package selections independently while dedicated initial-pin regression assertions remain unchanged and the explicit release workflow still passes.
- [x] 3.3 Add canonical source/packaging/toolchain identity, command-managed `package-preview-*` prerelease creation at the exact pushed packaging SHA and non-clobber reuse/completion; verify focused tests cover equal keys via different ref spellings, changed source/packaging/toolchain keys, conflicts, partial publication and create/upload races without overwrite or incomplete-success reporting.
- [x] 3.4 Return a complete exact paired URL/provenance/checksum handoff and document runnable setup, defaults, feature iteration, post-merge selection and approval scope; verify output/CLI tests prove Vue's archived shared URL equals the returned shared URL, no manual tags/config/test edits are needed, and existing `packages-*` workflows cannot be triggered by preview identities.

## Workflow follow-up

- Lead obtains authorization/access before pushing a release tag. Tester proves actual Actions publication, anonymous downloads/checksums, logs excluding legacy preparation, repeat-publication retention, cache-empty UI installation and maintained brand compatibility. These live checks are not implementer task checkboxes.
- Companion UI changes cannot finalize real-asset lockfiles until publication/download evidence is available. Local archives are not completion evidence for public hosting.
- Archive only when the operator chooses it, after review and acceptance; merging and deployment are separate work.
- Preview extension: input-10 authorizes command-managed preview publication after source checks; implementer/tester, not spec writer, execute it. Tester proves actual on-demand publication and anonymous checksum downloads, branch/ref plus full-commit selection, branch advancement without publishing edits/manual tags, retained earlier URLs, same-identity reuse and returned-pair VSF consumption. Live checks are not implementation checkboxes.
- Preserve accepted pinned-migration evidence and all existing tags/assets. Determine preview regressions from the actual implementation diff; do not silently replace final UI pins with preview test sources.

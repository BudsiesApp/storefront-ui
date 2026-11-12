# Tasks

## 1. Isolated source packaging

- [ ] 1.1 Add explicit shared/Vue source configuration and isolated Git-tree staging; verify focused tests extract the two initial commits independently and preserve names, versions and runtime dependencies.
- [ ] 1.2 Add lightweight Vue entry generation and staged hook/shared-URL edits; verify focused tests cover the baseline component/export discovery, both generated files, unchanged non-shared runtime dependencies and absence of generation hooks/GitPkg URLs in packaged manifests.
- [ ] 1.3 Produce repeatable npm-compatible archives with lifecycle scripts disabled and pinned tooling; verify archive tests cover referenced components/stories, styles, utilities, shared deep-import trees, documented source differences and identical repeated outputs without root/workspace installs or standalone builds.
- [ ] 1.4 Document local preparation, source-versus-packaging revisions and allowed staged edits alongside the packaging command; verify every documented input/output matches the script and focused test invocation.

## 2. Traceable non-overwriting publication

- [ ] 2.1 Add deterministic release metadata and SHA256SUMS for the two named archives; verify focused tests recompute archive hashes and match source paths/commits, package identities, packaging SHA, release tag and asset filenames.
- [ ] 2.2 Add the `packages-*` tag workflow and publication code with tag-scoped serialization, required token permission and no-clobber preflight/upload behavior; verify no-network publication tests cover absent, identical, conflicting and partial existing assets and prove conflicting existing bytes/provenance are never replaced or deleted.
- [ ] 2.3 Document authorized tag publication, real anonymous URLs, reruns/conflicts, later-source selection, direct/indirect UI dependency updates and retention; verify the procedure names every required asset and never recommends tag movement, clobber uploads or historical cleanup.

## Workflow follow-up

- Lead obtains authorization/access before pushing a release tag. Tester proves actual Actions publication, anonymous downloads/checksums, logs excluding legacy preparation, repeat-publication retention, cache-empty UI installation and maintained brand compatibility. These live checks are not implementer task checkboxes.
- Companion UI changes cannot finalize real-asset lockfiles until publication/download evidence is available. Local archives are not completion evidence for public hosting.
- Archive only when the operator chooses it, after review and acceptance; merging and deployment are separate work.

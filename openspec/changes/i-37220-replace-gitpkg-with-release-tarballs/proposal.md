# Proposal

## Why

Consumers currently ask GitPkg to extract Storefront UI subdirectories during installation. Redmine [#37220](https://redmine.gorbunov.studio/issues/37220) instead requires prepared public release packages, avoiding both that live service and preparation of the legacy development toolchain.

## What Changes

- Add isolated packaging and a release-tag-triggered GitHub Actions publication workflow for `@storefront-ui/shared` and `@storefront-ui/vue`, with explicit source revisions in the tagged release configuration.
- Select each package's source revision independently; preserve the existing distinct initial pins.
- Generate Vue entry files before packing, include component/style/runtime sources, and replace Vue's indirect shared GitPkg URL in its packaged manifest.
- Publish release-specific anonymous-download assets with source/packaging provenance and SHA-256 checksums; never overwrite conflicting existing assets.
- Document subsequent publication, consumer updates and retention. Keep the multi-package repository and ordinary VSF compilation.

## Capabilities

### New Capabilities

- `storefront-ui-package-publication`: preparation, traceable publication and retention of shared/Vue package release assets.

### Modified Capabilities

None; this repository previously had no canonical OpenSpec capabilities.

## Impact

New packaging scripts, focused tests, a publication workflow and documentation in `BudsiesApp/storefront-ui`, based on maintained `optimuspro`. Initial package payloads are extracted from their respective historical commits, not from the packaging checkout. Companion UI manifest/lock changes consume these assets. No registry, package renaming/version upgrade, standalone library build, customer behavior change, GitPkg teardown, or production deployment.

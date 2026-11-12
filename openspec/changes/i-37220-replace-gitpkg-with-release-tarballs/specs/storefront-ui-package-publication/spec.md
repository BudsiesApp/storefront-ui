# Spec Delta

## Purpose

Distribute prepared Storefront UI shared and Vue sources as traceable public release packages without requiring GitPkg or the legacy development toolchain during consumer installation.

## ADDED Requirements

### Requirement: Explicit independent source selection
Publication SHALL run through GitHub Actions in `BudsiesApp/storefront-ui` with explicitly selected shared and Vue source revisions, resolved to full commits independently of the packaging revision. The initial artifacts MUST preserve package names, versions and runtime dependencies except the documented shared dependency transport change.

#### Scenario: Initial migration
- **WHEN** the initial release is prepared
- **THEN** shared comes from `3ff374628936ba579a9bbb2a634c6c3ce9db6ac5` and Vue comes from `b345b9cb261dabf1c105f4e6007fe7332ec8b6a4`, with each package remaining version `0.7.11`
- **AND** differences from those package sources are limited to documented packaging preparation and manifest transport changes

#### Scenario: Later publication
- **WHEN** a maintainer explicitly selects source revisions in the release configuration and triggers publication with a release tag
- **THEN** the archives use those resolved package commits rather than implicitly taking both packages from the workflow checkout

### Requirement: Prepared Vue source distribution
The Vue archive SHALL include generated `index.js` and `storiesOf.js`, their referenced component/story files, styles and runtime sources required by existing consumers. Consumer installation MUST NOT generate entry files or prepare the source repository. Packaging MUST NOT install the complete legacy development toolchain or invoke the standalone library build.

#### Scenario: Archive is installed without package preparation
- **WHEN** the Vue archive is extracted and installed by VSF
- **THEN** both generated entry files already exist, component exports resolve to packaged sources, and no installation hook regenerates them
- **AND** `styles.scss`, `src/css`, component sources, utilities and shared style/icon/variable sources remain available at their existing import paths

#### Scenario: Packaging execution is inspected
- **WHEN** the workflow prepares the two archives
- **THEN** its logs show isolated source preparation and packaging without root/workspace development-toolchain installation or the standalone Vue library build

### Requirement: Release-only dependency transport
The Vue packaged manifest SHALL reference the matching shared release asset, and both packaged manifests MUST contain no GitPkg dependency URLs. Runtime dependency names and ranges MUST otherwise remain unchanged.

#### Scenario: Vue introduces an indirect shared dependency
- **WHEN** a consumer installs Vue and the shared package
- **THEN** Vue's shared dependency URL matches the corresponding published shared asset used by the consumer, without a GitPkg request or a second source revision

### Requirement: Public traceable release assets
GitHub Releases in the source repository SHALL host the prepared archives at stable release-specific anonymous-download URLs. Release metadata SHALL identify every package name, version, source subdirectory and full source commit, the full packaging revision, asset names and SHA-256 archive checksums.

#### Scenario: Published archive is downloaded anonymously
- **WHEN** a consumer downloads an archive without credentials from its release-specific URL
- **THEN** it receives the prepared package rather than a repository source archive or expiring Actions artifact, and its SHA-256 matches the release metadata

### Requirement: Existing release assets remain unchanged
Publication MUST NOT overwrite or delete previously published assets or repoint a consumed release URL. A repeat publication SHALL reuse identical existing content and reject conflicting archives or provenance instead of replacing them.

#### Scenario: Identical repeat
- **WHEN** publication targets an existing release whose corresponding assets and provenance are identical
- **THEN** it succeeds by reusing those assets without replacing their bytes

#### Scenario: Conflicting repeat
- **WHEN** publication targets an existing asset name with different archive contents or incompatible provenance
- **THEN** publication fails visibly and preserves all existing assets and their download URLs

### Requirement: Maintainer publication procedure
Maintenance documentation SHALL explain explicit source selection, prepared packaging, release publication, provenance/checksum verification, consumer manifest/lockfile updates and retention of previously consumed assets.

#### Scenario: Maintainer publishes a later revision
- **WHEN** a maintainer follows the documented procedure
- **THEN** they can publish a new release and update both direct and indirect dependency URLs without GitPkg, registry adoption or removal of historical assets

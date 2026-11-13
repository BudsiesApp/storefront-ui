# storefront-ui-package-publication Specification

## Purpose

Distribute prepared Storefront UI shared and Vue sources as traceable public release packages without requiring GitPkg or the legacy development toolchain during consumer installation.

## Requirements

### Requirement: Automatic stable branch publication
Every push to `optimuspro` SHALL publish a non-prerelease, immutable GitHub release with tag and title `optimuspro_<first seven characters of the triggering commit SHA>`. Shared and Vue sources and the packaging revision MUST use and record the full exact triggering commit, independently of historical release configuration. The Vue archive MUST reference the shared asset in the same release. Existing stable, tag-based and preview releases MUST remain available and unchanged.

#### Scenario: Stable branch advances
- **WHEN** a push updates `optimuspro`
- **THEN** the workflow publishes both prepared archives with provenance and checksums for that exact commit without changing consumers

#### Scenario: Stable release is repeated or conflicts
- **WHEN** the same stable publication is rerun
- **THEN** identical assets are reused, and an incompatible tag, release title, status or asset fails without replacing existing content
- **AND** a tag pointing to a different full commit fails even when that commit shares the same seven-character prefix

### Requirement: Explicit independent source selection
The explicit release-tag path SHALL run through GitHub Actions in `BudsiesApp/storefront-ui` with independently selected shared and Vue source commits. The on-demand path SHALL preserve this existing interface. The initial migration artifacts MUST preserve package names, versions and runtime dependencies except the documented shared dependency transport change.

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
The Vue packaged manifest SHALL reference the matching shared release asset, and both packaged manifests MUST contain no GitPkg dependency URLs. Runtime dependency names and ranges MUST otherwise remain unchanged from each artifact's selected source commit.

#### Scenario: Vue introduces an indirect shared dependency
- **WHEN** a consumer installs Vue and the shared package
- **THEN** Vue's shared dependency URL matches the corresponding published shared asset used by the consumer, without a GitPkg request or a second source revision

### Requirement: Public traceable release assets
GitHub Releases in the source repository SHALL host the prepared archives at stable release-specific anonymous-download URLs. Release metadata SHALL identify every package name, version, source subdirectory and full source commit, the full packaging revision, asset names and SHA-256 archive checksums.

#### Scenario: Published archive is downloaded anonymously
- **WHEN** a consumer downloads an archive without credentials from its release-specific URL
- **THEN** it receives the prepared package rather than a repository source archive or expiring Actions artifact, and its SHA-256 matches the release metadata

### Requirement: Existing release assets remain unchanged
Publication MUST NOT overwrite or delete previously published assets or repoint a consumed release URL. A repeat publication SHALL reuse identical existing content and reject conflicting archives or provenance instead of replacing them. The separately authorized feature-preview cleanup is the sole deletion exception described below.

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

### Requirement: On-demand independent preview selection
An authorized maintainer SHALL be able to invoke a documented preview command with independently selected shared and Vue branch/ref or commit inputs. Each distinct selected ref MUST resolve once to a full source commit. Unchanged-companion defaults MUST be visible. Unresolvable selections MUST fail clearly without falling back to another source.

#### Scenario: One package changes while its companion remains pinned
- **WHEN** a maintainer selects an unmerged Vue feature branch and uses the documented shared default, or explicitly selects shared and leaves Vue unchanged
- **THEN** the returned preview identifies both resolved source commits and uses the selected changed package with the visible unchanged companion

#### Scenario: The selected branch advances
- **WHEN** a branch moves after its ref was resolved for one invocation, and another preview is requested later
- **THEN** the first invocation uses only its original resolved commits and its URLs remain unchanged, while the later request resolves the branch again to the later commit

#### Scenario: Invalid selected source
- **WHEN** a selected branch/ref or commit cannot be resolved in the source repository
- **THEN** the command exits unsuccessfully with the failed selection identified and publishes no substitute package set

### Requirement: Preview invocation without publishing edits
The on-demand command SHALL publish prepared sources without per-iteration tracked configuration changes, source-expectation test edits, packaging-config/test commits or manually created tags. Generic checks MUST validate requested resolved sources independently of dedicated initial-pin regression coverage. The same command MUST accept an explicit final merged source revision.

#### Scenario: Feature iteration and post-merge selection
- **WHEN** a maintainer invokes previews for a feature commit, a later commit and then its merged commit
- **THEN** each invocation needs only source selection, not edits to publishing configuration or tests, and preserves the initial-pin regression assertions

### Requirement: Immutable preview identity and complete handoff
Each preview SHALL identify the repository, resolved shared/Vue source commits and packaging commit. A new source or packaging identity MUST use a distinct public release identity. Success MUST return both exact anonymous package URLs and provenance/checksum locations only for a complete verified matching asset set, with Vue's shared URL exactly equal to the returned shared asset.

#### Scenario: Matching preview is reused
- **WHEN** the same on-demand resolved source and complete packaging identity, including the recorded toolchain, is requested again through the same or a different ref spelling
- **THEN** a complete matching preview is reused without replacing its assets, and the same package and provenance/checksum URLs are returned

#### Scenario: Conflict or interrupted publication
- **WHEN** the preview identity already has conflicting or incomplete assets
- **THEN** conflicting existing bytes/provenance are preserved and the command fails rather than overwriting them; an incomplete matching set can be completed without replacement, but no incomplete set is reported as success

#### Scenario: Packaging or merge identity changes
- **WHEN** a selected source or packaging commit differs, including a new merge commit with similar file contents
- **THEN** the command uses a distinct preview identity and retains previously consumed URLs except when an eligible feature preview is later cleaned up

### Requirement: Automatic branch preview publication
Pushes to non-maintained branches containing the preview workflow SHALL publish a public prerelease titled and tagged `<branch>_<first seven characters of the triggering commit SHA>`, with both package sources and packaging revision set to the full exact pushed commit. Publication MUST wait until compatible cleanup support is on `optimuspro` and MUST NOT update or deploy consumers.

#### Scenario: Maintained and internal branches
- **WHEN** a push targets the default, `optimuspro`, `main`, `master`, `develop` or `preview-cleanup/` branch
- **THEN** no branch preview is published

#### Scenario: Publication handoff
- **WHEN** publication succeeds
- **THEN** the workflow summary identifies the release, source commit, tracking state, package URLs, manifest and checksums

#### Scenario: Branch advances rapidly
- **WHEN** two commits are pushed to a branch with the workflow
- **THEN** each publication uses its own triggering commit rather than the later branch head, subject to GitHub Actions trigger and concurrency limits

#### Scenario: Branch name contains a slash
- **WHEN** a branch-named preview is published
- **THEN** the release tag preserves the branch name and asset URLs encode the tag as a single URL path component; the Vue archive references the matching shared asset

#### Scenario: Existing publication conflicts
- **WHEN** a branch tag, release status, title, provenance or asset conflicts
- **THEN** publication fails without replacing existing assets or repointing the tag

### Requirement: Feature-preview cleanup
New preview releases SHALL record eligible branch associations outside immutable assets. Scheduled cleanup MAY delete a trusted tracked preview only after every associated branch has been observed absent for at least 30 days. Publication, tracking and cleanup MUST serialize; errors MUST fail safe. Deleting a preview makes its URLs unavailable but MUST NOT delete its Git tag. A branch already absent when an automatic preview is published MUST be pinned because its protection cannot be verified.

#### Scenario: Exclusions and reuse
- **WHEN** a release is stable, untracked, commit-only, protected or associated with a maintained branch
- **THEN** cleanup does not delete it; explicit commit-only reuse permanently prevents cleanup
- **AND** reuse from a feature branch records that association before success
- **AND** an omitted historical companion does not prevent tracking the explicitly selected feature branch

#### Scenario: Reappearance or multiple associations
- **WHEN** any associated branch is observed present
- **THEN** its deletion timer resets and cleanup waits until all associations have independently aged through 30 days of observed absence

#### Scenario: Observed-state limitations
- **WHEN** a branch reappears between scheduled observations or after the final check
- **THEN** the reappearance can be missed because branch writes are not atomic with release deletion; maintainers MUST be informed of this limitation

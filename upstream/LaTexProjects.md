# LaTexProjects extraction inventory (N1.1)

**Status:** read-only source audit; proposed dispositions, not authorization to copy or redistribute. Reviewed on 26 November 2026. Source: [Gonza10V/LaTexProjects at 906a18074080635271b87cb29a063498ea75b3b0](https://github.com/Gonza10V/LaTexProjects/tree/906a18074080635271b87cb29a063498ea75b3b0), branch `main`. The GitHub recursive tree response was not truncated (1,035 entries). Root `VERSION` reads `0.1.4`; this is the upstream version, not a Neruda version. No working research content was downloaded or copied into this package. Working document trees were inventoried by path/identity rather than by reading individual document contents.

## License and disposition key

The upstream [LICENSE](https://github.com/Gonza10V/LaTexProjects/blob/906a18074080635271b87cb29a063498ea75b3b0/LICENSE) is MIT, copyright 2026 DRAGGON Lab contributors. Its README explicitly limits that license to repository-owned templates, scripts, docs and examples and preserves independent terms for research sources, publisher files, datasets, logos and branding. Observed root license is not component-level clearance or university approval. Preserve original notices and check ownership, third-party content, dependencies and distribution terms before extraction. No candidate is approved for copying by this manifest.

- **Candidate:** useful reusable infrastructure; review content, rights, dependencies and behavior before copying/adapting.
- **Adapt:** architecture is useful but known portability, safety, semantics or documentation changes are required.
- **Reference:** learn from or link to the source; do not copy wholesale.
- **Exclude:** not part of Neruda's infrastructure extraction. No permission to move or delete source.

All digests below are Git object IDs observed in the pinned tree (SHA-1 blob/tree identities), not independently computed SHA-256 file hashes. The commit plus path and Git object ID identify the source bytes or subtree. Obtain actual file/archive SHA-256 hashes and applicable third-party terms during extraction and toolchain verification. Source-level MIT is an initial candidate assumption for owned files; asset-specific clearance remains pending.

## 1. Infrastructure and compatibility inventory

| Source path | Git blob ID | Disposition and review requirement |
|---|---|---|
| `LICENSE` | `fbfd3e02392b521934e41d3a4fe67f3e1b870aa2` | Reference; preserve copyright/permission notices for reused owned files; do not replace existing Neruda license silently. |
| `VERSION` | `845639eef26c0e95586203ae78369f67552ccb17` | Reference upstream version only; independent Neruda version. |
| `README.md` | `e8acdbe0837d654dd6f9e81f3ba4ab20c1e2f0cd` | Reference documented workflows, license boundary and limitations; rewrite Neruda guidance. |
| `AGENTS.md` | `60e350d5e78c8a29859646d696a1b4ccd13c04bc` | Reference approval/build/QA conventions; avoid course-specific or other agent harness dependencies. |
| `Makefile` | `a9fcbc147e6d6d0535fb072fe97b893075276101` | Adapt entry points for independently owned projects; inspect version checks and shell path safety. |
| `scripts/tectonic.sh` | `60fabffd89a81bedf38c930a5b50c31255c82c68` | Adapt; remove host-local and workshop fallback, verify exact version and cache behavior. |
| `scripts/install-tectonic.sh` | `ec18469284fc2f4e8ca2e6410e08a1712b485b60` | Adapt; explicit permission, verified official archive hash, platform and extraction safety. |
| `scripts/scaffold-project.sh` | `bb2079a4ea81f9083e1580c1e88450beb3d79ba1` | Adapt; safe names/non-overwrite pattern, independent project layout, containment and symlink tests. |
| `scripts/build-project.sh` | `281398d019e0dc313c3ae5aa7f2d4f66e83f94f9` | Adapt; project boundary, exact bibliography version, safe build/clean and provenance. |
| `scripts/build-all.sh` | `be25a9171cd7f4f75ebcce5db12b2c7f6a21f5a3` | Adapt; discover explicit synthetic fixtures only, robust path handling and non-destructive behavior. |
| `scripts/check-latex-log.sh` | `b5ab61a17d621b63409e50cdba4097dc8e61f782` | Adapt; preserve undefined ref/citation diagnostics, test missing logs, path handling, meaningful warnings and false negatives. |
| `tools/tectonic/VERSION` | `c5523bd09b187d88eb8caeb979852a301d6c2728` | Reference observed Tectonic 0.17.0 candidate; verify in N1.2. |
| `tools/tectonic/SHA256SUMS` | `5e586435dc291de52dfa9758f1e4ebc0b65bc7b8` | Reference checksum coverage; only Intel macOS archive listed. Verify official archives per selected platform. |
| `.github/workflows/latex.yml` | `413565444134bc2f526d593634063c7b00c74d86` | Adapt clean CI design; remove workshop notebook jobs, separate synthetic outputs, verify dependency/action pins and permissions. |
| `tex/draggonlab.sty` | `93fada466998ac43add88a387fbf76add0890689` | Candidate; semantic macros/units and Unicode font packages, brand rights and dependency review; verify compatible engines. |
| `tex/beamerthemeDRAGGON.sty` | `bf852f14d1294c0c304bc5e1862f9064aba433be` | Candidate; theme, semantic styles, 8 mm margin, branding and accessibility; render before/after all template frames. |
| `docs/authoring-guide.md` | `12e145cf8b452e3bd8cc5f237315b75689611d82` | Reference layout and evidence conventions; adapt ordered symbol definitions and shared interface. |
| `docs/build-and-release.md` | `717c960322b861db14f4a0b8355e2e0967558a87` | Reference pinned compatibility and publisher override; revise based on N1.2 observed results. |
| `docs/agent-harness.md` | `39486daf1d1f041d2a2ac1c90b5ef73dc1ebe74c` | Reference historical audit only; do not inherit host-specific paths or claim fresh builds. |
| `docs/submission-checklist.md` | `37d2b249c6161c8de02d7397912c613d652c5a90` | Candidate guidance for independent review; verify journal policy and authorship at actual submission. |
| `CHANGELOG.md` | `06e4482d0ff55fc61011d69db4401c26a1ca8cb1` | Reference upstream history, not a Neruda changelog. |
| `.editorconfig` | `a722c3ec4240b74a445c6c4d3e3eb9439297c54a` | Candidate convention; content and license review pending. |
| `.gitignore` | `fed4596e0e666735c1b13ed3fc83a3e2b35e004f` | Candidate patterns; validate actual layout, outputs, private materials and secret exclusion. |

## 2. Template inventory

The source trees `templates/papers/base` (`ffc2764c6221a5bbe0aa5511605813de26816490`) and `templates/slides/base` (`07c2fbd4c09a8e84f4085389477128a9db2ef395`) are candidates, not bulk-copy approval. The paths below are relative to those directories; the tree IDs also identify their ancillary README evidence directories. The key templates, manifests, metadata, sample bibliography and section excerpts were inspected statically. Remaining ancillary README content and the full mathematical example need line-level review before import. Rework the example mathematics and sample plots/results to meet the approved ordered-symbol and explicit synthetic/theoretical labeling requirements; no example value is empirical evidence.

### Paper starter (`templates/papers/base/`)

| Path | Git blob ID | Disposition |
|---|---|---|
| `README.md` | `f7f094cbcb81816b74646d3dc1e8b2db47e555ae` | Adapt commands/standalone guidance. |
| `Tectonic.toml` | `9839d115ddb87ce9b597346612159d73e2e0d6a0` | Adapt bundle/relative path after N1.2; keep shell escape off. |
| `src/main.tex` | `838f54d9b9e971508f7491bca6baed109b89ba59` | Candidate article, references and modular structure; review publisher and placeholder semantics. |
| `src/metadata.tex` | `42d08bfd33b090ea74b86f1ad50a9c2f190ad9da` | Adapt demo authors/URLs/date; no real authorship defaults. |
| `src/bib/references.bib` | `e2d7637ad92048ccc786a640c372cd24d587bf73` | Reference example bibliographic record, verify relevance and terms before reuse. |
| `src/sections/abstract.tex` | `7ab4837bd9140da7499ffc4be64647be972cc4db` | Candidate narrative placeholder; label synthetic. |
| `src/sections/introduction.tex` | `500414d45323b2a03aec38b0b694c5b781c31822` | Candidate; verify citations and gap framing. |
| `src/sections/mathematical-concepts.tex` | `bb0e24f04955d610a7eab98928faf1e6cc320081` | Adapt math example to ordered symbol definitions, meaningful checks and full review. |
| `src/sections/results.tex` | `68b9f3aa51c4549445c9773cfe30b5d6d7d10d3a` | Adapt examples, explicitly synthetic, uncertainty and provenance. |
| `src/sections/methods.tex` | `08667975e7c707669c76bb70d1a743628dd69254` | Candidate methods guidance, domain-appropriate controls. |
| `src/sections/discussion.tex` | `f4e7681c74e9e9d1551f961af7cfb8da2d950b62` | Candidate limitations and interpretation. |
| `src/sections/conclusions.tex` | `d630d5597c28eb00c851d460efcc41800774d6e9` | Candidate bounded conclusions. |
| `data/raw/README.md` | `75b983a1d8b254f7b7d68dd6f8d2a6ee469dbea2` | Candidate documentation only; no data. |
| `data/processed/README.md` | `3e93f39d0d735d5de10a006b478fc72765848c04` | Candidate documentation only. |
| `figures/source/README.md` | `6ef7cacc753a0f925d4928f9ae1e3f598e76d620` | Candidate documentation only. |
| `figures/generated/README.md` | `f246dc3d3631b2cb69a10fac860b2b46a782f121` | Candidate documentation only. |
| `sources/documents/README.md` | `72a6b836ab423b9b9e847c3b6de6dcd57e69cd65` | Candidate documentation; cite/ref only permitted content. |
| `sources/images/README.md` | `29ae403328bd780812f3aa6a10e6e7e2a505abd4` | Candidate documentation; attribution/permissions. |

### Slide starter (`templates/slides/base/`)

| Path | Git blob ID | Disposition |
|---|---|---|
| `README.md` | `443a7a4a639ef0b9a326174423f8bc7b754b99af` | Adapt handout and validated commands. |
| `Tectonic.toml` | `fab98a1af7da9600888ae2cd75877f3e0fe5ae67` | Adapt bundle/relative path after N1.2; shell escape off. |
| `src/main.tex` | `5c67e5c3bda2d2cfa4acec667a4b24eb82f6f206` | Candidate 16:9 Beamer and modular entry. |
| `src/metadata.tex` | `182b1c8b80992187f149fbe37a868377ac8abcf3` | Adapt example metadata, no author defaults. |
| `src/bib/references.bib` | `7dc1d12055e562daa7ae85e4fbdd247117814525` | Reference demo bibliography; verify. |
| `src/sections/motivation.tex` | `716a921e29f5fce2d7474061d4261250f2c09902` | Candidate audience problem framing. |
| `src/sections/methods.tex` | `289ae5bde64af04c5b33582e1f968e19b0833e57` | Adapt equations with immediate ordered definitions; visual review. |
| `src/sections/results.tex` | `02b4775c395ef2f61307e0fd49adab98c8122469` | Adapt example plot (illustration, not measured confidence); label and define axes. |
| `src/sections/conclusions.tex` | `aee5f3d3cf776fae5df0e39012e9afa08328f399` | Candidate; verify message and source. |
| `src/sections/backup.tex` | `c99d3525b1649cc215e82f3d7f1f06175821109c` | Candidate build identity/reference frame. |
| `data/raw/README.md` | `b086c298e3593ff3715b9f05f474544be996dd4e` | Candidate documentation only. |
| `data/processed/README.md` | `7ec6f8e47740feb9bf3676e9b2af62e162d7be58` | Candidate documentation only. |
| `figures/source/README.md` | `64c9d1922811e5db3f6b358c50c7239878b76c09` | Candidate documentation only. |
| `figures/generated/README.md` | `101954e94b87b57eb638a4926d1a3a500dfa02fe` | Candidate documentation only. |
| `sources/documents/README.md` | `4758ff2b2210aff27a860a201b7c93214a6ec172` | Candidate documentation; licensed sources only. |
| `sources/images/README.md` | `defec07625fd7940218a17e3651c476ceb8e1e35` | Candidate documentation; attribution/permission. |

## 3. Explicit exclusions

| Source scope | Git tree/object ID where observed | Rationale |
|---|---|---|
| `projects/` (including `projects/papers/` and `projects/slides/`) | `660cdc9cd5f846fe16df6ff9aaa1db85c0953dd8` | All working documents, project data, course material, generated PDFs/images, environment binaries and project-specific code remain project-owned; 906 tree entries under `projects/`, not individual cleared assets. |
| `projects/papers/` | `d37aec30186759a57cb28248795ad6eafbd6b881` | No manuscript/source/data migration. |
| `projects/slides/` | `a8f6a8529b70f0791e762d7014fccfa9c7f86c3d` | No existing slide/teaching/workshop migration. |
| `SEMTM0003_2026-27_RNA_Sensor/` | `87719cc5d73e17cf7a70db7f7017e0d4fbadcfe3` | Exclude teaching/assessment and associated project-specific material. |
| `docs/research/` | `dfb8d9b3ed32c4f0ffdcb47672665815d5d3cd82` | Exclude bulk research documents; separate authorization and attribution if a reference is needed. |
| `.claude/`, `.cursor/` | `aa413e1a9b259338a2bf25c06829153bce64b2ae`, `c3b0b68d27ca5d7def72a9bb6fa8f3154ec40f7e` | Exclude platform-specific hooks/configuration and personal tooling. |
| Other MCP, Graft, Copilot configuration and unrelated files | Pinned source tree, not allowlisted | Not necessary for standalone Neruda; no copying. |
| Binaries, caches, `.venv`, generated outputs, publisher-owned files, external sources/images/fonts and private data | Not separately cleared | Exclude by default. Use approved official distributions or controlled references; do not inherit a host-local installation or redistribution right. |

All paths not explicitly listed as candidate/adapt remain excluded unless separately reviewed. Git tree inspection cannot enumerate untracked host files; no local tool or cache was examined. No binary content, private manuscripts or existing research data were copied.

## 4. Observed compatibility and blockers

| Observation at pinned source | Implication for N1.2/N1.3/N1.4 |
|---|---|
| `tools/tectonic/VERSION` = `0.17.0`; both `Tectonic.toml` use `https://data1.fullyjustified.net/tlextras-2022.0r0.tar`, `shell_escape = false`; build/release doc pairs Biber 2.17 with biblatex 3.17. | Test reviewed compatibility unit and clean bibliography/figure builds; validate source, archive/bundle, font and cache identity; no claim these pins are latest. |
| Installer selects Darwin/Linux x86_64/aarch64 targets; `SHA256SUMS` contains only `tectonic-0.17.0-x86_64-apple-darwin.tar.gz` with digest `7c90ef5b6ddb1eb1937e4337add5237b79338e4b9676459fa91187d24d6cdf80`. | Source selection is not proven OS support. Obtain and verify platform-specific official checksums/terms. No unreviewed installation. |
| Wrapper falls back to a specific workshop `.tools/` path and `/private/tmp/tectonic-vcc-cache`; wrapper version check uses substring matching. | Remove host/project assumptions; design exact version checks and explicit cache/network policy; verify cold and warm build in clean environment. |
| Build helper checks for Biber executable on PATH rather than proving exact compatible version; historical September 2026 audit says Biber missing locally at that time. | Verify actual bibliography binary/version and behavior. Do not conflate historical audit with present environment. |
| Upstream scaffold refuses non-kebab case and existing targets, copies template without `build/`; assumes destination directories and same relative layout. | Test standalone independent project layout, existing destination, traversal and symlink boundaries; reject overwrites. |
| Build-all/log helpers split discovered paths on whitespace and rely on the upstream layout; log checker detects selected unresolved citations/refs/missing logs. | Validate supported path spaces, nonzero exits, missing/false-pass logs, warnings, safe build/clean and artifact scope. |
| CI on `ubuntu-latest` uses setup-tectonic pins, read-only repository permission, builds all discovered workspaces and runs unrelated workshop notebooks. | New CI should build only public synthetic fixtures, verify pins and local parity; avoid course dependencies and private PDF/log upload. Do not infer CI success from YAML. |
| Shared style uses fontspec, unicode-math, mathtools, siunitx, booktabs and other packages; rejects pdfTeX. Theme uses shared palette/semantic macros; default Beamer 16:9, 8 mm margin and handout option. | Verify package/font compatibility, brand permission and actual rendering/accessibility; journal-specific class/engine overrides reviewed separately. |
| Sample template equations/plots and metadata include illustrative values and placeholder claims/URLs. | Keep examples clearly synthetic, no scientific claims by default, ordered symbol definitions and reproducible evidence fixtures. |

Historical upstream commands, inspected as source (not available or tested in Neruda): `./scripts/tectonic.sh --version`, `make new-paper NAME=...`, `make new-slides NAME=...`, `./scripts/build-project.sh paper|slides ...`, `make check`, `./scripts/check-latex-log.sh`. Tool installation requires explicit permission even upstream; do not interpret this inventory as permission to run them. The old compiler, Biber, bundle and publisher alternatives are evaluated in N1.2. No clean build, installer run, log test or rendering occurred in N1.1.

## 5. Migration acceptance and next steps

N1.1 can be reviewed now for correct scope, documented source identity, standalone architecture and exclusions. The IP/release reviewer must accept the extraction candidates and dispositions; unresolved component rights block actual copying. N1.2 tests the minimal independently usable toolchain, captures versions/checksums/logs and supported platform matrix (or explicit blockers), and records a follow-on ADR. N1.3 extracts only cleared assets, removes upstream-specific dependencies and tests safe scaffold/semantic templates; N1.4 builds/checks and provenance; N1.5 validates clean standalone article, slides and handout, page review and upgrade/rollback. A3.1/N2.1 specify shared evidence references separately. Preserve source revision, path, original notice, adaptation rationale, changed paths, validation status and reviewer in each import PR. Actual extraction, commits, installs and publication are outside this review-only task.

## N1.3 disposition

The approved N1.3 scope used this inventory as a design reference for semantic
notation, standalone layout and a 16:9 Beamer handout. Neruda authored its
scaffolder, templates and styles in this repository. The starter uses the lab
name as text and carries Neruda's existing MIT license for its original assets.
See the [provenance and verification record](../docs/n1-3-scaffold.md).

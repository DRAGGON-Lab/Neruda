# Neruda

**A reproducible scientific communication framework**

Neruda is DRAGGON Lab's LaTeX-first infrastructure for building traceable scientific manuscripts, presentations and figures. It treats scientific documents as versioned, reviewable build products: content, bibliography, mathematical notation, figure source, data references, compiler and generated artifacts have explicit identities.

**Status:** Apple Silicon first, portability by design. The native MacTeX/LuaLaTeX candidate has local article, slide, handout and offline-build evidence. Native compatibility awaits independent review and maintainer acceptance. Cross-platform validation is deferred to [N1.2b](https://github.com/DRAGGON-Lab/Neruda/issues/12). [LaTexProjects](https://github.com/Gonza10V/LaTexProjects) remains the migration reference.

## Planned capabilities

- Standalone versioned article and 16:9 Beamer templates, shared semantic mathematics and DRAGGON Lab visual conventions.
- Reviewed, pinned LaTeX compiler/bibliography compatibility unit, non-installing preflight, safe scaffolding, explicit figure generation and build/log validation.
- Project-owned manuscripts and presentations linked to source evidence, with reproducible figures, semantic references and audit-ready provenance.
- Nature-inspired scientific writing conventions, living manuscripts, audience-specific presentations and journal adaptations, supported by independent authoring/review workflows in [ANDES](https://github.com/DRAGGON-Lab/ANDES).
- Standalone use without AI or ANDES installed. No mandatory network service, personal account or hidden host cache.

## Start here

| Document | Purpose |
|---|---|
| [PRODUCT.md](PRODUCT.md) | Users, use cases, staged scope and success criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Template/toolchain boundaries, evidence flow and deployment |
| [AGENTS.md](AGENTS.md) | Agent startup and non-installing preflight rules |
| [AGENT.md](AGENT.md) | ChatGPT/Codex coordination and document verification |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution, privacy, review and release gates |
| [Design baseline](docs/design-baseline.md) | Approved decisions and cross-repository interface ownership |
| [ADR-001](docs/decisions/ADR-001.md) | Selective extraction and standalone package boundary |
| [Extraction inventory](upstream/LaTexProjects.md) | Pinned upstream source, digests, compatibility findings, exclusions and migration disposition |

## Candidate build stack

Use [the stack guide](docs/latex-stack.md) for the implemented command-line driver,
verified native setup, optional editor configuration and remaining gates. See
[compatibility evidence](docs/n1-2-compatibility.md) and [ADR-003](docs/decisions/ADR-003.md).
The driver never installs dependencies or silently selects another compiler.

## Local development

Clone using authorized Git access and inspect the actual checkout:

```sh
git clone https://github.com/DRAGGON-Lab/Neruda.git
cd Neruda
git rev-parse HEAD
git status --short
```

Use only the implemented candidate commands and explicitly verified dependencies.
Do not invoke upstream script names as native commands or install tools without
approval. [N1.2a](https://github.com/DRAGGON-Lab/Neruda/issues/2) reviews the
native stack. The compatibility report preserves the historical Tectonic
investigation alongside the native results.

### Planned layout

```text
Neruda/
  README.md  PRODUCT.md  ARCHITECTURE.md
  AGENTS.md  AGENT.md  CONTRIBUTING.md
  docs/ upstream/           design, ADRs, reviewed extraction provenance
  tex/                      versioned semantic styles and Beamer theme
  templates/papers/         base and justified document-type variants
  templates/slides/         16:9 Beamer and handout variants
  tools/ scripts/           reviewed pins, scaffold/build/check entry points
  examples/ tests/          synthetic examples and negative fixtures
```

Style/template/scaffold modules remain planned; candidate tools, scripts and tests are implemented for the compatibility investigation. Individual research documents belong in their own project repositories or restricted collections. Keep the upstream LaTexProjects working projects intact. Production packaging and release remain gated on compatibility acceptance.

### Toolchain and testing

The Python driver provides non-installing preflight, build and output checks.
Both behavioral regression suites run on pull requests. Run native integrity and
build checks on a Mac with the provisioned pins. The Linux TeX Live and historical
Tectonic workflows run by explicit dispatch for authorized investigations.
Installing, repairing or changing the toolchain or locks requires explicit approval.
The candidate disables shell escape.

Future release checks include safe scaffolding (no overwrite/path traversal), version checks and missing-tool diagnostics, clean paper and slide builds without ANDES, unresolved references/citations checks, explicit figure provenance and visual inspection of every page/slide. A successful compilation alone is not scientific validity or publication readiness.

## Collaboration and governance

ChatGPT investigates scientific narrative, scope, evidence and design choices. Codex implements authorized document/build changes and returns real verification artifacts. Humans remain accountable for claims, authorship, permissions, target-journal requirements and publication. Start with [AGENTS.md](AGENTS.md).

Public infrastructure, private research, controlled stable releases. The existing [MIT license](LICENSE) applies to original repository material; third-party source documents, datasets, branding, images, fonts, publisher files and tools retain their own terms. No working manuscripts or research data are copied into the infrastructure repository to make a build succeed.

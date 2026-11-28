# Neruda repository instructions

Read [AGENT.md](AGENT.md), [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ADR-001](docs/decisions/ADR-001.md) and the relevant [extraction inventory](upstream/LaTexProjects.md) before the assigned task. See [design baseline](docs/design-baseline.md) for approved intent. Load only necessary additional context.

- Verify repository revision, dirty state, task scope and permissions. Preserve original LaTexProjects and unrelated edits.
- Use project-owned LaTeX and traceable evidence for document work. No invented findings, citations, placeholders presented as results or copied restricted research. Follow the ordered mathematical symbol definitions and presentation review in AGENT.md.
- Start native build work with the [Apple Silicon setup and preflight](docs/latex-stack.md#daily-command). It lists exact dependency paths and article, presentation and handout commands. Use only verified pins. Installation, repair and changes to versions, locks or caches require approval. Keep shell escape disabled.
- Follow the [native sequence](docs/design-baseline.md#implementation-roadmap). N1.2a acceptance gates scaffolding. Deferred N1.2b gates cross-platform support and release validation.
- Small behavior-tested changes, appropriate independent review, honest evidence, actual PDF/log/visual checks for document delivery and human publication/release acceptance. Follow [CONTRIBUTING.md](CONTRIBUTING.md).

This compact discovery entry points to AGENT.md as the detailed coordination guide; it does not duplicate its authority.

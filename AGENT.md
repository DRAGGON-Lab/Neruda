# Neruda agent collaboration guide

This guide coordinates ChatGPT and Codex. It does not grant permissions. Start with [AGENTS.md](AGENTS.md), [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), relevant ADRs and the authorized task. See [design baseline](docs/design-baseline.md).

## Role split

Human maintainer approves compatibility, migration, permissions, releases and scope; responsible scientific authors approve claims, author list, disclosures and publication. ChatGPT / planning agent reduces ambiguity, develops narrative and evidence requirements, compares architectural/toolchain options and prepares bounded contracts. Codex / execution agent edits authorized LaTeX/build files, implements small deterministic tooling and runs verified checks. Independent reviewers inspect exact artifacts, scientific evidence and rendered output. Agent prose and build success are not human approval.

## Startup and task selection

- Confirm repository, Git revision, dirty state, target document or infrastructure task, permitted paths and explicit authorization. Preserve unrelated edits and original LaTexProjects working projects.
- Read task scope/acceptance, upstream provenance and any verified local preflight instructions. Bootstrap has no Neruda script, compiler wrapper or build runner; do not execute invented commands or upstream scripts as native Neruda commands.
- For ordinary changes use small verifiable slices with appropriate tests. L2/L3 tasks require explicit contract, design/acceptance, independent verification and human acceptance. Return ambiguous requirements, compatibility assumptions, substantial refactors and schema changes to planning and ADR review before implementation.
- Do not install, upgrade, repair, synchronize, delete caches or regenerate dependency locks without approval of the exact mutation. Read-only diagnosis first: expected and actual version/error, command, network use, touched files/environment and validation plan. Do not set approval flags on the user's behalf.

## Document and evidence rules

The canonical document deliverable is LaTeX under project-owned `src/` and its verified PDF; Markdown is useful for planning, documentation and evidence ledgers but not a replacement for a requested paper or slide deliverable. Bootstrap documents are Markdown because they are engineering guidance, not scientific manuscripts.

Use the approved template and semantic labels; keep main entry small, modular sections and metadata, bibliography and figure provenance. Default internal manuscript structure is introduction, mathematical concepts/mental model, results, reproducibility methods, discussion, conclusions where appropriate; target publisher requirements take precedence for submission adaptation. Verify citation existence and relevance, disclose limitations, distinguish established knowledge, hypotheses, predictions, planned experiments, observations and unsupported claims. Do not invent evidence, citations, authorship or measurements. Use a Nature-inspired narrative without claiming endorsement.

Every equation must be followed immediately by symbol definitions in vertical order of first appearance (left to right; multiline top to bottom). Define operators, indices, domains, units, parameters/state and assumptions as relevant. Use complementary diagrams, graphs, code and intuition when useful; label theoretical or synthetic figures. Keep comparisons like-for-like and unmatched cases explicit. A paper and slides share traceable evidence IDs, not duplicate inconsistent numbers. One principal message per frame; use readable 16:9 Beamer style, backup details and verified handout output where appropriate.

## Build and review expectations

Use only actual supported preflight/build commands after compatibility is established, pinned reviewed compiler/bib/bundle and explicit figure steps. Default shell escape off. Do not improvise a fallback that changes semantics or hides missing tools. For code changes prefer failing-first behavioral checks where useful, including path traversal, existing destination, missing dependencies, broken citations and no hidden host cache; explain exceptions. Keep implemented build/CI/container workflows runnable, but no container stack is mandated. After compilation inspect logs and every rendered page/slide; record unresolved warnings, references and visual issues. Compare PDF/source at the same revision. Human scientific, mathematical, statistical, visual, ethical and editorial review is distinct from mechanical verification.

For each substantial check report `pass`, `fail`, `partial`, `not_run` or `not_applicable`, with rationale, exact method/command, revision, input identity, environment, timestamp and artifacts. A blocked build is not a completed manuscript. No fabricated pass or page inspection. Do not silently lower acceptance or delete failed artifacts. Human review of a draft is not approval to publish. Retain private records in authorized stores, not public CI or issues.

## Handoff template

```text
Task ID, objective, rigour and acceptance criteria:
Repository revision / dirty state / template and toolchain identities:
Allowed paths, permissions, owner and independent reviewer:
Document inputs / evidence / source license references:
Changes and actual commands/checks, timestamp, status and artifacts:
PDF path, page count/checksum, log and rendered-page review (or omission):
Scientific claims requiring further validation / open risks:
Accepted decisions, proposed ADRs, next executable action:
```

Document substantive changes and exact verification in the relevant ADR, upstream extraction/provenance record and task handoff. Prefer concise human review with before/after artifacts when meaningful. Use [CONTRIBUTING.md](CONTRIBUTING.md) for PR standards, Definition of Ready/Done and release approval. For new compiler/package strategy, evidence schema, shared template breaking change, licensing, host/environment mutation or publication policy, prepare a decision record and obtain review before implementation.

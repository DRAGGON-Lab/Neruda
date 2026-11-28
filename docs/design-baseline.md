# Approved design baseline

Design v0.1 and Implementation Plan v0.1 (approved 26 November 2026) govern intended behavior. The full approved decision register is maintained in the authorized planning workspace; this public-safe index points to derived repository documentation without redistributing private planning conversations or research.

| Decisions | Repository interpretation |
|---|---|
| 1.5, 8.1 | Neruda independently versioned, project-owned documents and optional restricted collections; [architecture](../ARCHITECTURE.md) and [ADR-001](decisions/ADR-001.md). |
| 8.2-8.4 | Canonical lab document types, Nature-inspired methodology, living manuscripts and audience-specific presentations from shared evidence; [product](../PRODUCT.md). |
| 3.4, 6.1-6.5 | Multimodal explanations, epistemic distinctions, scientific provenance and ordered mathematical symbol definitions; [agent guide](../AGENT.md). |
| 2.1-2.4, 7.6 | Proportional verification and authority, concise issues and PRs; [contribution policy](../CONTRIBUTING.md). |
| 10.1, 10.3-10.4 | Public infrastructure, private research, human-governed release and staged delivery; [contribution policy](../CONTRIBUTING.md) and [product](../PRODUCT.md). |

## Implementation roadmap

The maintainer's native-first decision amends the Neruda portion of Implementation Plan v0.1 and its backlog. The [N1 epic](https://github.com/DRAGGON-Lab/Neruda/issues/3) is the live coordination record. Historical N1.2 evidence remains associated with issue #2 and PR #11.

| Task | Prerequisite and outcome |
|---|---|
| N1.1 | Accepted extraction audit. The [inventory](../upstream/LaTexProjects.md) records source identities and open clearance. |
| [N1.2a](https://github.com/DRAGGON-Lab/Neruda/issues/2) | After N1.1, independently review and accept exact native Apple Silicon compatibility. |
| [N1.3](https://github.com/DRAGGON-Lab/Neruda/issues/5) | After N1.2a acceptance, clear sources and branding and deliver safe standalone scaffolding and shared styles in a separate PR. |
| [N1.4](https://github.com/DRAGGON-Lab/Neruda/issues/6) | After N1.3, implement native build/check and artifact provenance using the accepted N1.2a contract. |
| [N1.5](https://github.com/DRAGGON-Lab/Neruda/issues/7) | After N1.4, validate a clean standalone candidate, all rendered pages, upgrade/rollback and exact maintainer release approval for the declared platform scope. |
| [N1.2b](https://github.com/DRAGGON-Lab/Neruda/issues/12) | Deferred. Required for declaring cross-platform support and completing the cross-platform release gate. |

N2.1 depends on N1.1 and ANDES A3.1. It defines a versioned evidence contract without runtime coupling. N2.3 retains its N1.5 dependency. Each task needs its own acceptance and authority.

## Scientific communication sources inherited from the approved design

These are references to methodology, not copied content or an endorsement. The design session used accessible guidance; the full text of Scientific Writing 101 was subscription-restricted. Verify target-journal requirements separately at submission.

- [Nature summary paragraph](https://www.nature.com/documents/nature-summary-paragraph.pdf)
- [Effective Writing](https://www.nature.com/scitable/topicpage/effective-writing-13815989/)
- [Scientific Writing 101](https://www.nature.com/articles/nsmb0210-139)
- [Nature Portfolio author guidance](https://www.nature.com/nature-portfolio/for-authors/write)
- [Writing for Greater Impact](https://www.nature.com/masterclasses/writing-for-greater-impact/50732650)

The [LaTexProjects inventory](../upstream/LaTexProjects.md) is a fresh pinned source audit, not evidence of current Neruda functionality. Existing source, licenses, runtime claims and actual checks remain distinct. Keep design intent, observed behavior, provenance and research evidence in their respective authoritative records.

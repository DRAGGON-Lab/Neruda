# Neruda product definition

**Status:** approved product direction (Design v0.1); bootstrap wording for review. See [design baseline](docs/design-baseline.md).

## Problem and users

Research narratives, mathematical models, figures, evidence and presentation slides frequently evolve separately. Manual formatting and undocumented compiler environments make documents difficult to rebuild, verify and maintain. Neruda addresses document infrastructure and reproducibility while leaving scientific judgment and human authorship intact.

| User | Job to be done |
|---|---|
| Student / researcher | Create living scientific documents and communicate progress from evidence, not invented results |
| Scientific author | Maintain modular LaTeX source, bibliography and clear mathematical explanations |
| Presenter / teacher | Reuse reproducible figures, adapt scientific narrative and generate legible audience-specific slides |
| Reviewer / PI | Trace central claims to evidence, inspect source and rendered artifacts, review limitations and approve publication |
| Maintainer | Release, test, version and migrate templates and build tools without requiring an agent runtime |

## Goals and non-goals

Goals: a coherent standalone scientific document infrastructure; reproducible and versioned builds; semantic notation and consistent presentation design; evidence linkage and reviewable provenance; readable scientific writing and audience-specific communication; non-destructive migration from LaTexProjects. Support external/controlled data references rather than forced duplication. Use ANDES for optional scientific reasoning, writing, review and coaching.

Non-goals: a WYSIWYG editor or mandatory web platform; a repository of every lab manuscript; automatic authorship, publication or journal submission; a guarantee of Nature acceptance; unreviewed publisher class redistribution; replacing mathematical, statistical or scientific review with compilation; requiring ANDES, ECx, a specific AI provider, host-local cache or hidden environment dependency. Do not force universal document structure on all journals.

## Primary workflows

1. **Initialize and pin:** choose document type and template version; scaffold in the research project's authorized location without overwriting existing work; establish reviewed toolchain and evidence references.
2. **Develop a living manuscript:** context, question and theory; assumptions and planned methods; preliminary results and failures; verified evidence; discussion and limitations; journal adaptation. Keep unexecuted plans and hypotheses visibly distinct from results.
3. **Produce figures:** explicit generation from versioned source code/data and parameters; record units, conditions, uncertainty, dependencies and license; use clear labels, semantic references and accessible visual encodings.
4. **Create presentations:** choose audience, objective and duration; build a narrative from shared evidence (not manuscript-to-bullets conversion); one principal claim per frame, readable figures, backup detail and handout variant where appropriate.
5. **Verify and release:** pin environment; build; inspect logs and every rendered page; resolve citation/reference issues; independently assess claims, mathematics, statistics, reproducibility, visual quality and permissions; obtain accountable human acceptance.

## Document and presentation profiles

Canonical lab documents: research concept, technical note, research article, methods paper, internal progress report, review, reproduction report and research proposal. Use the default internal article narrative (introduction, mathematical concepts and mental model, results, reproducibility methods, discussion, conclusions) where appropriate. Nature-inspired guidance narrows from context to gap and supported central contribution, then explains implications with precision; adapt to venue requirements without changing evidence. No affiliation with or endorsement by Nature is implied.

Presentation profiles: lab meeting (previous milestone, new insight, evidence, failures, decisions, next step), research seminar (motivation/theory/results), conference (central supported contribution), teaching (formalism and intuition), defence (rationale/methods/limitations), grant pitch (opportunity/feasibility/impact), technical demonstration (architecture and observed behavior). Default to the reviewed shared 16:9 Beamer style; allow target venue/accessibility requirements to override it. Provide printable handouts and optional backup frames.

Every equation is followed by vertical definitions of symbols in the order of first appearance left to right, top to bottom across multiline equations. Explain operators, domains, codomains, indices, parameters/state, units, assumptions and meaningful checks where appropriate. Use diagrams and quantitative graphs only when they aid understanding. Theoretical illustrations and synthetic examples are labelled explicitly. Comparisons use like-for-like units, splits, baselines, denominators, protocols and evidence types; mark missing or unmatched evaluations instead of claiming causal superiority.

## Initial scope and success criteria

N1.1 is documentation/extraction inventory only. The first independently useful Neruda slice (N1.5) will require N1.2 verified compatibility and subsequent scaffold/build/CI work. Integrated authoring/review (N2) depends on A3.1 and N2.1 versioned evidence interfaces. "v1" denotes staged product scope, not a promised version tag.

| Scope | Measurable acceptance evidence |
|---|---|
| Standalone article and slides | Clean supported environment builds both synthetic examples without ANDES or ECx; compiler/bib versions, inputs, commands, logs, pages and output checksums recorded |
| Safe scaffolding | Valid new project works; unsafe names/path traversal/existing targets are refused without modifying prior work; no hidden local caches |
| Reproducible figures | Versioned generating code, input identity, parameters/environment and stable consumed figure; explicit generation step before compile |
| Document review | Citation/label/input checks resolve, all rendered pages inspected, meaningful warnings resolved or explained; no placeholder claim presented as real evidence |
| Shared evidence (N2) | Common evidence IDs connect an illustrative result to data, script, figure, manuscript and presentation; missing evidence is explicitly marked; no dependency on ANDES internals |
| Research use | Human can rebuild, explain provenance, review central claims and adapt to a target audience/venue; limitations and unsupported platforms visible |
| Release and rollback | Human approves exact immutable candidate, documented compatibility and upgrade/rollback preserve project sources |

Future variants, publisher adapters, additional language bindings and advanced visual/reproducibility checks require demonstrated need. Establish actual platform/toolchain support, licensing and usability evidence before release; no guaranteed byte-identical PDFs without a justified test and appropriate identity policy.

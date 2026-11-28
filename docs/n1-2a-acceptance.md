# N1.2a native compatibility review

**Engineering assessment:** ready for independent build review and a maintainer
decision on this Apple Silicon configuration. Issue #2 remains open. The
maintainer's native-first roadmap decision authorizes the scope of this review.

[PR #11](https://github.com/DRAGGON-Lab/Neruda/pull/11) was already merged when
this review started. Its reviewed head was
`e0b5fb4d062d35bbeb0c863cbb2cac27f28ffe15`. The follow-up starts from merge
`1f2226c9d786a328dc3dc087ca38af1636b08c26`, whose tree matches that head. The
targeted native verification below ran from clean implementation revision
`ea5932453740e91e3327953672dce229edb306d0`. The subsequent handoff adds review
records and evidence. Review both the implementation and the handoff at the
current follow-up PR head.

## Verified prior evidence

Native macOS 27.2.1 arm64 uses the reviewed MacTeX / TeX Live 2026 installation
with LuaHBTeX 1.24.0, latexmk 4.88, Biber 2.21 and biblatex 3.21. The installed
dependency inventory contains 3,098 locked files. The [original report](n1-2-compatibility.md)
records actual fixture, driver, harness and source identities.

| Check | Result from committed evidence |
|---|---|
| Artifact integrity | All 104 entries in the November 28 native export manifest matched SHA-256. Four PDFs per profile matched both their receipts and the profile's expected checksum. |
| Article, presentation and handout | All 12 receipts recorded compiler and build exit 0 across cold, sealed warm, OS-network-denied warm and OS-network-denied empty caches. The HTTPS control and network-denial probes met their expected exits. |
| Bibliography, fonts and shell escape | All 12 Biber logs reported version 2.21 and wrote bibliography output. TeX logs identify biblatex 3.21. Receipts record no output-check errors, disabled shell escape and consumed installed resource and font hashes matching the lock. |
| Missing dependency | The native matrix records the expected refusal, exit 2. |
| Visual review | Prior inspection covered 13 reference pages (2 article, 6 presentation, 5 handout). The committed comparison records all 52 matrix raster pages and both standalone pages matching the inspected references. |
| Standalone | The copied article built outside the checkout under OS network denial with its own sources, driver, lock and selected native Biber. It used the explicitly provisioned TeX Live tree. |
| Prior regressions | The historical 59-test Ubuntu result is recorded in [run 46088531399](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46088531399). That job's provisioning phase failed before Linux compilation. |

The [native evidence](../experiments/n1_2/evidence/texlive-arm64-20261128/)
preserves those receipts, logs, PDF hashes and visual comparisons. Cold tests
start with empty writable caches and a complete installed distribution. The OS
network boundary is part of the offline experiment. Daily builds isolate the
tool environment and caches. The driver does not restrict filesystem reads.

## Follow-up checks on Apple Silicon

Both specified unittest suites passed locally on Python 3.9.6 (19 driver and
45 experiment tests, 64 total). YAML parsing confirmed pull requests run both
regression suites and the two provisioning experiments are dispatch-only.

From the repository root, the [documented preflight and article build](latex-stack.md#daily-command)
ran with `NERUDA_TEX_ROOT=/usr/local/texlive/2026` and the explicitly pinned
`.tools/texlive-provisioning-20261127/arm64/biber`. Preflight exited 0 for
both the project-local binary and its durable copy in `Neruda_artifacts`.
An absent override preflight exited 2 and named the expected executable path.
The fresh article build exited 0, recorded 221 consumed installed resources, and
produced the same two rendered pages as the prior inspected references. Both
pages were inspected again. The PDF
SHA-256 is `2eb4ec82700f8b9546884cca4bdb593d721ebee5b6836051a85fa155e83a8672`.
Logs, PDF, receipts and comparison hashes are in the
[targeted evidence](../experiments/n1_2/evidence/texlive-arm64-n1-2a-review/).
The full native matrix and standalone experiment use the prior evidence.

## Automated PR #11 findings

The archived threads remain linked to their original review. These fixes and
regressions are in the follow-up:

| Finding | Disposition |
|---|---|
| [Executable launch failures](https://github.com/DRAGGON-Lab/Neruda/pull/11#discussion_r4721474273) | The runner already had an outer `OSError` path. The follow-up adds the tool and probe to the message and tests an actual executable-format failure. Exit 2 preserves a diagnostic receipt with compilation marked `not_run`. |
| [Private filenames in receipts](https://github.com/DRAGGON-Lab/Neruda/pull/11#discussion_r4721474281) | Both public exporters now record a clean, dirty or unknown state without the porcelain listing. Tests cover redacted exports and preservation of the raw input receipt. |
| [Evidence exports under operational caches](https://github.com/DRAGGON-Lab/Neruda/pull/11#discussion_r4721474292) | Both historical cache roots and their descendants are refused before output. A regression test covers four cache-path refusal cases. |

The native driver now distinguishes a missing pinned file from a checksum
mismatch, names a missing Biber override and reports exit 0 in successful
preflight JSON. The README and agent guides point to the actual CLI, explicit
dependency paths and separate article, presentation and handout entry points.

## Remaining decisions

- Review the trusted MacTeX installer verification and the separate arm64 Biber
  derivative. The installed universal source and the derivative matched their
  pinned hashes again during this review. `codesign --verify` again rejected
  the derivative's signature. Its successful execution and pinned hash support
  this exact local candidate. A different Mac may enforce a policy that rejects
  it. Review the derivation and rollback implications before accepting this
  provisioning choice. [Provisioning record](mactex-provisioning.md)
- Independently review the native logs, PDFs, agent startup instructions and exact
  follow-up revision. Record the maintainer's N1.2a decision before starting
  N1.3. Native verification currently relies on the provisioned lab Mac.
- N1.3 has a scoped acceptance contract and still needs source and branding
  clearance for reused assets plus separate implementation authorization.
  [N1.3 issue](https://github.com/DRAGGON-Lab/Neruda/issues/5)
- Linux authenticated acquisition, Linux and Intel Mac validation, portable
  provisioning and cross-platform release validation are deferred. Editor GUI
  checks and broader document support remain outside this native CLI review.
  [N1.2b issue](https://github.com/DRAGGON-Lab/Neruda/issues/12)
- ANDES architecture, local design records and live issue links were inspected.
  ANDES issue #43 still depends on the same Neruda N1.5 issue. Its dependency
  remains valid. The external planning workspace's original Implementation Plan
  v0.1 and BACKLOG.json may need the Neruda amendment mirrored there by their
  owner. The repository design baseline and live N1 epic record the amendment.

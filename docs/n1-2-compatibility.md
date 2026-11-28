# N1.2 compatibility report

## New candidate: TeX Live / LuaLaTeX

Native Apple Silicon validation **passes locally; cross-platform acceptance is
pending**. The maintainer installed the verified MacTeX 2026 package and approved
separate native Biber extraction. The observed unit is LuaHBTeX 1.24.0, latexmk
4.88, Biber 2.21 and biblatex 3.21. See [ADR-003](decisions/ADR-003.md),
[provisioning](mactex-provisioning.md), and [daily commands](latex-stack.md).

| Platform | New candidate status |
|---|---|
| macOS arm64, macOS 27.2.1 | local compatibility passes; independent acceptance pending |
| macOS x86_64 | untested |
| Linux x86_64 | prepared March 22 snapshot validation; execution approved, results pending |

The final local matrix uses the exact driver digest recorded in each receipt and
the harness digest in its summary. It ran against HEAD
`6e3624da58f31eb1904cfadd858118ebbf2a907e` with explicitly recorded dirty state;
this is not an immutable release or a claim that uncommitted code is reviewed.

| Scenario | Article | Presentation | Handout |
|---|---|---|---|
| Cold writable caches; local distribution installed | pass | pass | pass |
| Warm sealed compiler/font caches; fresh outputs | pass | pass | pass |
| OS-network-denied warm caches | pass | pass | pass |
| OS-network-denied empty writable caches | pass | pass | pass |
| Page count | 2 | 6 | 5 |

A successful HTTPS control probe followed by a failing probe under macOS
`sandbox-exec` `(deny network*)` validates the OS network boundary. No compiler
`--only-cached` flag is involved. Missing installed dependencies refuse with exit
2 before compilation. All final TeX/Biber checks pass, with actual Biber processing
and resolved references; consumed package/font hashes match the lock. Shell escape
remains disabled. Environment isolation is not a filesystem-access sandbox.

All 13 reference pages were inspected at 1500-pixel width using macOS PDFKit:
ordered equation definitions, Unicode/unit glyphs, table values, references,
bibliography, clipping, overlap and handout overlay collapse. No clipping or
overlap was observed. The article's bibliography occupies page 2; hyperlink boxes
and default Beamer navigation remain unchanged fixture styling. All 52 final
matrix raster pages match the inspected references, including the November 28
rerun with literal filename handling and pruned generated-source directories. The standalone article adds
2 matching pages, for 54 final comparison pages. Independent human/build review
remains pending; this agent inspection does not substitute for it.

PDF bytes were identical across the four local scenarios for each fixture:

| Fixture | SHA-256 |
|---|---|
| Article | `46c7a5650ce7b35c382677be04c3776b5c8b51f77a32608f6dbe893e34ec190b` |
| Presentation | `967f0adf9cea988dfbc29e423d1b009ebb8b40daef1344af20966ffac5987ebd` |
| Handout | `ef397b582c25c734fd95f1b01219cb29252b92f644b009bb75c54e7fe8549432` |

This demonstrates repeatability for these inputs on this host, not cross-platform
byte identity. Previous command-line revisions have different PDF trailer IDs but
identical rendered pages; their artifacts and hashes remain preserved. A copied article project outside the Neruda checkout also passed
with local tools under OS network denial, without editor/AI dependencies.

Sanitized [latest receipts, logs and PDFs](../experiments/n1_2/evidence/texlive-arm64-20261128/)
include the [case summary](../experiments/n1_2/evidence/texlive-arm64-20261128/summary.json),
[visual comparison](../experiments/n1_2/evidence/texlive-arm64-20261128/visual-comparison.json),
and link to [preserved universal-Biber/font-cache failures](../experiments/n1_2/evidence/texlive-arm64-20261127/diagnostics/). Manifest hashes distinguish
raw and sanitized exports. Operational caches/seals remain local and cannot be
reconstructed or authorized from sanitized receipts. A durable copy and verified
installer/native executable are in the maintainer-selected
`Neruda_artifacts/texlive-2026-native-20261127` store.

Regression verification: 16 driver tests plus 41 N1.2 tests pass; YAML syntax and handwritten-source whitespace checks
pass. Literal compiler logs retain their original whitespace; the unrestricted
whitespace scan flags those machine-generated data files. Generated `build/` trees are now excluded from historical fixture hashing
and copying, preventing stale PDFs and caches from contaminating Tectonic tests.
The earlier interrupted test run is not reported as passing; the corrected complete
suite passed. Historical Tectonic evidence remains intact. HTTP 429 indicates a
provisioning failure, not Tectonic/Biber incompatibility.

The March 1 ISO is a different snapshot (including geometry 5.9 versus 6.0 and
latexmk 4.87 versus 4.88). The TUG-documented March 22 archive matches all 4,478
installed packages with shared runtime files. Signed-metadata authentication must
run in CI before any archive code is executed. The maintainer approved publishing
and running the [prepared Ubuntu procedure](texlive-linux-provisioning.md).
At this report update execution is pending, so no new CI success or evidence link
is asserted. Native Intel/Linux execution, editor GUI validation, independent review
and maintainer acceptance remain open.
N1.2 remains **not ready for acceptance**.

## Historical Tectonic compatibility evidence

Status: **engineering work through `fc00ab6` approved; compatibility acceptance pending**. Observations: 2026-11-27.
Base Neruda revision: `7bdf17ce40577a15877ac8fe0d79ee9a9b4f985c`.
Fixtures and runner were introduced for review in PR #11 at
`025ce44c61555c2186525e428820cd83d8934718`; no release identity is asserted.
Subsequent remediation receipts record HEAD, dirty state and exact input/harness
hashes; a dirty run is not represented as an immutable committed revision.
Upstream reference: `906a18074080635271b87cb29a063498ea75b3b0`.
LaTexProjects and its dirty working tree were not modified.

## Provisioning observations

The user explicitly approved isolated Tectonic 0.17.0, Biber 2.17, and pinned
PyMuPDF 1.26.6 provisioning in `.tools/n1_2`. No global installation was made.

Official Tectonic release API:
`https://api.github.com/repos/tectonic-typesetting/tectonic/releases/tags/tectonic%400.17.0`.

| Archive | Official SHA-256 |
|---|---|
| tectonic-0.17.0-x86_64-apple-darwin.tar.gz | `7c90ef5b6ddb1eb1937e4337add5237b79338e4b9676459fa91187d24d6cdf80` |
| tectonic-0.17.0-x86_64-unknown-linux-gnu.tar.gz | `1a715688baf591e650c8aeb160ae934e181685eecbb38b317de30b269ac5d606` |

The Mac archive was downloaded from the official GitHub release and its measured
digest matched. `tectonic --version` returned `Tectonic 0.17.0`. Archive listing
contained only `tectonic` before extraction. Linux metadata was inspected; the
Linux archive was not downloaded or executed.

Biber was downloaded over HTTPS from
`https://downloads.sourceforge.net/project/biblatex-biber/biblatex-biber/2.17/binaries/MacOS/biber-darwin_x86_64.tar.gz`.
Archive listing contained only `biber`. Measured SHA-256:
`aa72ccdd01d59367b919d517f7a116e5dc40848abc1909cd812b485f791df7f4`.
This is a locally measured identity, **not an independently verified publisher
digest**. SourceForge metadata endpoints returned HTTP 400/404. Initial version
probes were slow but completed with `biber version: 2.17`. Bibliography processing
compatibility remains untested because the bundle could not be fetched.

The first PDF-inspector install failed: Python 3.9.13 does not satisfy PyMuPDF
1.26.6's Python >=3.10 requirement. An existing Python 3.13.14 interpreter was
then used to create `.tools/n1_2/inspection-py313`; `uv pip install --python
.tools/n1_2/inspection-py313/bin/python 'PyMuPDF==1.26.6'` succeeded. The unused
Python 3.9 environment is retained; no cache repair or version change occurred.

## Initial evidence and limits (historical)

| Check | Status | Method / result |
|---|---|---|
| Runner refusal paths | pass | `python3 -m unittest discover -s experiments/n1_2 -p 'test_*.py' -v`: six tests passed |
| Whitespace | pass | `git diff --check` (tracked changes); added files also require review |
| Native environment | observed | Darwin x86_64, macOS 15.7.9; compiler/bibliography absent from PATH initially |
| Compiler identity | pass | Mac archive SHA-256 and binary `--version`, above |
| Biber compatibility | partial | Exact version observed; bibliography processing not reached |
| Article / slides / handout | fail | Cold builds exited 1 fetching pinned bundle index: HTTP 429; no PDFs |
| Cold / warm / offline | partial | Cold attempted; warm/offline remain not_run without a successful cold build |
| Bundle / biblatex / fonts | not_run | Expected bundle and biblatex pairing not yet observed in a build |
| Semantic and rendered-page review | not_run | No PDFs available |
| Linux x86_64 | untested | No clean Linux runner execution |
| Independent review / human acceptance | partial | Engineering reviewer found missing-output and foreign-cache acceptance flaws; corrected with regression tests. Human compatibility acceptance not_run; ADR-002 proposed |

Cold attempt receipts and console logs are retained locally at
`/private/tmp/neruda-n1-2-bounded-20261127/cold/` and
`/private/tmp/neruda-n1-2-retry-20261127/cold/`. These temporary directories are
not durable repository artifacts. Both reached exact-version preflight, then
failed with HTTP 429 for
`https://data1.fullyjustified.net/tlextras-2022.0r0.tar.index.gz`.
Between attempts, a HEAD request returned HTTP 200 with no Retry-After header;
the following actual compiler GET still returned 429. No bundle URL, tool
version or cache fallback was changed. Original receipts predate final runner
review fixes and do not validate those fixes with real builds.

Next action: retry with the unchanged pinned unit when the bundle service allows
the download, using a new work root. Then run the cache matrix, inspect every
page and repeat on a clean Linux runner. Retain all failed attempts. N1.3 and
downstream tasks remain blocked on accepted compatibility.

## PR #11 remediation — native Apple Silicon

The remediation host reports `Darwin arm64`. Both historical temporary receipt
paths above and `.tools/n1_2` were absent in this checkout. Their observations
remain historical narrative; original receipts cannot be reconstructed here.

The runner now constructs a minimal environment for version probes and builds:
private HOME/XDG/TeX/PAR/temp directories, deterministic locale/time, no inherited
Perl/font/loader/search overrides, and a private PATH containing only the Biber
shim. The shim passes `--noconf`, preventing configuration discovery via host
`kpsewhich`. Fixtures request Latin Modern font files rather than family names.
This is environment isolation, not an OS filesystem or network sandbox. Actual
consumed font identities and absence of native font fallback remain unverified
until successful compilation and inspection.

With separately approved downloads/extraction, measured archives were:

| Archive | SHA-256 / verification |
|---|---|
| Tectonic 0.17.0 aarch64-apple-darwin | `a3f1cac7c5678f01661a92212f58480ae3b0634115d880dbc59e2953ded45667`; matches official release metadata |
| Biber 2.17 darwin_universal | `182e1efa074d8a2a23a8893f2a22440d4e463cce55e4ed02076ac4c0ee0614b2`; measured only; publisher JSON endpoint returned 404 |

`file` identifies arm64 Tectonic and arm64/x86_64 Biber slices. `otool -L`
shows Apple system libraries/frameworks in their load commands; this does not
prove the contents of PAR's subsequently unpacked libraries.

Native command:
`python3 experiments/n1_2/run.py --tool-dir .tools/n1_2/arm64/bin --work-root experiments/n1_2/artifacts --case cold`.
Tectonic's exact version probe passed. Biber's universal loader failed before
its version output, calling `/usr/bin/lipo -extract_family`; this host's `lipo`
help lists `-extract` and `-thin`, but not `-extract_family`. Diagnostic: cannot
find the extracted thin binary, errno 2. Exit 2, compilation **not_run**.
No system tool repair, binary thinning or Rosetta fallback was attempted.

Sanitized native preflight receipts are tracked in
[`experiments/n1_2/evidence`](../experiments/n1_2/evidence/), with raw/export
checksums. Existing exports are never overwritten. Test-generated evidence is
confined to temporary test directories and is not compiler evidence.
The expanded suite has 13 passing tests, covering successful output handling,
timeouts, cold-receipt acceptance/refusal, environment poisoning and export
redaction. Real successful builds, warm/offline compilation, bibliography/font
identity, PDF inspection and independent review remain **not_run**. Intel macOS
results above are historical; Linux remains untested.

### Bounded replacement comparison

Retain Tectonic 0.17.0 for both candidates. The historical candidate remains
`tlextras-2022.0r0` with Biber 2.17/biblatex 3.17: historical HTTP 429 plus the
new native universal-loader blocker prevent acceptance.

The alternative is the upstream
[texlive2024-0312 recipe at Tectonic 0.17.0](https://github.com/tectonic-typesetting/tectonic/blob/tectonic%400.17.0/bundles/bundles/texlive2024-0312/bundle.toml).
Its declared bundle identity is
`8fae742a1d9453fc3abfe7c6971363696f611ade1266c17788ccb5c18ffd1312`;
its input is the historical `texlive-20240312-texmf.tar` with declared hash
`87f7f5fd9618689cd9ae436ad37cefe43fabf1f2f457ac3860ec2aa854578d20`.
These are recipe declarations, not locally verified bundle/archive measurements.
Unlike the historical hosted bundle, this candidate requires verified bundle
construction and its prerequisites; no independently verified hosted artifact
was established. Do not substitute a third-party mirror or download a latest
Biber independently of the bundled biblatex version. Inspect the resulting
biblatex version, select its publisher-documented matching Biber and verify its
native executable before the full cache/build/render matrix. Bundle creation
and any additional installation require exact reviewed commands and approval.

Recommendation: keep ADR-002 proposed and production pins unchanged. The 2024
recipe is a bounded investigation candidate, not a validated replacement.
Apple Silicon is a required validation target with a recorded blocker, not a
supported platform. N1.2 and downstream acceptance remain incomplete.

## Native arm64 manual-thinning experiment

Follow-up at source revision `767ade93e118cf5a8d8a77767c6ec45027fef7a7`,
2026-11-27. User authorized manual thinning while preserving originals and pins.
Command Line Tools were already installed; no installation or repair occurred.
The selected `/usr/bin/lipo` advertises `-thin`; its SHA-256 is
`ed6f5284033aa2aae6a58427c25ba3ab119947b40365627b24e5d51a4b70a1cd`.

`/usr/bin/lipo <ORIGINAL_TOOLS>/biber -thin arm64 -output <THIN_TOOLS>/biber`
exited 0 in a fresh `.tools/n1_2/arm64-thin.a3201eaf` directory. Python
`Path.chmod(0o755)` made the result executable and `shutil.copy2` copied the
unchanged Tectonic executable. `file` and `lipo -archs` report arm64 only.

| Executable | SHA-256 |
|---|---|
| Original universal Biber | `d894bfb75f2df1935fbcf452e8a79fd80de5c859ade4842d8e0681306b509681` |
| Derived arm64 Biber | `ec2e851a60a36ff9aa756120c728ffec7a8727e4a1a6094e504b0863f2bb7bd4` |
| Unchanged Tectonic | `b52b5a730e2b0b33087304f7720f649603953f270a6b1c88bb031e1ae01f7f9c` |

The derived bytes match the arm64 slice independently read from the universal
binary. Original executable hashes remain unchanged. Archive identities remain
those above; Biber's archive digest is still locally measured only. Derived
`codesign --verify --strict` returned 1 (invalid signature). The original universal executable also fails this signature check, so the failure
is not attributed to thinning. No re-signing,
quarantine removal or execution-policy change was made. Isolated execution still
returned exact `biber version: 2.17` and `Tectonic 0.17.0`, both exit 0.
This demonstrates loader bypass and version startup, not bibliography semantics.

The runner used `--tool-dir .tools/n1_2/arm64-thin.a3201eaf` and fresh work roots:

| Case | Work root under `.tools/n1_2/` | Result |
|---|---|---|
| Sandboxed cold | `thin-work.1120ad8b` | exit 1; bundle-index request could not be sent |
| Network-enabled cold | `thin-network.9ee75246` | exit 1; HTTP 429 for article and slides |
| Empty-cache offline | `thin-work.1120ad8b` | exit 1; expected failure without cached bundle |

Sanitized receipts, console logs and provisioning identity/commands are retained
under the tracked evidence directory. Raw work roots remain ignored and intact.
Warm/offline reuse and the successful poisoned-environment comparison are
not_run because neither cold run compiled. No PDFs were produced; bibliography,
consumed fonts/bundle, visual inspection and independent review remain not_run.
The 13 runner regression tests and whitespace check pass.

Manual thinning is therefore a **candidate provisioning strategy** with a passing
isolated version check. It does not resolve publisher checksum corroboration,
signature verification or the bundle service failure. No compiler/bibliography/
bundle pins changed, and N1.2 compatibility acceptance remains pending.

## Source provenance and cache-integrity corrections

Follow-up to `d176b4cc5d0fc31270189e9bcb9f3bdf1c9e5673` (2026-11-27).
Git stdout and stderr are captured separately for revision and dirty state.
Only exit-zero, full 40-character hexadecimal commit output is accepted as
`source_revision`; warnings and errors are preserved under `git_diagnostics`.
Unavailable metadata is null and prevents compilation (exit 2, not_run receipt).
The same metadata capture is used for build and preflight-failure receipts.

Five historical receipts contain contaminated revision fields: the three
`preflight-20261127T145018Z-fb7df49b`, `preflight-20261127T145109Z-9ef18396`,
`preflight-20261127T145146Z-e69ecef2` receipts, plus
`20261127T152659Z-arm64-cold-20aca5dd` and
`20261127T152728Z-arm64-offline-empty-6f2080ea`. They remain unchanged as
historical evidence; their revision strings must not be treated as valid SHAs.

Warm/offline cases now compare every current regular cache file and SHA-256
against the successful cold receipt's inventory before creating the case or
compiling. Added, removed or modified files, links, special/unreadable entries
and missing/malformed inventories are refusals. The baseline is always the
successful cold inventory: even a recorded warm build changing the cache
requires a fresh cold experiment before further reuse. The runner never repairs
or renews the cache baseline. Post-build inventory errors retain a failed receipt.

Verification: 18 unittest tests pass, including separate Git diagnostics and
metadata failure paths, populated/empty cache reuse, cache mutations and final
inventory failure. `git diff --check` passes. A fresh offline-empty run under
`.tools/n1_2/metadata-check.024d8404`, using the existing thinned tools, exits 1
as expected without a cached bundle. Its new exported receipt has a validated
commit SHA and separately recorded Git warnings; no bundle download was needed.
The run records its dirty state and input/harness hashes. No PDFs were produced.

These corrections do not complete N1.2: Linux, successful cold/warm/offline builds,
actual biblatex/font/bundle identity, resolved references and bibliography,
rendered-page inspection, independent review and packaging acceptance remain
pending. ADR-002 remains proposed. No tool versions or provisioning changed.

## Maintainer approval and continuation — 2026-11-27

The user approved the engineering work through
`fc00ab60105a4cb51454a70bd75ffbafa560be31` and authorized continuation of the
remaining N1.2 investigation. The scoped decision is recorded in ADR-002.
Compatibility/platform acceptance remains pending the outstanding actual builds,
cache experiments, bibliography/font identity and rendered-page review.

### Continuation results after approval

A fresh network-enabled native cold run used the unchanged thinned tools:
`python3 experiments/n1_2/run.py --tool-dir .tools/n1_2/arm64-thin.a3201eaf --work-root .tools/n1_2/continued-cold.778a8b16 --case cold`.
Both article and slides again returned exit 1 fetching the pinned bundle index
with HTTP 429. The run's source revision is `fc00ab6`; dirty state records the
approval documentation additions. No PDFs were produced. All prior artifacts
and the new raw work root remain intact; sanitized receipts/logs are tracked.
No warm/offline reuse was attempted against this failed cold receipt.

| Current acceptance area | Status after continuation |
|---|---|
| Completed engineering corrections | Human approval recorded through `fc00ab6`; 18 regression tests pass |
| Native macOS arm64 compiler/Biber startup | Exact Tectonic 0.17.0 and Biber 2.17 previously observed; tools unchanged |
| Native macOS arm64 cold compilation | fail: unchanged bundle-index HTTP 429 |
| Cache integrity/refusal behavior | Regression-tested; real successful cold/warm/offline matrix blocked |
| Empty-cache offline behavior | Expected failure demonstrated in preserved prior evidence |
| Linux x86_64 | Actual Actions attempts recorded below: Ubuntu 22.04 cannot start compiler; Ubuntu 24.04 passes tool startup but compilation fails HTTP 429 |
| Intel macOS | Historical attempts only; no fresh validated platform result |
| Actual biblatex, bibliography, consumed fonts/bundle | not_run: blocked before compilation |
| PDF identities and all-page visual inspection | not_run: no PDFs |
| Archive verification | Tectonic archive verified; Biber publisher digest/signature limitations remain |
| Candidate compatibility unit / packaging ADR | Not accepted; ADR-002 remains proposed for these decisions |

Additional read-only upstream investigation found no alternate official 2022
bundle download in the archived bundle repository's GitHub releases. Its releases
API returned a 2021 release with listing/digest assets, not the required 2022
bundle. This does not prove that no mirror exists; no verified equivalent was
established. No bundle pin, third-party mirror or bibliography version was changed.

Next executable dependency: supply a clean Linux execution environment and/or
restore access to the pinned bundle. A replacement-bundle experiment remains a
separate candidate investigation requiring verified inputs and reviewed exact
provisioning commands; it is not silently substituted for this failed run.

### Approved Linux job preparation

The user selected GitHub Actions and explicitly approved the prepared Ubuntu
22.04 workflow, including isolated provisioning of the pinned Linux tools and
execution with Biber's uncorroborated publisher-digest limitation. ADR-002 records
the exact approval scope. `linux_ci.py` provides checksum/member/ELF checks,
provisioning receipts, conditional cache-matrix execution and reviewed artifact
selection. No production installer or system package installation is introduced.
The existing 18 regressions plus three archive-verification tests pass locally.
Pinned action tag identities were verified through the official repositories:
checkout v4.2.2 `11bd71901bbe5b1630ceea73d27597364c9af683`, upload-artifact
v4.6.2 `ea165f8d65b6e75b540449e92b4886f43607fa02`.
Actual Linux results must be recorded from the Actions run; workflow configuration
and local tests alone do not establish Linux execution or compatibility.

### First actual Linux result and approved follow-up

[Actions run 46030742564](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46030742564)
checked out `8e9e09aa0d89ab2231def87a998ad6688efb4462` on Ubuntu 22.04.5,
image `ubuntu22 / 20261122.372.1`, Python 3.10.12. All 21 tests passed.
Both archive digests matched the reviewed values and extraction succeeded.
Tectonic then failed before version output: the binary requires GLIBC_2.36,
GLIBC_2.38 and GLIBC_2.39 symbols missing from this runner. Cold and offline-empty
were not_run (runner exit 2); warm/offline were skipped. This is an observed
binary/environment incompatibility, not a compiler build failure or PDF result.

The uploaded artifact (ID `15214147468`, ZIP SHA-256
`51742756c5592170e7943dfe80d29b9185694b960b83ce96e3552f2a293af9c4`)
was retrieved, checksum-verified and preserved under
`experiments/n1_2/evidence/linux-run-46030742564`. Its embedded export checksums
were verified. No PDFs were present. The job's failure was retained rather than
converted into a successful compatibility result.

The user explicitly approved a fresh Ubuntu 24.04 runner with the same archives
and checksums. This changes the environment candidate, not the compiler or
bibliography pins. No system-library repair or package install is performed.
The follow-up receipt records the runner image identity; actual results follow.

### Ubuntu 24.04 execution result

[Actions run 46031054171](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46031054171)
checked out `984e62dfd5b6aa3d52f07199920e57f8a70f2a14` on image
`ubuntu24 / 20261122.23.1`, Python 3.12.3. All 21 tests passed. Both reviewed
archive digests matched, and isolated probes returned exact `Tectonic 0.17.0`
and `biber version: 2.17`. The environment change resolved the observed compiler
startup incompatibility without changing binaries or installing system packages.

The cold article and slide builds exited 1 fetching the unchanged bundle index:
HTTP 429. The job therefore skipped warm/offline reuse. Empty-cache offline also
exited 1, with an `only cached` notice followed by a bundle-index HTTP 429
message; this is an empty-cache failure, **not proof of blocked network access**.
The engine flag remains distinct from an OS network sandbox. No PDFs were
produced, so bibliography resolution, actual biblatex/font identity, consumed
bundle identity and all-page review remain not_run. Neither native Mac nor Linux
is yet a fully validated supported platform.

Artifact ID `15213164503`, ZIP SHA-256
`cf085dc0b312a6d8e0ec8c831ad1b523e7a5666a676bce5458ef522ebf50d910`,
was downloaded and verified. Sanitized provisioning receipts, build logs, case
summary and export manifests are committed under
`experiments/n1_2/evidence/linux-run-46031054171`. All retained manifest checksums
and host-path checks pass. The Actions job remains failed, accurately reflecting
the blocked compatibility matrix. Its image/provisioning approval remains scoped
to investigation, not compatibility or release acceptance.

The remaining critical dependency is now demonstrated on two execution hosts:
the pinned bundle service must become available, or a separately reviewed,
verified replacement-bundle experiment must be authorized. Repeated downloads,
cache repair, library replacement and tool-version substitution were not used
to manufacture a passing build. N1.3 remains gated on N1.2 acceptance.

## Reliable local-bundle work: implementation and current gate

The two additional artifacts from run `46031329144` were independently downloaded
and checked against GitHub's reported ZIP SHA-256 values:

| Artifact | ZIP SHA-256 | Observed result |
|---|---|---|
| 15213808737, attempt 1 | `f510a71e2eb1addb5dd744f6876860d8c82f8b64a9801544763ab6a08f41a59b` | Article failed fetching amstext.sty; presentation and handout compiled |
| 15214503126, attempt 2 | `663ac25b56fa7acd586ce50e06fd792ea91ed7042de6efc1a1cabab02ec7de6f` | Both projects failed fetching bundle index |

They are retained unchanged under `evidence/artifact-15213808737` and
`evidence/artifact-15214503126`. Export-manifest and PDF checksums were verified.
The positive logs identify biblatex 3.17 and Biber 2.17, including successful
bibliography output for slides and handout. Their PDF hashes are
`d2ee9d7731fce7d36db20f2f79b6b469fc816631bbfff62b996ed5c10f944e97`
and `c5739a7d75ec7d8b320902cd9af924285e7a700a9218b0742644466a1b307eb5`.
Logs report six presentation and five handout pages; independent rendered-page
inspection remains pending. Warnings include unicode-math command replacement,
hyperref PDF-string handling and nested color changes; successful exit alone
is not visual acceptance. HTTP 429 is not evidence of bibliography incompatibility.

Tectonic 0.17.0 source at `8c0126a9653239a2e6e0a5274af9b8510f643030`
confirms local ZIP, TTB and directory backends. Its indexed-tar backend is
HTTP-range based; the build command ignores its --bundle option. The runner now
binds staged manifests to a verified ZIP instead. Streaming SHA-256 and ZIP CRC,
member and internal-fingerprint checks happen before compiler invocation.
Missing/invalid resources produce preserved preflight diagnostics and exit 2.
A source-lock-gated converter prepares byte-preserving ZIP candidates without
publishing or endorsing them. No real usable bundle lock exists yet.

Twenty-six behavioral tests pass locally. They cover the existing integrity and
source-provenance behavior plus missing/corrupt/mismatched local resources,
manifest binding without remote fallback, successful synthetic empty-cache local
selection and verified-source packaging. These synthetic tests do not demonstrate
real compilation. The CI regression job is independent of provisioning. The
provisioning job now reports its primary blocker directly in the job summary;
full matrix results and compiler errors are summarized when compilation runs.

Current implementation remains gated: acquire the complete original bundle and
independently verify its archive identity before preparing a real ZIP/runtime
lock, dependency asset/cache, three-platform local-resource matrix or OS-enforced
offline checks. Full PDFs, actual consumed fonts and all-page review are still
outstanding. No new supported platform or release is declared.

If the original bundle cannot be independently verified, the replacement proposal
is a separate investigation of upstream texlive2024-0312 with Tectonic 0.17.0.
Use the upstream source recipe and declared input checksum already recorded above;
verify the actual resulting biblatex version, then request approval of its matching
Biber and exact archives before execution. Do not substitute the candidate into
the existing compatibility unit or infer package identity from the year label.

### Complete official acquisition and verification hold

The bounded acquisition completed on its first attempt from the official URL.
The archive is retained outside Git at the selected artifact store under
`quarantine/d79dce7a8e8449a99a5030b328847905/attempt-0.tar`.
Actual size: 2,881,562,112 bytes. Locally measured archive SHA-256:
`425685e124746c15ba9bb8e0596bdaad98fce886afa347fbcf9ec0e9acd7fe79`.
Tar inspection found 134,980 regular members, no duplicate names or special
members. Embedded metadata records SVNREV 62885, GITHASH
`082081a375be008c2e049cd7cf1137314f888b18`, and the internal fingerprint
`6ffe055852f8faf66c0acbe1a7fb27f87b869a90bad1204f3bf4d9683f597c7c`.
The fingerprint agrees with the prior successful CI cache namespace, but is not
an independently published archive checksum. The embedded Git reference could
not be resolved as a commit/tree in the archived upstream bundle repository.
The user confirmed having no independent checksum reference. These observations
are not promoted into verification or an approved runtime lock. The acquisition
receipt is committed; the large archive remains quarantined and was not compiled,
converted, uploaded or published.

[CI run 46051321188](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46051321188)
checks source `d1b721460c0b4e23cfe3df97a06bc6a2b18879fa`. The independent
regression job passed all 26 tests. The Linux job also passed 26 tests, then
stopped with `Provisioning blocked: local bundle and reviewed bundle lock are
required; remote fallback is disabled`. This primary diagnostic is directly
visible in the job output and summary. The failed provisioning result is retained;
no compatibility pass is inferred from the test job's success.

Implementation status is deliberately partial at the verification gate:
local ZIP verification, source-lock-gated candidate packaging, manifest binding,
revised cache policy tests, independent regression execution, primary CI
summaries and historical evidence retention are implemented. Actual ZIP
promotion, approved lock pins, dependency-asset publication, verified CI cache
activation, all-three-platform compilation, OS-enforced network denial and
independent rendered-page inspection remain unimplemented or not_run pending
that gate. There is no claim that a new local bundle has compiled successfully.
N1.2 is **not ready for acceptance**.

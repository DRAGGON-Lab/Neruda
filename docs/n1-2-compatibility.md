# N1.2 compatibility report

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
| Linux x86_64 | not_run: no Docker/Podman/Lima/Colima/QEMU Linux runtime found locally; environment selection requested |
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

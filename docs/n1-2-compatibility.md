# N1.2 compatibility report

Status: **partial; not accepted**. Observations: 2026-11-27.
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

## Evidence and current limits

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

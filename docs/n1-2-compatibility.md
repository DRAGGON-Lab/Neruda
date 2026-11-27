# N1.2 compatibility report

Status: **partial; not accepted**. Observations: 2026-11-27.
Base Neruda revision: `7bdf17ce40577a15877ac8fe0d79ee9a9b4f985c`.
Fixtures and runner are uncommitted additions; no release identity is asserted.
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

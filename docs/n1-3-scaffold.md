# N1.3 standalone scaffolding and templates

The [N1.3 contract](https://github.com/DRAGGON-Lab/Neruda/issues/5) follows
[N1.2a acceptance](https://github.com/DRAGGON-Lab/Neruda/issues/2). The two
implementation slices branch from
`8c5b223274f119f493e48b7bc88b9786a3a2c9ac`, the merge of PR #13.
The native verification used a clean checkout at
`732c0a7239be1740d56f2f2b74533cc92022a80d`. The evidence commit adds this
record and the artifacts alongside those sources.

## Provenance

DRAGGON Lab's Neruda project authored the scaffolder, starter documents,
synthetic example and styles for N1.3. These original assets carry the
[repository's MIT license](../LICENSE). The styles use the DRAGGON Lab name
as text. The [LaTexProjects inventory](../upstream/LaTexProjects.md) informed
the project layout, semantic notation and 16:9 presentation and handout.
The implementation uses original source and copies only the existing Neruda
license, driver and native lock plus the explicit starter assets. The [LaTeX
Project documentation](https://www.latex-project.org/help/documentation/)
is cited with its URL and bibliographic metadata.

The [manifest](evidence/n1-3/manifest.json) records per-file SHA-256 hashes
for both bundles, the copied infrastructure and the exported evidence. It
also records the environment, lock and selected Biber identities, and exact
PDF and rendered-page hashes. The target directories are private on creation
and are populated from an allowlist. A failed copy removes its own entries
and reports any path that still needs attention.

## Verification on 28 November 2026

Environment was macOS 27.2.1 (26B131) on arm64 with Python 3.9.6 and the
provisioned MacTeX 2026 tree. LuaHBTeX 1.24.0, latexmk 4.88, Biber 2.21 and
biblatex 3.21 came from the accepted configuration. The two new projects
were created in a fresh parent directory with spaces outside the checkout.

| Check | Status | Evidence |
|---|---|---|
| Behavioral suites | pass | `python3 -m unittest discover -s tests -p 'test_*.py' -v` ran 29 tests. `python3 -m unittest discover -s experiments/n1_2 -p 'test_*.py' -v` ran 45 tests. Scaffold tests cover exact inventories, existing targets, symlinks, traversal, concurrent creation and interrupted copies. |
| Network boundary | pass | HTTPS control and sandbox startup exited 0. The same HTTPS request under `sandbox-exec` exited 6. [Probe results](evidence/n1-3/network-status.txt) |
| Preflight, build and output check | pass | Both copied drivers passed preflight. Fresh runs used empty writable caches. All three builds and output checks exited 0 and all recorded distribution resources and PDF-embedded fonts matched the lock. The LuaLaTeX command used `-no-shell-escape`. |
| References and bibliography | pass | Equation 1 and numeric citation [1] resolve in the PDFs. Biber processed the real documentation entry and wrote its bibliography. Final slide and handout logs record the expected `epstopdf` warning that shell escape is disabled. The examples use no EPS conversions. |
| Page inspection | pass | PDFKit rasterized all ten pages at 1500 px width. The implementation review checked heading alignment, clipping, legibility, the ordered definitions of **y**, **A**, **x**, units, numeric citations and URL rendering. Presentation pages 3 and 4 show the two overlay steps. Handout page 3 retains the complete content, with a white background on all four handout pages. |
| Independent build and visual review | not_run | The PR contains the exact source identity and artifacts for the independent reviewer. Maintainer acceptance follows that review. |

| Output | Pages | Logs and receipt |
|---|---:|---|
| [Article PDF](evidence/n1-3/article/main.pdf) | 1 | [TeX](evidence/n1-3/article/tex.log) · [Biber](evidence/n1-3/article/biber.log) · [Receipt](evidence/n1-3/article/receipt.json) |
| [Presentation PDF](evidence/n1-3/presentation/main.pdf) | 5 | [TeX](evidence/n1-3/presentation/tex.log) · [Biber](evidence/n1-3/presentation/biber.log) · [Receipt](evidence/n1-3/presentation/receipt.json) |
| [Handout PDF](evidence/n1-3/handout/handout.pdf) | 4 | [TeX](evidence/n1-3/handout/tex.log) · [Biber](evidence/n1-3/handout/biber.log) · [Receipt](evidence/n1-3/handout/receipt.json) |

The copied projects sit outside Git, so their driver receipts carry no Git
revision. The manifest ties their source hashes to the clean Neruda revision
used for scaffolding. Exported receipts and logs replace local paths with
tokens and trim trailing whitespace. PDFs retain their original bytes.

## Reproduce the native review

From Neruda on the provisioned lab Mac, use the exact build commands below.
The parent should be an existing direct path. The macOS `/tmp` path resolves
through a symlink, so the example uses `/private/tmp`.

```sh
work=$(mktemp -d '/private/tmp/neruda-review.XXXXXX')
mkdir "$work/projects with spaces"
python3 scripts/scaffold.py article model-article --parent "$work/projects with spaces"
python3 scripts/scaffold.py slides model-slides --parent "$work/projects with spaces"

export NERUDA_TEX_ROOT=/usr/local/texlive/2026
export NERUDA_BIBER="$PWD/../Neruda_artifacts/texlive-2026-native-20261127/biber-arm64"
offline() {
  /usr/bin/sandbox-exec -p '(version 1) (allow default) (deny network*)' "$@"
}
probe() {
  "$@" /usr/bin/curl --silent --show-error --max-time 10 --output /dev/null \
    https://www.latex-project.org/help/documentation/
}
probe
offline /usr/bin/true
probe offline
```

The observed exits, in order, were 0, 0, and 6. Continue with both preflights
and all three entry points under that policy.

```sh
verify() (
  cd "$work/projects with spaces/$1" || exit 1
  entry=$2
  offline /usr/bin/python3 scripts/latex.py preflight --lock tools/texlive-lock.json &&
  receipt=$(offline /usr/bin/python3 scripts/latex.py build --project . --entry "$entry" --lock tools/texlive-lock.json) &&
  offline /usr/bin/python3 scripts/latex.py check --project . --entry "$entry" --lock tools/texlive-lock.json \
    --output "$(dirname "${receipt#Build receipt: }")"
)
verify model-article src/main.tex
verify model-slides src/main.tex
verify model-slides src/handout.tex
```

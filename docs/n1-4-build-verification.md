# N1.4 native build verification

[N1.4](https://github.com/DRAGGON-Lab/Neruda/issues/6) starts from PR #14's
merge on main at `aac10eca973cfe2c11324d2e1bbb92c1310a38a7`, after
[N1.3 acceptance](https://github.com/DRAGGON-Lab/Neruda/issues/5). The
[manifest](evidence/n1-4/manifest.json) records the clean implementation
revision, fixture identities, environment, lock and executable SHA-256
values, run timestamps and output identities.

## Verification on 28 November 2026

On macOS 27.2.1 (26B131), arm64, with Python 3.9.6, the pinned toolchain
was MacTeX 2026 with LuaHBTeX 1.24.0, latexmk 4.88, Biber 2.21 and biblatex
3.21. The native lock matches the N1.3 merge byte for byte.

| Check | Status | Observation |
|---|---|---|
| Behavioral suites | pass | 40 driver/scaffold tests and 45 compatibility experiment tests. Figure tests cover a missing receipt, stale inputs and output, a consumed image without a receipt, and a declared image never consumed. |
| Network boundary | pass | The HTTPS control and sandbox startup exited 0. The HTTPS probe inside macOS network denial exited 6. |
| Figure repeat | pass | Two explicit generations yielded identical PNG and figure receipt hashes. |
| Native preflight, builds and output checks | pass | Two fresh isolated runs each for the article, presentation and handout. All used shell escape disabled. The article recorder identified the generated PNG and Biber identified the project-owned bibliography. |
| Native output review | pass | All 10 pages were rasterized with PDFKit at 1500 pixels wide and inspected. The one-page article has a legible synthetic figure, equation and figure references, and a resolved citation. The five-page presentation shows the overlay steps on pages 3 and 4. The four-page white handout retains the completed content on page 3. Repeat builds matched input identities, PDF metadata and rendered page hashes. |
| Broken bibliography and unresolved reference | pass | Both builds exited 1 and retained available logs. The diagnostics identify `bib/missing-demo.bib` and `no-such-equation`. |
| Missing pinned Biber | pass | Build exited 2 before creating a run or invoking latexmk. |
| Altered artifact, malformed PDF and legacy receipt | pass | An altered TeX log and a structurally malformed PDF each returned 1 from `check`. The malformed PDF used matching hashes to exercise the pinned PDF reader. An unversioned N1.3 article receipt returned 0 with its original artifacts. |
| Independent tester and maintainer acceptance | not_run | The exact PR revision and evidence are available for independent review. Maintainer acceptance follows that review. |

| Output | Pages | Retained evidence |
|---|---:|---|
| [Article PDF](evidence/n1-4/article/main.pdf) | 1 | [Receipt](evidence/n1-4/article/receipt.json) · [TeX log](evidence/n1-4/article/main.log) · [Biber log](evidence/n1-4/article/main.blg) |
| [Presentation PDF](evidence/n1-4/presentation/main.pdf) | 5 | [Receipt](evidence/n1-4/presentation/receipt.json) · [TeX log](evidence/n1-4/presentation/main.log) · [Biber log](evidence/n1-4/presentation/main.blg) |
| [Handout PDF](evidence/n1-4/handout/handout.pdf) | 4 | [Receipt](evidence/n1-4/handout/receipt.json) · [TeX log](evidence/n1-4/handout/handout.log) · [Biber log](evidence/n1-4/handout/handout.blg) |

The evidence copies preserve original PDF bytes. Local paths in receipts
and logs were replaced with tokens. The receipt hashes describe the
original run files, and the manifest records the hashes of the exported
copies. Run `check` against the original run directory before exporting.

## Reproduce on Apple Silicon

Use the [documented pinned dependencies](latex-stack.md#daily-command),
including the absolute path to the approved native Biber executable. Run
the two regression suites from the Neruda checkout.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s experiments/n1_2 -p 'test_*.py' -v

workspace=$(mktemp -d '/private/tmp/neruda-review.XXXXXX')
mkdir "$workspace/projects with spaces"
parent="$workspace/projects with spaces"
python3 scripts/scaffold.py article model-article --parent "$parent"
python3 scripts/scaffold.py slides model-slides --parent "$parent"

offline() {
  /usr/bin/sandbox-exec -p '(version 1) (allow default) (deny network*)' "$@"
}
probe() {
  "$@" /usr/bin/curl --silent --show-error --max-time 12 --output /dev/null \
    https://www.latex-project.org/help/documentation/
}
probe
offline /usr/bin/true
probe offline
```

For the article, run both figure generations from the project root. For
the slides, run preflight and build/check both entry points without a
figure flag. Run each build/check twice.

```sh
verify() (
  cd "$parent/$1" || exit 1
  entry=$2
  shift 2
  offline python3 scripts/latex.py preflight --lock tools/texlive-lock.json &&
  receipt=$(offline python3 scripts/latex.py build --project . --entry "$entry" \
    --lock tools/texlive-lock.json "$@") &&
  offline python3 scripts/latex.py check --project . --entry "$entry" \
    --lock tools/texlive-lock.json --output "$(dirname "${receipt#Build receipt: }")"
)
(
  cd "$parent/model-article" || exit 1
  for attempt in 1 2; do
    offline python3 figures/source/build.py
    shasum -a 256 src/figures/generated/coordinate-scaling{.png,.receipt.json} \
      >"$workspace/figure-$attempt.sha256"
  done
  cmp "$workspace/figure-1.sha256" "$workspace/figure-2.sha256"
)
for attempt in 1 2; do
  verify model-article src/main.tex \
    --figure-receipt src/figures/generated/coordinate-scaling.receipt.json
  verify model-slides src/main.tex
  verify model-slides src/handout.tex
done
```

The broken bibliography used a fresh article entry with
`bib/references.bib` replaced by `bib/missing-demo.bib`. The reference
fixture pointed the article to a copy of its reproducibility section that
references `no-such-equation`. Both received the same figure receipt
argument. The missing-dependency test passed a nonexistent executable
using `--biber`. The output-check negatives used copies of a successful
run directory. See the manifest for the individual exits and diagnostics.

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

## Provenance review follow-up

The follow-up implementation was built from clean revision
`14ca9b9cdde1faaeb9e5d227c5937af27b9b77db`. The
[follow-up manifest](evidence/n1-4-input-audit/manifest.json) records the
toolchain, source and artifact hashes, pass counts, and per-page render
hashes. The native lock matches the original N1.4 lock.

| Check | Status | Observation |
|---|---|---|
| Behavioral suites | pass | 47 driver and scaffold tests and 45 compatibility experiment tests. They include first-pass-only dependencies, path aliases, changed file identity, scaffold rollback, and legacy receipt and cache compatibility. |
| Standalone starters | pass | Fresh article, presentation and handout projects passed two builds and checks each under macOS network denial. The input identities and rendered pages matched across repeats. The retained initial TeX records contain the font discovery inputs as well as the final-pass inputs. |
| External TeX and Biber inputs | pass | A synthetic article with an absolute TeX include and bibliography outside the project failed without declarations. With SHA-256 declarations it built and checked successfully, and the receipt identified both inputs. A stale hash stopped before compilation. A remote bibliography was refused at the Biber invocation. |
| Bibliography-free profile | pass | An article consuming a project-owned `scientific.dat` passed preflight, build and check with a nonexistent Biber override. Its receipt includes the data hash and has no Biber invocation. |
| Input drift | pass | The bibliography-free fixture signalled after TeX read `scientific.dat`. A separate process changed the file while TeX was still running. The build exited 1 and named the changed input. |
| Missing dependency, broken bibliography and unresolved reference | pass | Missing pinned Biber exited 2 before compilation. Both document failures exited 1 and named the failing input. |
| Visual review | pass | PDFKit rendered all 12 successful pages at 1500 pixels wide. The starter outputs retain the figure, the ordered equation definitions, the slide overlays and the handout's completed content. Both synthetic follow-up fixtures rendered legibly, and the external-bibliography fixture resolved its citation. |
| Independent review and maintainer acceptance | not_run | The updated PR identifies the exact revision for the independent tester. |

Use the same native commands above for the three starters. For the
external-input fixture, use the article's 11pt class and styles. Add an
absolute `\input` path to a synthetic paragraph and an absolute
`\addbibresource` path to a copy of the starter bibliography, both stored
outside the project directory. Build with and without
`--external-inputs PATH` using the [manifest format](latex-stack.md#figures-and-output-checks).
For the bibliography-free fixture, use the 11pt class and styles with a
section heading and `\input{scientific.dat}`. Run `preflight` and `build`
with `--bibliography none` and point `NERUDA_BIBER` at a nonexistent file.
Use the original `check` command with the resulting run.

Early verification showed that a cold LuaLaTeX run scanned host fonts.
The driver now sets the default font discovery policy to the pinned
TeX Live tree in the run-local configuration. The original run retains all
pass evidence. Exported receipts and final logs replace local paths with
tokens, and exported PDFs preserve their bytes. Artifact hashes in the
receipts refer to the original run files.

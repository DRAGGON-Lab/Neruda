# Candidate daily LaTeX stack

MacTeX / TeX Live → LuaLaTeX + latexmk → matched Biber/biblatex → PDF and logs.
Native candidate: LuaHBTeX 1.24.0, latexmk 4.88, Biber 2.21, biblatex 3.21.
See [ADR-003](decisions/ADR-003.md) and [provisioning](mactex-provisioning.md).
This is experimental; local validation is not an accepted supported release.

## Daily command

Python 3.9 or later is required. From the repository root:

```sh
export NERUDA_TEX_ROOT=/usr/local/texlive/2026
export NERUDA_BIBER="$PWD/.tools/texlive-provisioning-20261127/arm64/biber"
python3 scripts/latex.py preflight --lock tools/texlive-lock.json
python3 scripts/latex.py build --project experiments/n1_2/article --entry src/main.tex --lock tools/texlive-lock.json
```

For slides, select project `experiments/n1_2/slides` and entry `src/main.tex`;
for handouts use that project with `src/handout.tex`. Explicit `--tex-root` and
`--biber` override the respective environment selections. All selected binaries
must match the lock; there is no installation, repair or alternative-engine fallback.
The separate native Biber slice is required on this host; the installed universal
loader fails on its unsupported lipo operation. The original remains unchanged.

Every build creates a fresh project-local `build/<unique-id>` and prints the receipt
path. It retains console/TeX/Biber logs, PDF, source and consumed-resource hashes,
Git provenance (or explicit unavailable metadata for portable snapshots), cache
inventory and driver identity. Operational receipts are private; do not upload them
without sanitization. `check --output PATH` rechecks a run's logs and expected files.
Exit codes: 0 compilation checks passed; 1 compilation/output/log failure or timeout;
2 configuration/dependency/cache refusal. Compatibility receipts remain partial
until platform, rendered-page and independent acceptance checks are complete.

The current checks require bibliography artifacts, as all three fixtures use Biber.
Bibliography-free projects and automatic PDF preview integration are not validated.

## Cache and offline experiments

```sh
python3 scripts/latex.py seal-cache --output PATH_TO_SUCCESSFUL_RUN --lock tools/texlive-lock.json
python3 scripts/latex.py build --project experiments/n1_2/article --entry src/main.tex --lock tools/texlive-lock.json --cache-from PATH_TO_SEALED_RUN
python3 experiments/n1_2/texlive_matrix.py --root NEW_EXPERIMENT_DIRECTORY --tex-root "$NERUDA_TEX_ROOT" --biber "$NERUDA_BIBER" --lock tools/texlive-lock.json
```

A seal is an explicit, non-overwriting snapshot of a successful run's cache and raw
receipt. Reuse verifies the lock, receipt digest, source identity and current cache
inventory before copying only compiler/font caches into the new run. It never
repairs the baseline. Warm runs have fresh auxiliary/output directories, so actual
compilation is exercised. Cache seals are integrity checks, not cryptographic trust
or human compatibility approval. They authorize only reuse of a chosen known run.

Cold means empty writable caches with the distribution already installed. The
matrix tests cold, warm, OS-network-denied warm, and OS-network-denied
empty caches for each fixture. It validates a successful HTTPS control and denied
probe first, using `sandbox-exec` with `(deny network*)`. Missing installed resources
are a separate exit-2 negative case. The matrix does not use `--only-cached`.
The Linux adapter creates a new network namespace and restores the unprivileged
runner identity. A successful boundary-ready command is required before accepting
only curl DNS/connect/timeout failure codes as network-denial evidence. Linux
execution and matching-source signature authentication are pending first CI results.

`TEXMFOUTPUT` is the run directory, permitting private font-cache writes under
TeX Live's existing `openout_any=p`; shell escape remains disabled. Environment
isolation is not a filesystem sandbox. Recorded consumed resources must match
pinned hashes; Lua-generated cache contents are recorded separately.

## Lock and project portability

`tools/texlive-lock.json` is the explicitly provisioned native arm64 candidate,
not a universal cross-platform lock. Its `texlive-local-v1` policy records release,
architecture, versions, media, verification reference, tool paths and resource
SHA-256 hashes. The separately approved Biber override has its own hash and source
identity. The initial inventory includes resources observed while populating fresh
font caches, not just final-pass dependencies. Ordinary builds never regenerate it.
Publisher verification is described in the provisioning record; a reference string
or a version probe alone is not proof of trustworthy bytes.

A standalone project can carry `src/`, this driver under `scripts/`, and its lock
under `tools/`, selecting its installed distribution explicitly. On this Mac the
native Biber slice can be kept locally with its recorded hash. An article snapshot
outside the checkout compiled under OS network denial using that layout. No separate
Neruda checkout, editor or AI runtime was needed. Do not commit dependency binaries.
Automatic template scaffolding and general snapshot packaging are separate work.

## Editors and remaining gates

LaTeX Workshop is recommended in repository-local settings. Supply `NERUDA_TEX_ROOT`
and `NERUDA_BIBER` to the VS Code process; its recipe invokes the same driver and lock.
The extension is recommended, not automatically installed. Automatic builds are off.
No editor preferences outside this workspace are modified.

Texmaker is optional: its [ARM64 release](https://www.xm1math.net/texmaker/download.html)
and [custom-command support](https://www.xm1math.net/texmaker/doc.html) can invoke the
same Python command, using quoted explicit project/entry/root/lock/Biber paths.
Its default pdfLaTeX recipe is inappropriate for these Unicode fixtures. Neither
editor integration has been manually exercised in its GUI yet.

Remaining: Linux signature/provisioning execution, Intel Mac validation,
reviewed dependency cache keys, editor GUI checks, independent review and maintainer
acceptance. The matching March 22 snapshot and Ubuntu procedure are prepared and approved for
publication/execution; see [the exact procedure](texlive-linux-provisioning.md).
No system updates, release, merge or issue closure is implied.

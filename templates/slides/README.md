# Neruda presentation starter

Edit `src/metadata.tex`, the files in `src/frames/`, and
`src/bib/references.bib`. The presentation and white-background handout share
the frame sources and bibliography. The handout combines the overlay steps.

## Build on the provisioned Apple Silicon Mac

Use Python 3.9 or later. From this project's root, set both dependency paths
to the provisioned locations on your machine. The second example path is the
lab's durable copy of the pinned native Biber executable.

```sh
uname -m
python3 --version
export NERUDA_TEX_ROOT=/usr/local/texlive/2026
export NERUDA_BIBER="/absolute/path/to/Neruda_artifacts/texlive-2026-native-20261127/biber-arm64"
python3 scripts/latex.py preflight --lock tools/texlive-lock.json
```

Continue after preflight reports `integrity_verified`.

```sh
slides=$(python3 scripts/latex.py build --project . --entry src/main.tex --lock tools/texlive-lock.json) &&
python3 scripts/latex.py check --project . --entry src/main.tex --lock tools/texlive-lock.json \
  --output "$(dirname "${slides#Build receipt: }")"

handout=$(python3 scripts/latex.py build --project . --entry src/handout.tex --lock tools/texlive-lock.json) &&
python3 scripts/latex.py check --project . --entry src/handout.tex --lock tools/texlive-lock.json \
  --output "$(dirname "${handout#Build receipt: }")"
```

Each run directory under `build/` contains its PDF (`main.pdf` or
`handout.pdf`), TeX and Biber logs, and `receipt.json`. Read the logs and
inspect every page of both versions. Confirm that each handout page retains
the intended overlay content. The driver uses isolated build caches and
disables shell escape. A Neruda checkout and AI runtime are optional.

The original starter and styles are distributed under [MIT](LICENSE).

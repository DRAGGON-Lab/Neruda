# Neruda article starter

Edit `src/metadata.tex`, the files in `src/sections/`, and
`src/bib/references.bib`. The starter demonstrates mathematical notation with
a synthetic worked example. Project-owned styles are alongside `src/main.tex`.

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

Continue after preflight reports `integrity_verified`. Generate the synthetic
coordinate-scaling PNG explicitly. Its receipt records the Python runtime
and SHA-256 hashes of the generator, data and output.

```sh
python3 figures/source/build.py
```

```sh
receipt=$(python3 scripts/latex.py build --project . --entry src/main.tex --lock tools/texlive-lock.json \
  --figure-receipt src/figures/generated/coordinate-scaling.receipt.json) &&
python3 scripts/latex.py check --project . --entry src/main.tex --lock tools/texlive-lock.json \
  --output "$(dirname "${receipt#Build receipt: }")"
```

Regenerate the figure after changing the generator or its synthetic inputs
in `figures/source/`. When removing the example figure, remove its
`\includegraphics` call and its corresponding figure receipt argument.

The run directory under `build/` contains `main.pdf`, the TeX and Biber logs,
and `receipt.json`. The output check verifies the retained artifacts against
the receipt. Read the logs and inspect every PDF page. The driver uses
isolated build caches and disables shell escape. A Neruda checkout and AI
runtime are optional.

The original starter and styles are distributed under [MIT](LICENSE).

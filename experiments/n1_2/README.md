# N1.2 compatibility investigation

This is a spike, not the production Neruda interface. It neither installs tools
nor imports LaTexProjects. All fixtures are synthetic, with no research claims.
The extensive production authoring starters remain N1.3 work.

## Run

Provide a directory containing exactly the approved `tectonic` and `biber`
executables (no `tectonic-biber`). The runner verifies exact version output.
Archive verification is a separate provisioning prerequisite; version strings
alone do not establish binary provenance.

```sh
python3 -m unittest discover -s experiments/n1_2 -p 'test_*.py' -v
python3 experiments/n1_2/run.py --tool-dir .tools/n1_2/bin --work-root /private/tmp/neruda-n1-2-native-20261127 --case cold
```

After a successful cold run, invoke the same command with `--case warm`,
`--case offline`, and `--case offline-empty`. Each case preserves its own source
copy, console logs, intermediate files and JSON receipt; existing case directories
are refused. Warm/offline reuse only this experiment's cache. The empty-cache
offline case is expected to fail, and is recorded as a failed build. The engine's
`--only-cached` switch is not a system-level network isolation proof.

Exit 2 means preflight/refusal, exit 1 means build failure, and exit 0 means the
compilation completed. Compilation receipts remain **partial** pending log,
semantic, font, bundle, and independent visual review. A successful command is
not acceptance of N1.2. Never upload host caches or private environment records.

## Review

Inspect final TeX/Biber logs for missing files, undefined citations/references,
rerun requests, font substitutions, overfull boxes and warnings. Confirm the
actual biblatex package version and resolved fonts from intermediates/cache.
Render and inspect every PDF page; check equation definitions, Unicode glyphs,
table values, reference resolution and bibliography. Presentation overlays must
collapse in the handout. Record page counts and PDF hashes alongside review.

Linux x86_64 must repeat this procedure on a fresh runner with verified Linux
archives; local macOS success cannot substitute for that evidence. A CI workflow
is deferred until provisioning is established, rather than publishing an untested
installer or implying successful Linux coverage.

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

## Durable evidence and isolation

`--evidence-root PATH` defaults to tracked `experiments/n1_2/evidence/`.
Every attempted build and failed preflight exports a unique sanitized receipt;
builds also export console/TeX/Biber logs. `manifest.json` records raw and exported
SHA-256 identities. Operational receipts and caches remain in the work root;
only operational receipts authorize warm/offline reuse. Public receipts contain
path tokens and must not be used as operational receipts. Review exports before
committing; the exporter only targets public synthetic fixture runs and is not
a general secret scanner for arbitrary documents or diagnostics.

All version/build processes use a constructed environment and private Biber shim
with `--noconf`. Native Apple Silicon is a validation target alongside Intel Mac
and Linux; see the compatibility report for observed blockers and the bounded
newer-bundle comparison. No support is inferred from archive availability.

## Candidate manual Biber arm64 provisioning

For the reviewed Biber 2.17 universal archive only, manual `lipo -thin arm64`
can bypass its unsupported universal-loader operation. Preserve the original;
use a fresh directory and verify derived architecture, slice checksum, signature
status and isolated exact-version output before builds. Copy the unchanged,
verified Tectonic into the same directory. This is not an automatic runner step.
See the compatibility report for exact source/derived hashes and the observed
signature and HTTP 429 limitations. Do not repair signatures or install system
tools as part of this procedure. All build cases retain the existing runner CLI.

## Provenance and cache refusal behavior

Git warnings are retained in `git_diagnostics`, separately from revision and
porcelain dirty-state stdout. Unavailable/invalid Git metadata prevents compilation
with exit 2 and an exported not_run receipt.

Warm/offline reuse requires an exact current file inventory match to the successful
cold receipt. Do not modify the cache between cases. Added, missing or changed
files, links and unsupported/unreadable entries are refused before compilation.
A warm build changing the inventory requires a fresh cold experiment; a later
receipt does not automatically authorize the changed cache. Existing evidence
and cache contents are preserved on refusal.

## Linux compatibility job

The approved `.github/workflows/n1-2-compatibility.yml` job uses Ubuntu 24.04 and
runs `python3 experiments/n1_2/linux_ci.py --root .tools/n1_2/linux-ci` after the
regression suite. This experimental CI helper downloads the exact reviewed Linux
archives, verifies SHA-256 before extracting one regular x86_64 ELF executable
per archive, and invokes the existing runner with a fresh work root. The Biber
archive digest is locally measured, not independently publisher-corroborated.
No system package installation or cache repair is performed.

Cold failure skips warm/offline cases but still attempts empty-cache offline.
A failing compatibility matrix fails the job. Sanitized provisioning/build
receipts and logs are uploaded even on failure, retained for 30 days. Successful
synthetic PDFs are retained with checksums for subsequent all-page review; the
job never claims visual acceptance. Archive/binary caches and raw tool directories
are excluded. The workflow checks out the PR head with credentials persistence
disabled and read-only repository permissions. Changing action/archive pins
requires review. Selected evidence must be committed before artifact expiry.

Ubuntu 22.04 was attempted first and could not start the pinned GNU Tectonic
binary (requires GLIBC_2.39). The user approved a fresh Ubuntu 24.04 environment;
no existing system libraries were upgraded. Documentation/evidence-only changes
do not retrigger the compatibility job. Runner image identity is recorded in
provisioning receipts; the distribution label is not an immutable image digest.

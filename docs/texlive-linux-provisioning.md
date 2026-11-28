# Prepared Ubuntu validation — publication and first execution approved

On 2026-11-28 the maintainer explicitly approved publishing the prepared changes to
PR #11 and running this Ubuntu validation procedure. Preserve that approval; do
not request it again for these exact steps. Execution results are recorded
separately; approval is not proof that GPG verification or compilation succeeded.

## Selected source and observed comparison

The official March 1 TeX Live 2026 ISO matches its published SHA-512, but is
**not the MacTeX snapshot**. Fifteen packages represented in the native dependency
inventory differ, including geometry 5.9 versus 6.0 and latexmk 4.87 versus 4.88.
No ISO installer or Linux executable was run. Its GPG verification remains pending;
the ISO is retained as comparison evidence, not promoted to a build dependency.

TUG documents the dated tlnet archive maintained by Norbert Preining:
[package-installation guidance](https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/web/pkginstall.html).
The archive for **2026-03-22** matches revisions and container SHA-512 values of all
**4,478 MacTeX packages with shared runtime files**. The Mac installation profile
itself records creation on March 22. This source preserves the observed compatibility
unit without changing the Mac installation. Adjacent dates were compared; none
matched that entire set. Metadata authentication has not yet run locally because
GnuPG is absent. Archive files remain quarantine data until official signatures pass.

## Approved CI procedure

Publish `.github/workflows/texlive-linux-compatibility.yml` and run it on PR #11
using a fresh Ubuntu 24.04 x86_64 runner. Its source and profile are pinned in
`tools/texlive-linux-source.json` and `tools/texlive-ci.profile`.

1. Run both regression suites independently of distribution availability.
2. Create a new `.tools/texlive-linux-ci` tree, refusing an existing destination.
   Require at least 10 GiB free; do not delete preinstalled tools to make space.
3. Download the official TeX Live public key to a private GnuPG home. Require its
   pinned file SHA-256 and the documented primary fingerprint
   `C78B82D8C79512F79CC0D7C80D5E5D9106BAB6BC`.
4. Verify signed checksums for the dated installer and repository database with
   `/usr/bin/gpg`. Require `VALIDSIG` for that primary key, not merely a successful
   download or a matching locally measured hash. See
   [TUG verification instructions](https://tug.org/texlive/verify.html).
5. Verify the installer and compressed/uncompressed database pins before extraction
   or installer execution. Retain failed downloads and logs; use bounded retries.
6. Invoke the verified installer, as the unprivileged runner user:

```text
/usr/bin/perl <WORK>/installer/install-tl-20260322/install-tl \
  --repository https://texlive.info/tlnet-archive/2026/03/22/tlnet \
  --profile <WORK>/texlive.profile --no-interaction --verify-downloads
```

`<WORK>` is the resolved new `.tools/texlive-linux-ci` directory. The inspected
installer supports these exact options and refuses to proceed without GPG when
`--verify-downloads` is requested. The profile installs the complete runtime scheme
there, excluding documentation/source archives, with no PATH/MANPATH, desktop or
file-association changes. HOME, temporary files and TeX configuration are private.
No apt, Homebrew, Docker, Rosetta or system TeX installation is involved.

7. Compare the installed shared resource bytes against the native reference lock,
   require exact compiler/Biber/latexmk versions and identical latexmk script bytes.
   Record platform-specific binaries and generated formats in a new candidate Linux
   lock under the work tree; never regenerate the committed Mac lock. A mismatch
   stops fixture compilation and prints the affected resources.
8. Compile article, presentation and handout in cold, warm, OS-network-denied warm,
   and OS-network-denied empty-cache scenarios. Missing dependencies must refuse.
   Linux isolation uses `sudo -n /usr/bin/unshare --net`, then `/usr/bin/setpriv`
   to restore the runner's UID/GID/groups and prohibit gaining new privileges before
   running each command. No global networking or security setting changes.
9. Upload only sanitized synthetic receipts/logs/PDFs for 30 days, including failed
   attempts. Print phase, primary diagnostics and actual case exit codes in the job
   summary. Failed required checks fail the job; skipped builds are `not_run`.

Installer SHA-256:
`11877c9ba5356fdfd5a23747f95ad4f467169f3569dce065b1c5b0fe2a0c5052`.
Compressed repository database SHA-256:
`f6dab808e04d7dc6bc8861b6801af4f8d2b62e7a171ffcd6fa05d8cfb1642a12`.
Signed SHA-512 values and the reference-lock digest are in the source configuration.
These are measured identities, **not a claim that local GPG verification passed**.
CI must establish that authentication before using this third-party archive.

The first approved execution is recorded below. No supported Linux result or release
is asserted. There is no cross-platform distribution cache yet: first establish and
review the Linux provisioning result before caching a trusted immutable installation.
Compiler/font cache integrity and reuse are tested separately. Intel macOS remains
an additional validation target. Existing Tectonic evidence and gates remain intact.

AGENT.md requires approval of the exact provisioning mutation. Earlier Ubuntu
approvals covered Tectonic/Biber archives, not this TeX Live installation procedure.
The approval recorded above concerns the workflow and its first execution; it does not
accept the architecture, merge the PR, close issues or authorize a supported release.

## First Ubuntu execution — blocked before installation

[Run 46087960068](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46087960068)
tested commit `3a1ede2df77076108d5e4dcf1dc6aabaa4943ee8` on Ubuntu 24.04.5,
glibc 2.39 and GnuPG 2.4.4. Both regression suites passed (57 tests). Key import
succeeded, but installer-signature verification failed with GPG `NODATA` / exit 2.
No installer ran; shared-resource checks, Linux tool versions and all fixture builds
are **not_run**, not failed compatibility tests.

A separate read-only request to the exact signature endpoint returned HTTP 200,
`text/html`, and a 2,402-byte HTML access-challenge page titled “Oh noes!”.
This explains why HTTP success alone is insufficient. The downloader now rejects
HTML explicitly, retains the raw response privately and exports its URL, MIME type,
size and SHA-256. It does not solve challenges, fall back to another source or weaken
the signature gate. Regression tests cover this response and exact-byte downloads.

[Sanitized evidence](../experiments/n1_2/evidence/texlive-linux-20261128/46087960068/)
and the [original artifact](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46087960068/artifacts/15239224827)
retain the negative result. Downloaded export hashes were independently checked
against the artifact manifest. The HTML body remains private.

Progress requires accessible machine downloads from the approved dated source, or
a separately reviewed authenticated copy of the same signed snapshot. No such
alternative has been provisioned or approved. A current CTAN mirror or March 1 ISO
would change the reviewed unit; neither is an automatic fallback. Do not repeat
large installation attempts while this signature endpoint remains blocked.

[Run 46088531399](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46088531399)
tested `ec277a9b276dc9ed1a534954c10698a2a5356ab8`: **all 59 tests passed**.
Provisioning then refused the HTML response at the signed-checksum endpoint with
the explicit diagnostic directly in the job output; the job exited 1 as required.
The [second artifact](https://github.com/DRAGGON-Lab/Neruda/actions/runs/46088531399/artifacts/15239812745)
and [checked-in evidence](../experiments/n1_2/evidence/texlive-linux-20261128/46088531399/)
preserve the result and download identity. Every exported file matched its manifest.
Additional read-only checks found HTML at the installer, compressed database and
`archive/geometry.tar.xz` endpoints too; retaining earlier signature files alone
would not solve current package access. No further installation run is warranted
until source access is resolved.

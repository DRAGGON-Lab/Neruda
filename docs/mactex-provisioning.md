# MacTeX installation — verified and installed by maintainer

On 2026-11-27 the maintainer explicitly approved the TeX Live 2026-only
installation below, conditional on checksum and publisher-signature verification.
This includes the recorded default-selection/path changes and excludes GUI and
Ghostscript updates. No repeated approval is needed for this exact procedure.

Official archive: `https://tug.ctan.org/systems/mac/mactex/mactex-20260324.pkg`.
Publisher SHA-512 retrieved on 2026-11-27 from the matching `.sha512` URL:

```text
68a62ac1d9e94bc049a64997bb60bd5969b5a82f5e16ad18cb776947e9f109c74be56ec9abbd2569b3abd1373929fe39586a7bb8c2179a72d9b914a513055623
```

The complete download is retained in ignored `.tools/texlive-provisioning-20261127/`.
Size: 6,865,013,189 bytes. Measured SHA-512 matches the publisher value above.
Measured SHA-256:
`e30af0640f51979a95b9f54084456d1e16749b79e12e65bdebd630fb2795ff1e`.
`pkgutil --check-signature` outside the sandbox confirms a trusted, notarized
Developer ID Installer certificate for Richard Koch (`RBGCY5RJWM`), timestamped
2026-03-22 20:21:27 UTC. The initial sandboxed check reported an invalid signature;
the outside-sandbox check with macOS trust-service access passed. No protection
was bypassed or modified.

The XAR Distribution and TeX Live Scripts range reads match the corresponding
bytes in the completely verified archive. Their SHA-256 values are respectively
`e8d8a5e4d1a29561d3a81589007c73d443f0f1d9ef5c9f29dae73dcd5c09f3c4`
and `ad12b0fa33d6eff0a9429eb9f88f27c6ee22bc462dd7cd4a2deff35a51827996`.
`installer -showChoicesAfterApplyingChangesXML` outside the sandbox confirms only
TeX Live selected, with GUI and all Ghostscript options deselected. The maintainer
subsequently installed it; the 2026 package receipt and default-selection link
confirm the installed tree. Raw archive/metadata verification JSON is in the ignored
provisioning directory; this document preserves the public-safe results.

The inspected Distribution specifies the exact component identifiers in
`tools/mactex-2026-choices.xml`: select TeX Live 2026 only; deselect GUI and all
three Ghostscript choices. The inspected postinstall script writes the 2026 tree,
replaces default-selection links under `/Library/TeX`, writes `/etc/paths.d/TeX`
and `/etc/manpaths.d/TeX`, and may initialize absent `texmf-local`. It runs
`tlmgr paper a4` when the host paper preference is A4, then `mktexlsr`,
`updmap-sys`, `fmtutil-sys --missing`, and `mktexlsr` in the new tree. These are
part of the proposed mutation, not ordinary compile behavior. Preserve/record
existing selection links and path files before installation. Do not remove 2020.

After full SHA-512 equality and valid expected publisher signature, inspect
`installer -showChoicesAfterApplyingChangesXML` to confirm only TeX Live selected.
The exact installation proposed for approval, from the repository root, is:

```sh
sudo /usr/sbin/installer \
  -pkg .tools/texlive-provisioning-20261127/mactex-20260324.pkg \
  -applyChoiceChangesXML tools/mactex-2026-choices.xml \
  -target /
```

Approval is recorded above. Abort for changed archive identity,
signature failure, unexpected component choices or unexpected installer scripts.
No security-control bypass, Rosetta installation or old-tree removal is proposed.

Linux candidate `texlive2026-20260301.iso` publisher SHA-512 retrieved separately:

```text
4a9071bb567c3bdd6443378dedc8e485aea4a2f1203ec8ed7c17f6787093b9c37636a037032c0be63352e3d0bf98cf5616dab19fdcd7cb83f766b3e085b620ff
```

The ISO has not been downloaded and its signature has not been verified. Shared
package identity remains untested. No Linux provisioning workflow is published.

Local verification: 16 driver regressions and 41 N1.2 regressions pass on Python
3.9. Real native compilation/cache results are documented in ADR-003.

The agent's `sudo -n true` required a password. The maintainer entered credentials
locally and completed installation. Previous selection links and path-file contents
are retained in the ignored provisioning directory's `pre-install-state.json`.
The 2020 tree remains present.

## Approved native Biber derivative

The installed universal Biber loader calls unsupported `lipo -extract_family`.
The maintainer explicitly approved a separate arm64 extraction:

```sh
/usr/bin/lipo /usr/local/texlive/2026/bin/universal-darwin/biber -thin arm64 -output .tools/texlive-provisioning-20261127/arm64/biber
chmod u+x .tools/texlive-provisioning-20261127/arm64/biber
```

Source SHA-256: `d3fb508fcd0623e2f8e802f8ff49acdf0fd6fe33874cf7ea9734d6b3334dfe17`.
Derived SHA-256: `a1a2784931d9156a9d4cc8cb609912d533f04365d2e4aa7b902001a2f1a65066`.
`file` identifies native arm64; startup returns `biber version: 2.21`.
`codesign --verify --verbose=2` reports an invalid signature on the derived slice.
No resigning, quarantine removal, Rosetta or system-binary replacement occurred.
The installed source and derived hashes are pinned separately.

"""Explicit provisioning and compatibility experiment for an ephemeral Linux runner."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from urllib.request import urlopen

import run

ARCHIVES = {
    "tectonic": (
        "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-x86_64-unknown-linux-gnu.tar.gz",
        "1a715688baf591e650c8aeb160ae934e181685eecbb38b317de30b269ac5d606",
        "official GitHub release digest",
    ),
    "biber": (
        "https://downloads.sourceforge.net/project/biblatex-biber/biblatex-biber/2.17/binaries/Linux/biber-linux_x86_64.tar.gz",
        "129d2e0332a57e985ffa253e5e9fbd28ef99af5a068d1b141145211969aa8999",
        "locally measured official download; not publisher-corroborated",
    ),
}


def extract(archive, destination, name, expected):
    """Verify bytes before extracting exactly one regular file without tar paths."""
    if run.digest(archive) != expected:
        raise ValueError(f"{name} archive checksum mismatch")
    with tarfile.open(archive) as source:
        members = source.getmembers()
        if len(members) != 1 or members[0].name != name or not members[0].isfile():
            raise ValueError(f"unexpected {name} archive members")
        with (destination / name).open("xb") as target:
            shutil.copyfileobj(source.extractfile(members[0]), target)
    (destination / name).chmod(0o755)
    data = (destination / name).read_bytes()
    if data[:6] != b"\x7fELF\x02\x01" or int.from_bytes(data[18:20], "little") != 62:
        raise ValueError(f"{name} is not an ELF64 x86_64 executable")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args(argv)
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        parser.error("requires native Linux x86_64")
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    tools = root / "bin"
    tools.mkdir()
    raw = root / "provisioning"
    raw.mkdir()
    public = root / "public"
    receipt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **run.source_metadata(), "platform": platform.platform(),
        "python": sys.version, "harness_sha256": run.digest(Path(__file__)),
        "status": "not_run", "archives": {},
    }
    try:
        if receipt["source_revision"] is None or receipt["dirty_state"] is None:
            raise ValueError("Git provenance unavailable")
        for name, (url, expected, verification) in ARCHIVES.items():
            archive = root / (name + ".tar.gz")
            with urlopen(url, timeout=60) as response, archive.open("xb") as target:
                shutil.copyfileobj(response, target)
            receipt["archives"][name] = {
                "url": url, "expected_sha256": expected,
                "actual_sha256": run.digest(archive), "verification": verification,
            }
            extract(archive, tools, name, expected)
            receipt["archives"][name]["executable_sha256"] = run.digest(tools / name)
        receipt["status"] = "pass"
    except Exception as error:
        receipt.update(status="fail", diagnostic=str(error))
    finally:
        (raw / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        run.export_evidence(raw, public / "provisioning", {
            str(root): "<CI_ROOT>", str(run.HERE.parents[1]): "<REPOSITORY>",
            str(Path.home()): "<HOME>",
        })
    if receipt["status"] != "pass":
        print("Linux provisioning failed; see preserved public receipt", file=sys.stderr)
        return 1
    outcomes = {}
    for case in ("cold", "warm", "offline", "offline-empty"):
        if case in ("warm", "offline") and outcomes["cold"] != 0:
            outcomes[case] = "not_run: cold did not compile"
            continue
        try:
            outcomes[case] = run.main([
                "--tool-dir", str(tools), "--work-root", str(root / "work"),
                "--evidence-root", str(public / "builds"), "--case", case,
            ])
        except SystemExit as error:
            outcomes[case] = error.code
    pdfs = {}
    for case in ("cold", "warm", "offline"):
        for kind, output in (("article", "article"), ("slides", "slides"), ("slides", "handout")):
            source = root / "work" / case / kind / "build" / output / (output + ".pdf")
            if source.is_file() and not source.is_symlink():
                target = public / "pdfs" / case / (output + ".pdf")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                pdfs[str(target.relative_to(public))] = run.digest(target)
    (public / "pdf-manifest.json").write_text(json.dumps(pdfs, indent=2) + "\n")
    summary = {"cases": outcomes, "visual_review": "not_run",
               "limitations": ["Biber publisher checksum corroboration pending",
                               "Successful compilation requires separate log and all-page review"]}
    (public / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if all(outcomes.get(case) == 0 for case in ("cold", "warm", "offline")) and outcomes.get("offline-empty") == 1 else 1


if __name__ == "__main__":
    sys.exit(main())

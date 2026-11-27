"""Non-installing compatibility experiment. Never repairs tools or caches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
BUNDLE = "https://data1.fullyjustified.net/tlextras-2022.0r0.tar"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(argv, cwd=None, env=None, timeout=600):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return result.returncode, result.stdout


def preflight(tool_dir):
    tools = {}
    for name, expected in (("tectonic", "Tectonic 0.17.0"), ("biber", "biber version: 2.17")):
        path = tool_dir / name
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"missing executable: {path}; installation requires approval")
        try:
            code, output = execute([str(path), "--version"], timeout=60)
        except subprocess.TimeoutExpired as error:
            raise ValueError(f"{name} --version exceeded 60 seconds") from error
        if code or output.strip() != expected:
            raise ValueError(f"{name} version mismatch: expected {expected!r}, got {output.strip()!r}")
        tools[name] = {"path": str(path), "version": output.strip(), "sha256": digest(path)}
    if (tool_dir / "tectonic-biber").exists():
        raise ValueError("remove ambiguity: tool directory must not contain tectonic-biber")
    return tools


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-dir", required=True, type=Path)
    parser.add_argument("--work-root", required=True, type=Path)
    parser.add_argument("--case", required=True, choices=("cold", "warm", "offline", "offline-empty"))
    args = parser.parse_args(argv)
    work = args.work_root.resolve()
    # Never mutate caller inputs or reuse output from another attempt.
    if work == HERE or work in HERE.parents or HERE in work.parents and work.name != "artifacts":
        parser.error("work root must be outside fixture source (or the ignored artifacts directory)")
    run = work / args.case
    if run.exists():
        parser.error(f"run already exists: {run}; choose a fresh work root, do not delete evidence")
    try:
        tools = preflight(args.tool_dir.resolve())
    except ValueError as error:
        print(f"not_run: {error}", file=sys.stderr)
        return 2
    cache = work / ("empty-cache" if args.case == "offline-empty" else "cache")
    if cache.is_symlink():
        parser.error("cache must not be a symlink")
    if args.case in ("warm", "offline") and not cache.is_dir():
        parser.error("warm/offline requires the cache from a cold run in this work root")
    if args.case in ("warm", "offline"):
        try:
            cold = json.loads((work / "cold" / "receipt.json").read_text())
        except (OSError, ValueError):
            parser.error("warm/offline requires a valid cold receipt")
        current_inputs = {str(p.relative_to(HERE)): digest(p) for kind in ("article", "slides")
                          for p in sorted((HERE / kind).rglob("*")) if p.is_file()}
        if (cold.get("compilation") != "pass" or cold.get("tools") != tools
                or cold.get("inputs") != current_inputs or cold.get("cache") != str(cache)):
            parser.error("cold receipt must describe a successful build with identical inputs and tools")
    if args.case in ("cold", "offline-empty") and cache.exists():
        parser.error("cold/empty-cache case refuses a preexisting cache")
    run.mkdir(parents=True)
    cache.mkdir(exist_ok=True)
    receipt = {
        "timestamp": datetime.now(timezone.utc).isoformat(), "case": args.case,
        "platform": platform.platform(), "architecture": platform.machine(),
        "tools": tools, "bundle_url": BUNDLE, "cache": str(cache),
        "source_revision": execute(["git", "rev-parse", "HEAD"], HERE)[1].strip(),
        "dirty_state": execute(["git", "status", "--porcelain"], HERE)[1],
        "inputs": {str(p.relative_to(HERE)): digest(p) for kind in ("article", "slides")
                   for p in sorted((HERE / kind).rglob("*")) if p.is_file()},
        "harness": {name: digest(HERE / name) for name in ("run.py", "test_runner.py")},
        "builds": [], "visual_review": "not_run", "status": "partial",
        "limitations": ["PDF inspection and font/bundle content identity require independent review",
                        "only-cached is an engine option, not an OS network sandbox"],
    }
    env = os.environ.copy()
    # Only the isolated directory supplies bibliography commands. General shell
    # tools remain available from system directories, not the user's environments.
    env.update(PATH=str(args.tool_dir.resolve()) + os.pathsep + "/usr/bin:/bin",
               TECTONIC_CACHE_DIR=str(cache), SOURCE_DATE_EPOCH="1786060800")
    failed = False
    try:
        for kind in ("article", "slides"):
            project = run / kind
            shutil.copytree(HERE / kind, project)
            command = [tools["tectonic"]["path"], "-X", "build", "--keep-logs", "--keep-intermediates"]
            if args.case.startswith("offline"):
                command.append("--only-cached")
            try:
                code, output = execute(command, project, env)
            except subprocess.TimeoutExpired as error:
                partial = error.output or ""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", errors="replace")
                code, output = 124, partial + f"\nBuild exceeded 600 seconds: {error}"
            (run / f"{kind}.console.log").write_text(output)
            pdfs = {str(p.relative_to(run)): digest(p) for p in sorted(project.rglob("*.pdf"))}
            receipt["builds"].append({"kind": kind, "command": command, "exit_code": code, "pdfs": pdfs})
            expected = ([project / "build/article/article.pdf"] if kind == "article" else
                        [project / "build/slides/slides.pdf", project / "build/handout/handout.pdf"])
            failed |= code != 0 or any(not p.is_file() or p.stat().st_size == 0 for p in expected)
        receipt["status"] = "fail" if failed else "partial"
        receipt["compilation"] = "fail" if failed else "pass"
    finally:
        receipt["cache_inventory"] = {str(p.relative_to(cache)): digest(p)
                                      for p in sorted(cache.rglob("*")) if p.is_file()}
        (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(run / "receipt.json")
    # Expected failure is recorded as a failure, never relabelled a clean build.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""Non-installing compatibility experiment. Never repairs tools or caches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import bundle
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
BUNDLE = "https://data1.fullyjustified.net/tlextras-2022.0r0.tar"


def fixture_inputs():
    """Generated build trees are not source inputs or reusable fixture assets."""
    inputs = {}
    for kind in ('article', 'slides'):
        for directory, subdirectories, names in os.walk(HERE / kind):
            subdirectories[:] = sorted(name for name in subdirectories if name != 'build')
            for name in sorted(names):
                path = Path(directory) / name
                if path.is_file():
                    inputs[str(path.relative_to(HERE))] = digest(path)
    return inputs


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(argv, cwd=None, env=None, timeout=600):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return result.returncode, result.stdout


def source_metadata():
    metadata = {"source_revision": None, "dirty_state": None, "git_diagnostics": {}}
    for field, arguments in (("source_revision", ["rev-parse", "--verify", "HEAD^{commit}"]),
                             ("dirty_state", ["status", "--porcelain"])):
        try:
            result = subprocess.run(["/usr/bin/git", *arguments], cwd=HERE,
                                    env={"PATH": "/usr/bin:/bin"}, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            diagnostic = {"exit_code": result.returncode, "stderr": result.stderr}
            value = result.stdout.strip() if field == "source_revision" else result.stdout
            if result.returncode == 0 and (field != "source_revision" or re.fullmatch(r"[0-9a-f]{40}", value)):
                metadata[field] = value
            else:
                diagnostic.update(stdout=result.stdout, error="Git failed or returned invalid metadata")
        except (OSError, subprocess.TimeoutExpired) as error:
            diagnostic = {"exit_code": None, "error": str(error)}
        metadata["git_diagnostics"][field] = diagnostic
    return metadata


def cache_inventory(cache):
    """Hash regular files only; refuse links and special entries without following them."""
    inventory = {}
    def visit(directory):
        for path in sorted(directory.iterdir()):
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                visit(path)
            elif stat.S_ISREG(mode):
                inventory[str(path.relative_to(cache))] = digest(path)
            else:
                raise ValueError(f"unsupported cache entry: {path}")
    if cache.is_symlink() or not cache.is_dir():
        raise ValueError("cache must be a regular directory")
    visit(cache)
    return inventory


POLICY = "local-bundle-v2"


def environment(root, cache, tools):
    """Construct, never inherit, the environment of every tool invocation."""
    root.mkdir(parents=True, exist_ok=True)
    for name in ("home", "config", "data", "tmp", "par", "bin", "texmf"):
        (root / name).mkdir(exist_ok=True)
    # Tectonic launches biber by name. The shim disables all config discovery,
    # including kpsewhich in an existing system TeX installation.
    shim = root / "bin" / "biber"
    shim.write_text("#!" + sys.executable + "\nimport os, sys\nos.execv(" +
                    repr(str(tools / "biber")) + ", [" + repr(str(tools / "biber")) +
                    ", '--noconf', *sys.argv[1:]])\n")
    shim.chmod(0o700)
    return {
        "PATH": str(root / "bin"), "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"),
        "XDG_CACHE_HOME": str(root / "cache"), "TMPDIR": str(root / "tmp"),
        "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
        "PAR_GLOBAL_TMPDIR": str(root / "par"), "TECTONIC_CACHE_DIR": str(cache),
        "TEXMFHOME": str(root / "texmf"), "TEXMFCONFIG": str(root / "texmf"),
        "TEXMFVAR": str(root / "texmf"), "TEXMFCACHE": str(root / "texmf"),
        "LC_ALL": "C", "LANG": "C", "TZ": "UTC", "SOURCE_DATE_EPOCH": "1786060800",
    }


def export_evidence(run, destination, replacements):
    """Export only public fixture receipts/logs; raw receipts stay operational."""
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for path in sorted(run.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if path.name != "receipt.json" and path.suffix not in (".log", ".blg"):
            continue
        content = path.read_text(errors="replace")
        if path.name == "receipt.json":
            receipt = json.loads(content)
            dirty = receipt.pop("dirty_state", None)
            if "git_diagnostics" in receipt:
                receipt["git_diagnostics"].pop("dirty_state", None)
            receipt["source_dirty"] = None if dirty is None else bool(dirty)
            content = json.dumps(receipt, indent=2) + "\n"
        for source, token in sorted(replacements.items(), key=lambda item: -len(item[0])):
            content = content.replace(source, token)
        content = re.sub(r"par-[0-9a-f]+/", "par-<USER>/", content)
        content = re.sub(r"neruda-probe-[A-Za-z0-9_-]+", "neruda-probe-<ID>", content)
        target = destination / path.relative_to(run)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        manifest[str(path.relative_to(run))] = {"raw_sha256": digest(path), "export_sha256": digest(target)}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def preflight(tool_dir):
    tools = {}
    for name, expected in (("tectonic", "Tectonic 0.17.0"), ("biber", "biber version: 2.17")):
        path = tool_dir / name
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"missing executable: {path}; installation requires approval")
        try:
            with tempfile.TemporaryDirectory(prefix="neruda-probe-") as temporary:
                root = Path(temporary)
                env = environment(root, root / "cache", tool_dir)
                code, output = execute([str(path), "--version"], cwd=root, env=env, timeout=60)
        except subprocess.TimeoutExpired as error:
            raise ValueError(f"{name} --version exceeded 60 seconds") from error
        except OSError as error:
            raise ValueError(f"could not launch {name} --version: {error}") from error
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
    parser.add_argument("--evidence-root", type=Path, default=HERE / "evidence")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--bundle-lock", type=Path)
    parser.add_argument("--case", required=True, choices=("cold", "warm", "offline", "offline-empty"))
    args = parser.parse_args(argv)
    work = args.work_root.resolve()
    evidence_root = args.evidence_root.resolve()
    if evidence_root.is_relative_to((work / args.case).resolve()):
        parser.error("evidence root must be outside the case directory")
    if any(evidence_root.is_relative_to((work / name).resolve()) for name in ("cache", "empty-cache")):
        parser.error("evidence root must be outside the operational caches")
    # Never mutate caller inputs or reuse output from another attempt.
    if work == HERE or work in HERE.parents or HERE in work.parents and work.name != "artifacts":
        parser.error("work root must be outside fixture source (or the ignored artifacts directory)")
    run = work / args.case
    if run.exists():
        parser.error(f"run already exists: {run}; choose a fresh work root, do not delete evidence")
    metadata = source_metadata()
    try:
        if metadata["source_revision"] is None or metadata["dirty_state"] is None:
            raise ValueError("Git provenance unavailable; see git_diagnostics")
        dependency = bundle.verify(args.bundle, args.bundle_lock)
        tools = preflight(args.tool_dir.resolve())
    except (ValueError, OSError) as error:
        print(f"not_run: {error}", file=sys.stderr)
        with tempfile.TemporaryDirectory(prefix="neruda-probe-evidence-") as temporary:
            evidence = Path(temporary)
            (evidence / "receipt.json").write_text(json.dumps({
                **metadata,
                "status": "not_run", "compilation": "not_run", "case": args.case,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "architecture": platform.machine(), "platform": platform.platform(), "environment_policy": POLICY,
                "inputs": fixture_inputs(),
                "tools": {name: {"sha256": digest(args.tool_dir.resolve() / name)} for name in ("tectonic", "biber") if (args.tool_dir.resolve() / name).is_file()},
                "diagnostic": str(error), "bundle_url": BUNDLE,
                "harness": {name: digest(HERE / name) for name in ("run.py", "test_runner.py", "bundle.py")},
            }, indent=2) + "\n")
            attempt = "preflight-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
            export_evidence(evidence, args.evidence_root.resolve() / attempt, {
                str(args.tool_dir.resolve()): "<TOOLS>", str(HERE.parents[1]): "<REPOSITORY>",
                str(Path.home()): "<HOME>", tempfile.gettempdir(): "<TMP>",
            })
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
        current_inputs = fixture_inputs()
        if (not isinstance(cold, dict) or cold.get("environment_policy") != POLICY
                or cold.get("bundle") != dependency
                or cold.get("harness") != {name: digest(HERE / name) for name in ("run.py", "test_runner.py", "bundle.py")}
                or cold.get("compilation") != "pass" or cold.get("tools") != tools
                or cold.get("inputs") != current_inputs or cold.get("cache") != str(cache)):
            parser.error("cold receipt must describe a successful build with identical inputs and tools")
        try:
            recorded = cold.get("cache_inventory")
            if not isinstance(recorded, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for k, v in recorded.items()):
                parser.error("cold receipt has missing or malformed cache inventory")
            if cache_inventory(cache) != recorded:
                parser.error("cache integrity mismatch against successful cold inventory")
        except (OSError, ValueError) as error:
            parser.error(f"cache integrity check failed: {error}")
    if args.case in ("cold", "offline-empty") and cache.exists():
        parser.error("cold/empty-cache case refuses a preexisting cache")
    run.mkdir(parents=True)
    cache.mkdir(exist_ok=True)
    resource = work / "dependencies" / "bundle.zip"
    receipt = {
        **metadata,
        "environment_policy": POLICY,
        "timestamp": datetime.now(timezone.utc).isoformat(), "case": args.case,
        "platform": platform.platform(), "architecture": platform.machine(),
        "tools": tools, "bundle": dependency, "cache": str(cache),
        "inputs": fixture_inputs(),
        "harness": {name: digest(HERE / name) for name in ("run.py", "test_runner.py", "bundle.py")},
        "builds": [], "visual_review": "not_run", "status": "partial",
        "limitations": ["PDF inspection and font/bundle content identity require independent review",
                        "only-cached is an engine option, not an OS network sandbox"],
    }
    env = environment(run / "isolation", cache, args.tool_dir.resolve())
    receipt["environment"] = env
    failed = False
    try:
        resource.parent.mkdir(exist_ok=True)
        if not resource.exists():
            with args.bundle.open("rb") as source, resource.open("xb") as target:
                shutil.copyfileobj(source, target)
        bundle.verify(resource, args.bundle_lock)
        for kind in ("article", "slides"):
            project = run / kind
            shutil.copytree(HERE / kind, project, ignore=shutil.ignore_patterns('build'))
            manifest = project / "Tectonic.toml"
            local_path = Path(os.path.relpath(resource, project)).as_posix()
            contents, count = re.subn(r'(?m)^bundle = .+$', 'bundle = ' + json.dumps(local_path), manifest.read_text())
            if count != 1:
                raise ValueError("expected exactly one document bundle setting")
            manifest.write_text(contents)
            receipt.setdefault("realized_manifests", {})[kind] = digest(manifest)
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
    except Exception as error:
        receipt["status"] = "fail"
        receipt["compilation"] = "fail"
        receipt["diagnostic"] = str(error)
        raise
    finally:
        try:
            receipt["cache_inventory"] = cache_inventory(cache)
        except (OSError, ValueError) as error:
            failed = True
            receipt.update(cache_inventory=None, status="fail", compilation="fail",
                           cache_diagnostic=str(error))
        (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        attempt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + platform.machine() + "-" + args.case + "-" + uuid.uuid4().hex[:8]
        export_evidence(run, args.evidence_root.resolve() / attempt, {
            str(work): "<WORK>", str(args.tool_dir.resolve()): "<TOOLS>",
            str(HERE.parents[1]): "<REPOSITORY>", str(Path.home()): "<HOME>",
        })
    print(run / "receipt.json")
    # Expected failure is recorded as a failure, never relabelled a clean build.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

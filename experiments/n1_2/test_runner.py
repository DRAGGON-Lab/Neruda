"""Boundary checks; these do not substitute for real compiler validation."""
import contextlib
import io
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import run


class RunnerBoundaries(unittest.TestCase):
    def test_foreign_cache_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "foreign").mkdir()
            (root / "cache").symlink_to(root / "foreign", target_is_directory=True)
            with patch.object(run, "preflight", return_value={}):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    run.main(["--tool-dir", str(root), "--work-root", str(root), "--case", "warm"])
            self.assertFalse((root / "warm").exists())

    def test_arbitrary_pdfs_do_not_count_as_required_outputs(self):
        def fake_execute(argv, cwd=None, env=None):
            if Path(argv[0]).name != "git":
                (cwd / "arbitrary.pdf").write_bytes(b"not required output")
            return 0, ""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(run, "preflight", return_value={"tectonic": {"path": "mock"}}):
                with patch.object(run, "execute", side_effect=fake_execute):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = run.main(["--tool-dir", str(root), "--work-root", str(root), "--case", "cold", "--evidence-root", str(root / "evidence")])
            self.assertEqual(code, 1)

    def test_missing_tools_do_not_create_work_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with contextlib.redirect_stderr(io.StringIO()):
                code = run.main(["--tool-dir", str(root), "--work-root", str(root / "work"), "--case", "cold", "--evidence-root", str(root / "evidence")])
            self.assertEqual(code, 2)
            self.assertFalse((root / "work").exists())

    def test_version_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root / "tectonic"
            tool.touch()
            tool.chmod(0o755)
            with patch.object(run, "execute", return_value=(0, "Tectonic 0.17.01")):
                with self.assertRaisesRegex(ValueError, "version mismatch"):
                    run.preflight(root)

    def test_fixture_source_cannot_be_work_root(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                run.main(["--tool-dir", "/missing", "--work-root", str(run.HERE), "--case", "cold"])

    def test_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cold").mkdir()
            evidence = root / "cold" / "receipt.json"
            evidence.write_text("previous evidence")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    run.main(["--tool-dir", "/missing", "--work-root", str(root), "--case", "cold", "--evidence-root", str(root / "evidence")])
            self.assertEqual(evidence.read_text(), "previous evidence")


class RunnerExecution(unittest.TestCase):
    def invoke(self, root, case="cold", executor=None):
        with patch.object(run, "preflight", return_value={"tectonic": {"path": "/approved/tectonic"}}), patch.object(run, "execute", side_effect=executor or self.success), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return run.main(["--tool-dir", str(root / "tools"), "--work-root", str(root / "work"), "--case", case, "--evidence-root", str(root / "evidence")])

    @staticmethod
    def success(argv, cwd=None, env=None, **kwargs):
        if Path(argv[0]).name == "git":
            return 0, "test-revision"
        outputs = ("article",) if cwd.name == "article" else ("slides", "handout")
        for name in outputs:
            target = cwd / "build" / name / (name + ".pdf")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"synthetic test output; not a compiler result")
        return 0, "fixture completed"

    def test_success_and_warm_offline_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for case in ("cold", "warm", "offline"):
                self.assertEqual(self.invoke(root, case), 0)
                receipt = json.loads((root / "work" / case / "receipt.json").read_text())
                self.assertEqual(receipt["compilation"], "pass")
                self.assertEqual(receipt["status"], "partial")
                self.assertEqual(sum(len(b["pdfs"]) for b in receipt["builds"]), 3)
            self.assertEqual(len(list((root / "evidence").iterdir())), 3)

    def test_invalid_cold_receipts_refused_before_output(self):
        for field in ("compilation", "tools", "inputs", "cache", "harness", "bundle_url", "environment_policy", "malformed", "missing", "list"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.invoke(root)
                path = root / "work/cold/receipt.json"
                data = json.loads(path.read_text())
                if field == "missing":
                    path.unlink()
                else:
                    data[field] = "mismatch"
                    path.write_text("{" if field == "malformed" else "[]" if field == "list" else json.dumps(data))
                with self.assertRaises(SystemExit):
                    self.invoke(root, "warm")
                self.assertFalse((root / "work/warm").exists())

    def test_timeout_keeps_partial_output_and_receipt(self):
        for partial in (b"partial diagnostic", "partial diagnostic"):
            def timeout(argv, cwd=None, env=None):
                if Path(argv[0]).name == "git":
                    return 0, "test-revision"
                raise subprocess.TimeoutExpired(argv, 600, output=partial)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.assertEqual(self.invoke(root, executor=timeout), 1)
                receipt = json.loads((root / "work/cold/receipt.json").read_text())
                self.assertEqual([b["exit_code"] for b in receipt["builds"]], [124, 124])
                self.assertIn("partial diagnostic", (root / "work/cold/article.console.log").read_text())

    def test_execute_propagates_timeout(self):
        with patch.object(run.subprocess, "run", side_effect=subprocess.TimeoutExpired(["tool"], 1)) as child:
            with self.assertRaises(subprocess.TimeoutExpired):
                run.execute(["tool"], env={"PATH": "/isolated"}, timeout=1)
            self.assertEqual(child.call_args.kwargs["timeout"], 1)

    def test_environment_does_not_inherit_host_configuration(self):
        poison = {key: "host-secret" for key in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS", "PAR_TEMP", "PERL5OPT", "FONTCONFIG_FILE", "DYLD_LIBRARY_PATH", "TECTONIC_TEST_FAKE_BIBER")}
        with tempfile.TemporaryDirectory() as directory, patch.dict(run.os.environ, poison):
            root = Path(directory)
            env = run.environment(root, root / "cache", root / "tools")
            self.assertFalse(set(poison) & set(env))
            self.assertEqual(env["HOME"], str(root / "home"))
            self.assertIn("--noconf", (root / "bin/biber").read_text())

    def test_preflight_uses_isolation_for_both_version_probes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("tectonic", "biber"):
                (root / name).touch()
                (root / name).chmod(0o755)
            def probe(argv, cwd=None, env=None, timeout=None):
                self.assertNotIn("PERL5OPT", env)
                self.assertEqual(timeout, 60)
                self.assertEqual(Path(env["HOME"]).parent, cwd)
                return 0, "Tectonic 0.17.0" if Path(argv[0]).name == "tectonic" else "biber version: 2.17"
            with patch.dict(run.os.environ, {"PERL5OPT": "host-secret"}), patch.object(run, "execute", side_effect=probe) as child:
                self.assertEqual(set(run.preflight(root)), {"tectonic", "biber"})
                self.assertEqual(child.call_count, 2)

    def test_export_redacts_paths_and_preserves_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw"
            source.mkdir()
            (source / "receipt.json").write_text('{"path": "/private/person/tools"}')
            (source / "console.log").write_text("/private/person/tools: HTTP 429")
            (source / "binary").write_bytes(b"excluded")
            run.export_evidence(source, root / "public", {"/private/person": "<HOME>"})
            self.assertEqual((root / "public/console.log").read_text(), "<HOME>/tools: HTTP 429")
            self.assertFalse((root / "public/binary").exists())
            self.assertTrue((root / "public/manifest.json").exists())
            with self.assertRaises(FileExistsError):
                run.export_evidence(source, root / "public", {})


class IntegrityRegressions(unittest.TestCase):
    invoke = RunnerExecution.invoke
    success = staticmethod(RunnerExecution.success)
    def test_git_warning_is_separate_in_both_receipt_paths(self):
        def git(argv, **kwargs):
            self.assertEqual(kwargs["stderr"], subprocess.PIPE)
            return subprocess.CompletedProcess(argv, 0, "a" * 40 + "\n" if "rev-parse" in argv else " M fixture.tex\n", "git warning\n")
        for failed_preflight in (False, True):
            with self.subTest(failed_preflight=failed_preflight), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with patch.object(run.subprocess, "run", side_effect=git):
                    if failed_preflight:
                        with patch.object(run, "preflight", side_effect=ValueError("missing tools")), contextlib.redirect_stderr(io.StringIO()):
                            code = run.main(["--tool-dir", str(root / "tools"), "--work-root", str(root / "work"), "--case", "cold", "--evidence-root", str(root / "evidence")])
                        self.assertEqual(code, 2)
                    else:
                        self.assertEqual(self.invoke(root), 0)
                receipt = json.loads(next((root / "evidence").glob("*/receipt.json")).read_text())
                self.assertEqual(receipt["source_revision"], "a" * 40)
                self.assertEqual(receipt["dirty_state"], " M fixture.tex\n")
                self.assertEqual(receipt["git_diagnostics"]["source_revision"]["stderr"], "git warning\n")

    def test_invalid_git_metadata_refuses_compilation(self):
        failures = [subprocess.CompletedProcess([], 1, "a" * 40, "fatal"),
                    subprocess.CompletedProcess([], 0, "", ""),
                    subprocess.CompletedProcess([], 0, "warning\n" + "a" * 40, ""),
                    subprocess.CompletedProcess([], 0, "not-a-sha", ""),
                    FileNotFoundError("missing Git"), subprocess.TimeoutExpired(["git"], 60)]
        for failure in failures:
            with self.subTest(failure=str(failure)), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                with patch.object(run.subprocess, "run", side_effect=failure if isinstance(failure, Exception) else None, return_value=failure):
                    self.assertEqual(self.invoke(root), 2)
                receipt=json.loads(next((root / "evidence").glob("*/receipt.json")).read_text())
                self.assertIsNone(receipt["source_revision"])
                self.assertEqual(receipt["compilation"], "not_run")
                self.assertFalse((root / "work").exists())

    def test_cache_integrity_and_malformed_inventory_refused(self):
        for case in ("warm", "offline"):
            for change in ("added", "removed", "modified", "file-link", "directory-link", "missing-inventory", "malformed-inventory", "unreadable", "special"):
                with self.subTest(case=case, change=change), tempfile.TemporaryDirectory() as directory:
                    root=Path(directory)
                    self.assertEqual(self.invoke(root),0)
                    cache=root / "work/cache"; entry=cache / "fixture"
                    entry.write_bytes(b"original")
                    receipt_path=root / "work/cold/receipt.json"
                    receipt=json.loads(receipt_path.read_text());receipt["cache_inventory"]=run.cache_inventory(cache)
                    if change=="added": (cache / "extra").touch()
                    elif change=="removed": entry.unlink()
                    elif change=="modified": entry.write_bytes(b"modified")
                    elif change=="file-link": entry.unlink();entry.symlink_to(receipt_path)
                    elif change=="directory-link": (cache / "link").symlink_to(root, target_is_directory=True)
                    elif change=="missing-inventory": del receipt["cache_inventory"]
                    elif change=="malformed-inventory": receipt["cache_inventory"]={"fixture": "not-a-digest"}
                    if change=="special": run.os.mkfifo(cache / "fifo")
                    receipt_path.write_text(json.dumps(receipt))
                    executor=Mock(side_effect=self.success)
                    original_digest=run.digest
                    def unreadable(path):
                        if path.resolve() == entry.resolve(): raise PermissionError("unreadable")
                        return original_digest(path)
                    with patch.object(run, "digest", side_effect=unreadable) if change=="unreadable" else contextlib.nullcontext():
                        with self.assertRaises(SystemExit):
                            self.invoke(root,case,executor)
                    executor.assert_not_called()
                    self.assertFalse((root / "work" / case).exists())

    def test_populated_cache_reuse_and_warm_changes(self):
        for changed in (False, True):
          with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def populate(argv,cwd=None,env=None):
                (Path(env["TECTONIC_CACHE_DIR"]) / "fixture").write_bytes(b"original")
                return self.success(argv,cwd,env)
            self.assertEqual(self.invoke(root,executor=populate),0)
            def warm(argv,cwd=None,env=None):
                if changed: (Path(env["TECTONIC_CACHE_DIR"]) / "new").touch()
                return self.success(argv,cwd,env)
            self.assertEqual(self.invoke(root,"warm",warm),0)
            if changed:
                with self.assertRaises(SystemExit):self.invoke(root,"offline")
            else:
                self.assertEqual(self.invoke(root,"offline"),0)

    def test_failed_inventory_still_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(run,"cache_inventory",side_effect=PermissionError("unreadable cache")):
                self.assertEqual(self.invoke(root),1)
            receipt=json.loads((root / "work/cold/receipt.json").read_text())
            self.assertEqual(receipt["compilation"],"fail")
            self.assertIsNone(receipt["cache_inventory"])


if __name__ == "__main__":
    unittest.main()

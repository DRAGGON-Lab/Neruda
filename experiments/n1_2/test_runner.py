"""Boundary checks; these do not substitute for real compiler validation."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
            if argv[0] != "git":
                (cwd / "arbitrary.pdf").write_bytes(b"not required output")
            return 0, ""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(run, "preflight", return_value={"tectonic": {"path": "mock"}}):
                with patch.object(run, "execute", side_effect=fake_execute):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = run.main(["--tool-dir", str(root), "--work-root", str(root), "--case", "cold"])
            self.assertEqual(code, 1)

    def test_missing_tools_do_not_create_work_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with contextlib.redirect_stderr(io.StringIO()):
                code = run.main(["--tool-dir", str(root), "--work-root", str(root / "work"), "--case", "cold"])
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
                    run.main(["--tool-dir", "/missing", "--work-root", str(root), "--case", "cold"])
            self.assertEqual(evidence.read_text(), "previous evidence")


if __name__ == "__main__":
    unittest.main()

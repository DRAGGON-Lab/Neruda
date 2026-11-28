"""Behavioral coverage for the scaffold CLI and copy failure paths."""

from contextlib import redirect_stderr, redirect_stdout
import errno
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import scaffold


SHARED = {
    ".gitignore": "templates/common/.gitignore",
    "AGENTS.md": "templates/common/AGENTS.md",
    "LICENSE": "LICENSE",
    "scripts/latex.py": "scripts/latex.py",
    "tools/texlive-lock.json": "tools/texlive-lock.json",
    "src/neruda.sty": "tex/neruda.sty",
    "src/bib/references.bib": "templates/common/src/bib/references.bib",
}
ARTICLE = (
    "README.md", "figures/source/build.py", "figures/source/scaling.json",
    "src/main.tex", "src/metadata.tex", "src/sections/introduction.tex",
    "src/sections/mathematical-concepts.tex", "src/sections/reproducibility.tex",
)
SLIDES = (
    "README.md", "src/main.tex", "src/handout.tex", "src/presentation.tex", "src/metadata.tex",
    "src/frames/mapping.tex", "src/frames/check.tex", "src/frames/documentation.tex",
)
EXPECTED = {
    "article": SHARED | {name: f"templates/article/{name}" for name in ARTICLE}
    | {"src/neruda-article.sty": "tex/neruda-article.sty"},
    "slides": SHARED | {name: f"templates/slides/{name}" for name in SLIDES}
    | {"src/beamerthemeNeruda.sty": "tex/beamerthemeNeruda.sty"},
}


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.parent = self.base / "parent with spaces"
        self.parent.mkdir()
        self.sentinel = self.parent / "existing.txt"
        self.sentinel.write_bytes(b"keep this")
        self.root = self.base / "bundle"
        for sources in EXPECTED.values():
            for source in sources.values():
                path = self.root / source
                path.parent.mkdir(exist_ok=True, parents=True)
                path.write_text(source)
        (self.root / "templates/article/extra.tex").write_text("not bundled")
        self.cli = self.root / "scripts/scaffold.py"
        shutil.copyfile(scaffold.__file__, self.cli)

    def args(self, profile="article", name="example", parent=None):
        return [profile, name, "--parent", str(self.parent if parent is None else parent)]

    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(self.cli), *args],
                              capture_output=True, text=True, cwd=cwd)

    def assert_inventory(self, destination, profile, root):
        files = {path.relative_to(destination).as_posix(): path.read_bytes()
                 for path in destination.rglob("*") if path.is_file()}
        expected = {name: (root / source).read_bytes()
                    for name, source in EXPECTED[profile].items()}
        self.assertEqual(files, expected)

    def assert_parent_intact(self, *expected):
        self.assertEqual(set(self.parent.iterdir()), {self.sentinel, *expected})
        self.assertEqual(self.sentinel.read_bytes(), b"keep this")

    def test_both_profiles_and_paths_with_spaces(self):
        for profile in EXPECTED:
            with self.subTest(profile=profile):
                destination = self.parent / profile
                result = self.run_cli(*self.args(profile, profile, self.parent.name), cwd=self.base)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"{destination}\n")
                self.assert_inventory(destination, profile, self.root)

    def test_repository_bundles_are_complete_and_standalone(self):
        root = Path(scaffold.__file__).resolve().parents[1]
        for profile in EXPECTED:
            with self.subTest(profile=profile):
                result = subprocess.run(
                    [sys.executable, str(root / "scripts/scaffold.py"),
                     *self.args(profile, profile)],
                    capture_output=True, text=True, cwd=self.base,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_inventory(self.parent / profile, profile, root)

    def test_article_figure_is_generated_explicitly_and_repeatably(self):
        root = Path(scaffold.__file__).resolve().parents[1]
        self.assertEqual(scaffold.main(self.args(), root=root), 0)
        project = self.parent / "example"
        generated = project / "src/figures/generated"
        self.assertFalse(generated.exists())
        results = []
        for _ in range(2):
            result = subprocess.run([sys.executable, "figures/source/build.py"], cwd=project,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            results.append({path.name: path.read_bytes() for path in generated.iterdir()})
        self.assertEqual(results[0], results[1])
        self.assertTrue(results[0]["coordinate-scaling.png"].startswith(b"\x89PNG\r\n\x1a\n"))

    def test_invalid_names_and_traversal(self):
        for name in ("", "Upper", "under_score", "naïve", "a--b", "-foo", "foo-", "a/b",
                     "..", "../escape", str(self.base / "escape"), "with space", "line\nbreak"):
            with self.subTest(name=name):
                self.assertEqual(self.run_cli(*self.args(name=name)).returncode, 2)
        for parent in ("", str(self.parent) + "/../" + self.parent.name,
                       self.base / "missing", self.sentinel):
            with self.subTest(parent=parent):
                self.assertEqual(self.run_cli(*self.args(parent=parent)).returncode, 2)
        self.assertFalse((self.base / "escape").exists())
        self.assert_parent_intact()

    def test_symlink_parent_and_intermediate_component(self):
        link = self.base / "link"
        link.symlink_to(self.parent, target_is_directory=True)
        inner = self.parent / "inner"
        inner.mkdir()
        for parent in (link, link / inner.name):
            self.assertEqual(self.run_cli(*self.args(parent=parent)).returncode, 2)
        self.assertEqual(list(inner.iterdir()), [])
        self.assert_parent_intact(inner)

    def test_all_existing_destinations_are_refused(self):
        empty = self.parent / "empty"
        empty.mkdir()
        existing = self.parent / "in-use"
        existing.mkdir()
        existing_file = existing / "data.txt"
        existing_file.write_text("keep this too")
        dangling = self.parent / "dangling"
        dangling.symlink_to(self.base / "does-not-exist")
        link = self.parent / "linked"
        link.symlink_to(existing, target_is_directory=True)
        for destination in (empty, existing, dangling, link, self.sentinel):
            with self.subTest(destination=destination):
                self.assertEqual(self.run_cli(*self.args(name=destination.name)).returncode, 2)
        self.assertEqual(list(empty.iterdir()), [])
        self.assertEqual(existing_file.read_text(), "keep this too")
        self.assertEqual(dangling.readlink(), self.base / "does-not-exist")
        self.assertEqual(link.readlink(), existing)
        self.assert_parent_intact(empty, existing, dangling, link)

    def test_simultaneous_invocations_reserve_once(self):
        command = [sys.executable, str(self.cli), *self.args()]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as first:
            second = subprocess.run(command, capture_output=True)
            first.communicate(timeout=20)
        self.assertEqual(sorted((first.returncode, second.returncode)), [0, 2])
        destination = self.parent / "example"
        self.assert_inventory(destination, "article", self.root)
        self.assert_parent_intact(destination)

    def test_invalid_bundled_sources_are_rejected_before_reservation(self):
        asset = self.root / "tex/neruda-article.sty"
        asset.unlink()
        result = self.run_cli(*self.args())
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("invalid bundled source tex/neruda-article.sty", result.stderr)
        self.assert_parent_intact()
        asset.symlink_to(self.sentinel)
        result = self.run_cli(*self.args())
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assert_parent_intact()
        asset.unlink()
        os.mkfifo(asset)
        result = self.run_cli(*self.args())
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assert_parent_intact()

    def failing_copy(self, exception, keep_foreign=False):
        destination = self.parent / "example"
        real_write = scaffold.write_file

        def write(descriptor, contents):
            if contents == b"templates/article/src/sections/mathematical-concepts.tex":
                os.write(descriptor, b"partial bytes")
                if keep_foreign:
                    (destination / "foreign.txt").write_bytes(b"keep foreign")
                raise exception
            real_write(descriptor, contents)

        stderr = io.StringIO()
        with patch.object(scaffold, "write_file", write), redirect_stderr(stderr), redirect_stdout(io.StringIO()):
            self.assertEqual(scaffold.main(self.args(), root=self.root), 1)
        return destination, stderr.getvalue()

    def test_interrupted_copy_removes_its_files_and_directories(self):
        for error in (KeyboardInterrupt(), OSError(errno.ENOSPC, "disk full")):
            with self.subTest(error=type(error).__name__):
                _, message = self.failing_copy(error)
                self.assertNotIn("partial output", message)
                self.assert_parent_intact()

    def test_copy_failure_preserves_foreign_file_and_reports_partial_path(self):
        destination, message = self.failing_copy(OSError(errno.EIO, "copy failed"), keep_foreign=True)
        self.assertIn(f"partial output may remain at {destination}", message)
        self.assertEqual(list(destination.iterdir()), [destination / "foreign.txt"])
        self.assertEqual((destination / "foreign.txt").read_bytes(), b"keep foreign")
        self.assert_parent_intact(destination)

    def test_symlink_swapped_in_after_reservation_is_preserved(self):
        destination = self.parent / "example"
        foreign = self.base / "foreign"
        foreign.mkdir()
        real_mkdir = os.mkdir

        def swap(name, mode=0o777, *, dir_fd=None):
            real_mkdir(name, mode=mode, dir_fd=dir_fd)
            if name == destination.name:
                destination.rmdir()
                destination.symlink_to(foreign, target_is_directory=True)

        stderr = io.StringIO()
        with patch.object(scaffold.os, "mkdir", swap), redirect_stderr(stderr):
            self.assertEqual(scaffold.main(self.args(), root=self.root), 1)
        self.assertIn(f"partial output may remain at {destination}", stderr.getvalue())
        self.assertEqual(destination.readlink(), foreign)
        self.assertEqual(list(foreign.iterdir()), [])
        self.assert_parent_intact(destination)

"""Linux archive verification tests use synthetic bytes, never execute binaries."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

import linux_ci
import run


class ArchiveVerification(unittest.TestCase):
    def fixture(self, root, name="biber", symlink=False, extra=False):
        archive = root / "source.tar.gz"
        data = b"\x7fELF\x02\x01" + bytes(12) + (62).to_bytes(2, "little")
        with tarfile.open(archive, "w:gz") as target:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            if symlink:
                member.type = tarfile.SYMTYPE
                member.linkname = "/outside"
            target.addfile(member, None if symlink else io.BytesIO(data))
            if extra:
                target.addfile(tarfile.TarInfo("extra"))
        destination = root / "bin"
        destination.mkdir()
        return archive, destination, data

    def test_valid_single_native_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, destination, data = self.fixture(Path(directory))
            linux_ci.extract(archive, destination, "biber", run.digest(archive))
            self.assertEqual((destination / "biber").read_bytes(), data)
            self.assertTrue((destination / "biber").stat().st_mode & 0o111)
            with self.assertRaises(FileExistsError):
                linux_ci.extract(archive, destination, "biber", run.digest(archive))

    def test_checksum_mismatch_never_extracts(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, destination, _ = self.fixture(Path(directory))
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                linux_ci.extract(archive, destination, "biber", "0" * 64)
            self.assertEqual(list(destination.iterdir()), [])

    def test_traversal_links_and_extra_members_refused(self):
        for kwargs in ({"name": "../biber"}, {"symlink": True}, {"extra": True}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as directory:
                archive, destination, _ = self.fixture(Path(directory), **kwargs)
                with self.assertRaisesRegex(ValueError, "archive members"):
                    linux_ci.extract(archive, destination, "biber", run.digest(archive))
                self.assertEqual(list(destination.iterdir()), [])

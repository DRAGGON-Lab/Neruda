import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import texlive_linux_ci as ci


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, member):
        path = self.root / 'installer.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            if member.isfile():
                member.size = 4
                archive.addfile(member, io.BytesIO(b'test'))
            else:
                archive.addfile(member)
        return path

    def test_valid_installer_archive_is_extracted_to_new_directory(self):
        archive = self.archive(tarfile.TarInfo('install-tl-20260322/install-tl'))
        ci.extract_installer(archive, self.root / 'unpacked')
        self.assertEqual((self.root / 'unpacked/install-tl-20260322/install-tl').read_bytes(), b'test')

    def test_traversal_and_symlinks_are_refused_before_extraction(self):
        for name, kind in [('../outside', tarfile.REGTYPE), ('/outside', tarfile.REGTYPE),
                           ('linked', tarfile.SYMTYPE)]:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.linkname = '/outside'
            with self.subTest(name=name), self.assertRaises(ValueError):
                ci.extract_installer(self.archive(member), self.root / 'unpacked')
            self.assertFalse((self.root / 'unpacked').exists())

    def test_incomplete_archive_is_not_accepted(self):
        path = self.root / 'incomplete.tar.gz'
        path.write_bytes(b'not a complete archive')
        with self.assertRaises(tarfile.TarError):
            ci.extract_installer(path, self.root / 'unpacked')
        self.assertFalse((self.root / 'unpacked').exists())

    def test_unsigned_or_wrong_key_metadata_is_refused(self):
        with patch.object(ci, 'execute', return_value='[GNUPG:] GOODSIG example\n'):
            with self.assertRaisesRegex(ValueError, 'pinned primary key'):
                ci.verify_signature(Path('sig'), Path('hash'), Path('keys'), 'EXPECTED', {}, self.root / 'log')
        with patch.object(ci, 'execute', return_value='[GNUPG:] VALIDSIG WRONG 2026 ... WRONG\n'):
            with self.assertRaises(ValueError):
                ci.verify_signature(Path('sig'), Path('hash'), Path('keys'), 'EXPECTED', {}, self.root / 'log')

    def test_pinned_primary_key_signature_is_accepted(self):
        with patch.object(ci, 'execute', return_value='[GNUPG:] VALIDSIG SUBKEY 2026 ... EXPECTED\n'):
            ci.verify_signature(Path('sig'), Path('hash'), Path('keys'), 'EXPECTED', {}, self.root / 'log')

    def test_download_size_limit_preserves_partial_evidence(self):
        with patch.object(ci.urllib.request, 'urlopen', return_value=io.BytesIO(b'too much data')):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                ci.download('https://example.invalid/fixture', self.root / 'download', 2)
        self.assertFalse((self.root / 'download').exists())
        self.assertTrue((self.root / 'download.attempt-0').exists())

    def test_html_success_response_is_refused_and_identity_is_preserved(self):
        body = b'<!doctype html><html><title>Oh noes!</title></html>'
        with patch.object(ci.urllib.request, 'urlopen', return_value=io.BytesIO(body)):
            with self.assertRaisesRegex(ValueError, 'returned HTML instead of an artifact'):
                ci.download('https://example.invalid/signature', self.root / 'signature.asc', 4096)
        self.assertEqual((self.root / 'signature.asc').read_bytes(), body)
        record = json.loads((self.root / 'signature.asc.download.json').read_text())
        self.assertEqual(record['bytes'], len(body))
        self.assertEqual(record['sha256'], ci.latex.digest(self.root / 'signature.asc'))

    def test_artifact_download_preserves_exact_bytes_and_identity(self):
        body = b'-----BEGIN PGP SIGNATURE-----\nfixture'
        with patch.object(ci.urllib.request, 'urlopen', return_value=io.BytesIO(body)):
            ci.download('https://example.invalid/signature', self.root / 'signature.asc', 4096)
        self.assertEqual((self.root / 'signature.asc').read_bytes(), body)
        self.assertTrue((self.root / 'signature.asc.download.json').is_file())

    def test_failed_command_keeps_log_and_nonzero_diagnostic(self):
        log = self.root / 'console.log'
        def execute(*args):
            log.write_text('primary compiler diagnostic')
            return 7
        with patch.object(ci.latex, 'execute', side_effect=execute):
            with self.assertRaisesRegex(ValueError, 'exited 7: primary compiler diagnostic'):
                ci.execute(['fixture'], {}, log)
        self.assertEqual(log.read_text(), 'primary compiler diagnostic')

    def test_export_redacts_paths_and_keeps_pdf_bytes(self):
        (self.root / 'failed.log').write_text(str(self.root) + ': failure')
        run = self.root / 'matrix/article/build/run'
        run.mkdir(parents=True)
        (run / 'main.pdf').write_bytes(b'synthetic PDF bytes')
        public = ci.public_export(self.root)
        self.assertEqual((public / 'failed.log').read_text(), '<CI_WORK>: failure')
        self.assertEqual((public / 'runs/article/run/main.pdf').read_bytes(), b'synthetic PDF bytes')
        self.assertIn('failed.log', json.loads((public / 'manifest.json').read_text()))

    def test_wrapped_tex_and_json_paths_are_redacted(self):
        prefix = '/private/example-user-directory'
        text = '/private/example-\nuser-directory/file.log'
        encoded = '/private/example-\\nuser-directory/file.log'
        for value in (text, encoded):
            self.assertEqual(ci.sanitize_text(value, {prefix: '<PRIVATE>'}), '<PRIVATE>/file.log')

"""Local resource selection and integrity behavior without external dependencies."""
import json
from pathlib import Path
import tempfile
import unittest

import bundle
import run
import test_runner


class BundleTests(unittest.TestCase):
    def test_invalid_dependencies_refuse_before_compiler(self):
        for change in ('missing', 'checksum', 'truncated', 'fingerprint'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);test_runner.local_bundle(root)
                path=root/'bundle.zip';lock=root/'bundle.lock.json'
                if change=='missing':path.unlink()
                elif change=='checksum':path.write_bytes(b'changed')
                elif change=='truncated':
                    path.write_bytes(b'PK');data=json.loads(lock.read_text());data['sha256']=bundle.sha256(path);lock.write_text(json.dumps(data))
                else:
                    data=json.loads(lock.read_text());data['content_fingerprint']='b'*64;lock.write_text(json.dumps(data))
                with self.assertRaises((ValueError,OSError)):bundle.verify(path,lock)

    def test_manifest_binds_only_local_resource_and_offline_empty_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def compile(argv,cwd=None,env=None):
                manifest=(cwd/'Tectonic.toml').read_text()
                self.assertNotIn('https://',manifest)
                self.assertIn('../../dependencies/bundle.zip',manifest)
                return test_runner.RunnerExecution.success(argv,cwd,env)
            harness=test_runner.RunnerExecution()
            self.assertEqual(harness.invoke(root,'offline-empty',compile),0)
            receipt=json.loads((root/'work/offline-empty/receipt.json').read_text())
            self.assertEqual(receipt['bundle']['sha256'],bundle.sha256(root/'bundle.zip'))
            self.assertEqual(receipt['compilation'],'pass')

    def test_missing_bundle_never_uses_remote(self):
        with self.assertRaisesRegex(ValueError,'remote fallback is disabled'):
            bundle.verify(None,None)

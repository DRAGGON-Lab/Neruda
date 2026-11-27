import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import bundle
import pack_bundle


class PackagingTests(unittest.TestCase):
    def test_verified_source_produces_byte_preserving_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'bundle.tar';lock=root/'source.json'
            with tarfile.open(source,'w') as archive:
                for name,data in [('SHA256SUM',b'a'*64),('test.tex',b'synthetic fixture')]:
                    info=tarfile.TarInfo(name);info.size=len(data);archive.addfile(info,io.BytesIO(data))
            lock.write_text(json.dumps({'version':bundle.VERSION,'archive_sha256':bundle.sha256(source),'content_fingerprint':'a'*64,'verification_reference':'synthetic test only'}))
            result=pack_bundle.pack(source,lock,root/'candidate')
            self.assertIn('test.tex',result['files'])
            runtime=root/'runtime.json';runtime.write_text(json.dumps({'version':bundle.VERSION,'sha256':result['zip_sha256'],'content_fingerprint':'a'*64,'verification_reference':'synthetic test only'}))
            bundle.verify(root/'candidate/bundle.zip',runtime)

    def test_source_verification_failure_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'bad.tar';source.write_bytes(b'bad')
            lock=root/'lock.json';lock.write_text(json.dumps({'version':bundle.VERSION,'archive_sha256':'0'*64,'content_fingerprint':'a'*64,'verification_reference':'synthetic'}))
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                pack_bundle.pack(source,lock,root/'candidate')
            self.assertFalse((root/'candidate').exists())

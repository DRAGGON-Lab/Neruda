"""Prepare a ZIP candidate from independently verified official archive bytes.

This never publishes artifacts or generates an approved runtime lock.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile

import bundle


def pack(archive, source_lock, destination):
    lock = json.loads(source_lock.read_text())
    for key in ('archive_sha256', 'content_fingerprint'):
        if not isinstance(lock.get(key), str) or not re.fullmatch('[0-9a-f]{64}', lock[key]):
            raise ValueError('reviewed source checksum and fingerprint are required')
    if lock.get('version') != bundle.VERSION or not lock.get('verification_reference'):
        raise ValueError('independent source verification reference required')
    if bundle.sha256(archive) != lock['archive_sha256']:
        raise ValueError('source archive checksum mismatch')
    destination.mkdir(parents=True, exist_ok=False)
    inventory = {}
    fingerprint = None
    with tarfile.open(archive, 'r|*') as source, zipfile.ZipFile(destination/'bundle.zip', 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for member in source:
            name = PurePosixPath(member.name)
            if not member.isfile() or len(name.parts) != 1 or name.is_absolute() or member.name in inventory or member.name in ('.','..') or '\\' in member.name:
                raise ValueError('unsafe or ambiguous source bundle member')
            info = zipfile.ZipInfo(member.name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100444 << 16
            value = hashlib.sha256()
            with source.extractfile(member) as stream, target.open(info, 'w', force_zip64=True) as output:
                data = stream.read(1024*1024)
                while data:
                    value.update(data)
                    output.write(data)
                    if member.name == 'SHA256SUM':
                        if fingerprint is not None or len(data) > 128:
                            raise ValueError('invalid internal fingerprint')
                        fingerprint = data.decode().strip()
                    data = stream.read(1024*1024)
            inventory[member.name] = value.hexdigest()
    if fingerprint != lock['content_fingerprint']:
        raise ValueError('source content fingerprint mismatch')
    receipt = {'status':'candidate: runtime lock requires separate review', 'source':lock,
               'zip_sha256':bundle.sha256(destination/'bundle.zip'), 'files':inventory}
    (destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--source-lock', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args=parser.parse_args()
    pack(args.archive,args.source_lock,args.destination)

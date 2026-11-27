"""Verified local ZIP resources; acquisition never grants permission to use bytes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

VERSION = 'tlextras-2022.0r0'


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def verify(path, lock_path):
    if path is None or lock_path is None:
        raise ValueError('local bundle and reviewed bundle lock are required; remote fallback is disabled')
    path, lock_path = Path(path), Path(lock_path)
    if path.is_symlink() or not path.is_file() or path.suffix != '.zip':
        raise ValueError('required local ZIP bundle is unavailable')
    lock = json.loads(lock_path.read_text())
    if not isinstance(lock, dict):
        raise ValueError('invalid bundle lock')
    if lock.get('version') != VERSION or not lock.get('verification_reference'):
        raise ValueError('bundle lock needs reviewed version and verification provenance')
    for key in ('sha256', 'content_fingerprint'):
        if not isinstance(lock.get(key), str) or not re.fullmatch('[0-9a-f]{64}', lock[key]):
            raise ValueError('invalid bundle lock digest')
    if sha256(path) != lock['sha256']:
        raise ValueError('local bundle checksum mismatch')
    try:
        with zipfile.ZipFile(path) as archive:
            names = set()
            for member in archive.infolist():
                name = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                if (member.flag_bits & 1 or name.is_absolute() or '..' in name.parts or '\\' in member.filename
                        or member.filename in names or stat.S_ISLNK(mode)):
                    raise ValueError('unsafe or duplicate bundle member')
                names.add(member.filename)
            if archive.testzip() is not None:
                raise ValueError('corrupt ZIP bundle')
            if archive.read('SHA256SUM').decode().strip() != lock['content_fingerprint']:
                raise ValueError('bundle content fingerprint mismatch')
    except (zipfile.BadZipFile, KeyError, UnicodeError) as error:
        raise ValueError(f'invalid local bundle: {error}') from error
    return {key: lock[key] for key in ('version', 'sha256', 'content_fingerprint', 'verification_reference')}

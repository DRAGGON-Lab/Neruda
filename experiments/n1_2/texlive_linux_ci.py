"""Candidate Linux provisioning. Execution requires review of the CI procedure."""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import latex


def sha512(path):
    result = hashlib.sha512()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def download(url, destination, maximum):
    """Bounded retries retain failed partial downloads without overwriting them."""
    for attempt in range(3):
        candidate = destination.with_name(destination.name + f'.attempt-{attempt}')
        try:
            with urllib.request.urlopen(url, timeout=60) as response, candidate.open('xb') as target:
                content_type = response.headers.get('Content-Type', '') if hasattr(response, 'headers') else ''
                length = 0
                while True:
                    block = response.read(1048576)
                    if not block:
                        break
                    length += len(block)
                    if length > maximum:
                        raise ValueError('download exceeds reviewed size limit')
                    target.write(block)
            if destination.exists():
                raise ValueError('download destination already exists')
            candidate.rename(destination)
            metadata = {'url': url, 'bytes': length, 'sha256': latex.digest(destination),
                        'content_type': content_type, 'attempt': attempt}
            destination.with_name(destination.name + '.download.json').write_text(
                json.dumps(metadata, indent=2) + '\n')
            with destination.open('rb') as downloaded:
                prefix = downloaded.read(512).lstrip().lower()
            if 'text/html' in content_type.lower() or prefix.startswith((b'<!doctype html', b'<html')):
                raise ValueError('dependency endpoint returned HTML instead of an artifact: ' + url +
                                 '; possible access challenge; raw response and download identity retained; '
                                 'no installer was executed')
            return
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def execute(command, env, log, timeout=120, cwd=None):
    code = latex.execute(command, cwd, env, log, timeout)
    output = log.read_text(errors='replace')
    if code:
        raise ValueError(f'{command[0]} exited {code}: {output[-2000:]}')
    return output


def verify_signature(signature, checksum, key_home, fingerprint, env, log):
    output = execute(['/usr/bin/gpg', '--batch', '--no-options', '--homedir', str(key_home),
                      '--status-fd', '1', '--verify', str(signature), str(checksum)], env, log)
    if not any(line.startswith('[GNUPG:] VALIDSIG ') and line.split()[-1] == fingerprint
               for line in output.splitlines()):
        raise ValueError('signature did not validate against the pinned primary key')


def extract_installer(archive_path, destination):
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive.getmembers():
            relative = Path(member.name)
            if (relative.is_absolute() or '..' in relative.parts
                    or not (member.isfile() or member.isdir())):
                raise ValueError('unsafe installer archive member')
            member.mode &= 0o755
        destination.mkdir(exist_ok=False)
        archive.extractall(destination)


def sanitize_text(text, replacements):
    """TeX can wrap a path mid-component; JSON can escape that line break."""
    separator = r'(?:\r?\n[ \t]*|\\n[ \t]*|\\r)*'
    for source, token in sorted(replacements.items(), key=lambda item: -len(item[0])):
        pattern = separator.join(re.escape(character) for character in source)
        text = re.sub(pattern, lambda match: token, text)
    return text


def public_export(root):
    """Only public synthetic outputs/logs; never upload installers or caches."""
    public = root / 'public'
    public.mkdir(exist_ok=True)
    replacements = {str(root): '<CI_WORK>', str(REPO): '<NERUDA>', str(Path.home()): '<USER_HOME>'}
    replacements[str(Path(tempfile.gettempdir()).resolve())] = '<TEMP_ROOT>'
    candidates = list(root.glob('*.log')) + list(root.glob('*.json'))
    matrix = root / 'matrix'
    if not matrix.exists() and (root / 'summary.json').exists():
        matrix = root
    if matrix.exists():
        candidates += list(matrix.glob('*.console.log'))
        candidates += list(matrix.glob('summary.json'))
        for profile in ('article', 'slides', 'handout'):
            for directory in (matrix / profile / 'build').glob('*'):
                candidates += [p for p in directory.iterdir() if p.is_file() and
                               (p.suffix in ('.pdf', '.log', '.blg', '.fls') or p.name == 'receipt.json')]
    manifest = {}
    for source in candidates:
        if source.is_symlink():
            raise ValueError('evidence symlink refused')
        relative = source.relative_to(root)
        if source.is_relative_to(matrix) and 'build' in source.relative_to(matrix).parts:
            parts = source.relative_to(matrix).parts
            relative = Path('runs', parts[0], *parts[2:])
        target = public / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.pdf':
            shutil.copyfile(source, target)
        else:
            text = sanitize_text(source.read_text(errors='replace'), replacements)
            target.write_text(text)
        manifest[str(relative)] = {'raw_sha256': latex.digest(source), 'export_sha256': latex.digest(target)}
    (public / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return public


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(argv)
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('requires a fresh Linux x86_64 runner; no host repair is performed')
    root = args.root.resolve()
    if '\n' in str(root) or '\r' in str(root):
        parser.error('newline in provisioning path')
    root.mkdir(parents=True, exist_ok=False)
    source = json.loads((REPO / 'tools/texlive-linux-source.json').read_text())
    reference_path = REPO / 'tools/texlive-lock.json'
    record = {'status': 'fail', 'phase': 'preflight', 'compilation': 'not_run',
              'harness_sha256': latex.digest(Path(__file__)), 'platform': platform.platform(),
              'libc': platform.libc_ver(),
              'image_os': os.environ.get('ImageOS'), 'image_version': os.environ.get('ImageVersion')}
    exit_code = 1
    bootstrap = root / 'bootstrap'
    bootstrap.mkdir()
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(bootstrap), 'TMPDIR': str(bootstrap),
           'LC_ALL': 'C', 'LANG': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '1786060800'}
    try:
        if latex.digest(reference_path) != source['native_lock_sha256']:
            raise ValueError('native reference lock changed without source-pin review')
        if shutil.disk_usage(root).free < 10 * 1024 ** 3:
            raise ValueError('at least 10 GiB free space required; nothing is deleted automatically')
        if not Path('/usr/bin/gpg').is_file():
            raise ValueError('runner lacks gpg; no unsigned provisioning is allowed')
        execute(['/usr/bin/gpg', '--version'], env, root / 'gpg-version.log')
        record['phase'] = 'verify signing key'
        key = root / 'texlive.asc'
        download(source['key_url'], key, 100000)
        if latex.digest(key) != source['key_sha256']:
            raise ValueError('signing-key file checksum mismatch')
        key_home = root / 'gnupg'
        key_home.mkdir(mode=0o700)
        execute(['/usr/bin/gpg', '--batch', '--no-options', '--homedir', str(key_home),
                 '--import', str(key)], env, root / 'key-import.log')
        record['phase'] = 'verify installer and repository metadata'
        repository = source['repository']
        for name in ('install-tl-unx.tar.gz.sha512', 'install-tl-unx.tar.gz.sha512.asc',
                     'tlpkg/texlive.tlpdb.sha512', 'tlpkg/texlive.tlpdb.sha512.asc'):
            download(repository + '/' + name, root / name.replace('/', '-'), 4096)
        verify_signature(root / 'install-tl-unx.tar.gz.sha512.asc', root / 'install-tl-unx.tar.gz.sha512',
                         key_home, source['primary_fingerprint'], env, root / 'installer-signature.log')
        verify_signature(root / 'tlpkg-texlive.tlpdb.sha512.asc', root / 'tlpkg-texlive.tlpdb.sha512',
                         key_home, source['primary_fingerprint'], env, root / 'database-signature.log')
        for filename, expected in [('install-tl-unx.tar.gz.sha512', source['installer_sha512']),
                                   ('tlpkg-texlive.tlpdb.sha512', source['database_sha512'])]:
            if (root / filename).read_text().split()[0] != expected:
                raise ValueError('signed checksum differs from reviewed pin: ' + filename)
        database = root / 'texlive.tlpdb.xz'
        download(repository + '/tlpkg/texlive.tlpdb.xz', database, 6000000)
        if latex.digest(database) != source['database_xz_sha256']:
            raise ValueError('repository snapshot changed')
        if hashlib.sha512(lzma.decompress(database.read_bytes())).hexdigest() != source['database_sha512']:
            raise ValueError('decompressed metadata checksum mismatch')
        installer = root / 'install-tl-unx.tar.gz'
        download(repository + '/install-tl-unx.tar.gz', installer, 12000000)
        if sha512(installer) != source['installer_sha512'] or latex.digest(installer) != source['installer_sha256']:
            raise ValueError('installer archive integrity mismatch')
        record['signatures'] = 'verified against pinned TeX Live primary key'
        record['source'] = source
        extract_installer(installer, root / 'installer')
        entry = root / 'installer/install-tl-20260322/install-tl'
        if not entry.is_file():
            raise ValueError('unexpected installer layout')
        profile = root / 'texlive.profile'
        profile.write_text((REPO / 'tools/texlive-ci.profile').read_text().replace('@ROOT@', str(root)))
        record['phase'] = 'install isolated dated distribution'
        command = ['/usr/bin/perl', str(entry), '--repository', repository, '--profile', str(profile),
                   '--no-interaction', '--verify-downloads']
        record['provisioning_command'] = command
        execute(command, env, root / 'installer.log', timeout=2400, cwd=root)
        installation = root / 'installation'
        reference = json.loads(reference_path.read_text())
        record['phase'] = 'verify shared resources and versions'
        mismatches = [name for name, expected in reference['files'].items()
                      if name.startswith('texmf-dist/') and
                      (not (installation / name).is_file() or latex.digest(installation / name) != expected)]
        if mismatches:
            record['resource_mismatches'] = mismatches
            raise ValueError('shared resources differ from native MacTeX: ' + ', '.join(mismatches[:10]))
        tools = {name: 'bin/x86_64-linux/' + name for name in ('lualatex', 'latexmk', 'biber')}
        probe_env = latex.environment(installation, root / 'probe-state', installation / 'bin/x86_64-linux')
        observed = {}
        expected_first_lines = {
            'lualatex': 'This is LuaHBTeX, Version 1.24.0 (TeX Live 2026)',
            'latexmk': 'Latexmk, John Collins, 9 March 2026. Version 4.88',
            'biber': 'biber version: 2.21',
        }
        for name, flags in [('lualatex', ['--version']), ('latexmk', ['-v']),
                            ('biber', ['--noconf', '--version'])]:
            output = execute([str(installation / tools[name]), *flags], probe_env,
                             root / (name + '-version.log'))
            if not output.strip().splitlines() or output.strip().splitlines()[0] != expected_first_lines[name]:
                raise ValueError('version mismatch: ' + name)
            observed[name] = output.strip()
        if latex.digest(installation / tools['latexmk']) != reference['files'][reference['tools']['latexmk']]:
            raise ValueError('latexmk source differs from the native reference')
        record['versions'] = observed
        files = {name: expected for name, expected in reference['files'].items() if name.startswith('texmf-dist/')}
        for name in list(tools.values()) + ['tlpkg/texlive.tlpdb', 'texmf.cnf']:
            files[name] = latex.digest(installation / name)
        for name in ('texmf-var/web2c', 'texmf-var/fonts/map'):
            for path in (installation / name).rglob('*'):
                if path.is_file():
                    files[str(path.relative_to(installation))] = latex.digest(path)
        lock = {key: reference[key] for key in ('policy', 'versions')}
        lock.update(release='texlive-20260322', architecture='x86_64', tools=tools, files=files,
                    media={'repository': repository, 'database_sha512': source['database_sha512']},
                    verification_reference='provisioning.json and pinned official-key verification logs')
        lock_path = root / 'candidate-linux-lock.json'
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + '\n')
        record['phase'] = 'compile cache/network matrix'
        record['compilation'] = 'attempted'
        execute([sys.executable, str(HERE / 'texlive_matrix.py'), '--root', str(root / 'matrix'),
                 '--tex-root', str(installation), '--lock', str(lock_path)],
                env, root / 'matrix.log', timeout=900)
        record.update(status='pass', phase='completed', compilation='pass')
        exit_code = 0
    except (ValueError, OSError, subprocess.TimeoutExpired, tarfile.TarError, lzma.LZMAError) as error:
        record['error'] = str(error)
        print(f"N1.2 {record['phase']}: {error}", file=sys.stderr)
    finally:
        (root / 'provisioning.json').write_text(json.dumps(record, indent=2) + '\n')
        public_export(root)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
                summary.write(f"## TeX Live Linux compatibility: {record['status']}\n\n")
                summary.write(f"Phase: {record['phase']}. Fixture compilation: {record['compilation']}.\n\n")
                if record.get('error'):
                    summary.write('```text\n' + record['error'].replace('```', "'''") + '\n```\n\n')
                matrix = root / 'matrix/summary.json'
                if matrix.exists():
                    summary.write('| Case | Actual exit | Expected exit |\n|---|---|---|\n')
                    for case in json.loads(matrix.read_text())['cases']:
                        actual = case['exit_code'] if case['exit_code'] is not None else 'not_run'
                        summary.write(f"| {case['case']} | {actual} | {case['expected_exit_code']} |\n")
                    for case in json.loads(matrix.read_text())['cases']:
                        expected = case['expected_exit_code']
                        matches = case['exit_code'] in expected if isinstance(expected, list) else case['exit_code'] == expected
                        if not matches and case.get('diagnostic'):
                            summary.write('\n### ' + case['case'] + '\n\n```text\n' +
                                          case['diagnostic'].replace('```', "'''") + '\n```\n')
                summary.write('\nPDF visual review and supported-release acceptance remain separate.\n')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

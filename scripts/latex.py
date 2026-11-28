"""Candidate standalone LuaLaTeX driver. Never installs or repairs dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

DRIVER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RECEIPT_VERSION = 2
GENERATED_FIGURES = Path('src/figures/generated')
PROJECT_EXCLUDES = {'build', '.git', '.tools', '.cache', '__pycache__'}
LEGACY_SOURCE_SUFFIXES = {'.tex', '.bib', '.sty', '.cls'}
DEPENDENCY_HELP = 'See the project README.md for pinned dependency paths.'
TEX_DIAGNOSTIC = re.compile(
    r'(?:\b(?:citations?|references?)\b.*\bundefined\b|\bundefined\b.*\b(?:citations?|references?)\b'
    r'|\b(?:Citation|Reference) [^\n]*\n[^\n]*\bundefined\b|\bUndefined control sequence\b'
    r'|Please\s+(?:\(re\)run|rerun|run)\s+(?:Biber|BibTeX|LaTeX)\b|\brerun\s+(?:LaTeX|to get|needed|required)\b'
    r'|Label\(s\) may have changed|Missing character:|Font .*not found'
    r'|(?:cannot find|not found|not created|No file).*\.(?:bib|bbl)\b'
    r'|File .*\.(?:bib|bbl).*not found)', re.I)
BIBER_DIAGNOSTIC = re.compile(
    r'\b(?:ERROR|FATAL)\s+-|\bWARN\s+-.*'
    r"(?:did(?: not|n't) find.*(?:database|entry)|(?:cannot|could not) find|not found|rerun)", re.I)
MISSING_BIB_INPUT = re.compile(r'^Bib file\(s\) not found in search path:(?:\n[ \t]+[^\n]+)+', re.M)
LEGACY_TEX_DIAGNOSTIC = re.compile(TEX_DIAGNOSTIC.pattern + r'|undefined', re.I)
LEGACY_BIBER_DIAGNOSTIC = re.compile(BIBER_DIAGNOSTIC.pattern + r'|\bERROR\b', re.I)
BIBER_SOURCE = re.compile(r"\bINFO - Found BibTeX data source '(.+)'\s*$")
PDF_METADATA_LUA = '''
local doc = pdfe.open(arg[1])
if not doc or pdfe.getstatus(doc) ~= 0 then os.exit(1) end
local major, minor = pdfe.getversion(doc)
local pages = pdfe.getnofpages(doc)
if not major or not minor or not pages or pages < 1 then os.exit(1) end
for page = 1, pages do
    if not pdfe.getpage(doc, page) then os.exit(1) end
end
print(string.format("%d.%d %d", major, minor, pages))
pdfe.close(doc)
'''


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def contained(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError('path escapes selected root: ' + str(relative))
    return path


def verify(root, lock_path, bibliography='biber'):
    if not root.is_dir():
        raise ValueError('missing TeX Live root: ' + str(root) + '. ' + DEPENDENCY_HELP)
    lock = json.loads(lock_path.read_text())
    if not isinstance(lock, dict) or lock.get('policy') != 'texlive-local-v1' or not lock.get('verification_reference'):
        raise ValueError('reviewed texlive-local-v1 lock required')
    files = lock['files']
    tools = lock['tools']
    if not files or set(tools) != {'latexmk', 'lualatex', 'biber'}:
        raise ValueError('incomplete dependency inventory')
    for relative, expected in files.items():
        if bibliography == 'none' and relative == tools['biber']:
            continue
        path = contained(root, relative)
        if not path.is_file():
            raise ValueError('missing pinned dependency: ' + str(root / relative) + '. ' + DEPENDENCY_HELP)
        if digest(path) != expected:
            raise ValueError('dependency integrity mismatch: ' + relative + '. ' + DEPENDENCY_HELP)
    for name, relative in tools.items():
        if name == 'biber' and bibliography == 'none':
            continue
        if relative not in files or not os.access(contained(root, relative), os.X_OK):
            raise ValueError('unverified executable: ' + name + '. ' + DEPENDENCY_HELP)
    for field in ('release', 'architecture', 'versions', 'media'):
        if not lock.get(field):
            raise ValueError('missing lock identity: ' + field)
    import platform
    if lock['architecture'] != platform.machine():
        raise ValueError('native architecture mismatch')
    return lock


def environment(root, state, bin_dir):
    env = {'PATH': str(bin_dir) + os.pathsep + '/usr/bin:/bin',
           'LC_ALL': 'C', 'LANG': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '1786060800'}
    for key, name in {'HOME': 'home', 'TMPDIR': 'tmp', 'XDG_CONFIG_HOME': 'config',
                      'XDG_CACHE_HOME': 'cache', 'TEXMFHOME': 'home-texmf',
                      'TEXMFLOCAL': 'local-texmf', 'TEXMFCONFIG': 'config-texmf',
                      'TEXMFVAR': 'var-texmf', 'TEXMFCACHE': 'font-cache',
                      'PAR_GLOBAL_TMPDIR': 'par'}.items():
        target = state / name
        target.mkdir(parents=True, exist_ok=True)
        env[key] = str(target)
    env['TEXMFDIST'] = str(root / 'texmf-dist')
    env['TEXMFOUTPUT'] = str(state.parent)
    env['OSFONTDIR'] = str(state / 'home-texmf')
    font_config = state / 'config/luaotfload/luaotfload.conf'
    font_config.parent.mkdir(exist_ok=True)
    font_config.write_text('[db]\nlocation-precedence = texmf\n')
    return env


def execute(argv, cwd, env, console, timeout):
    with console.open('wb') as output:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise


def log_diagnostics(path, pattern):
    if not path.is_file():
        return []
    contents = path.read_text(errors='replace')
    messages = {}
    for match in pattern.finditer(contents):
        start = contents.rfind('\n', 0, match.start()) + 1
        end = contents.find('\n', match.end())
        message = contents[start:len(contents) if end == -1 else end].strip()
        messages[f'{path.name}: {message}'] = None
    return list(messages)


def artifact_names(stem, bibliography='biber'):
    names = [stem + suffix for suffix in ('.pdf', '.log', '.fls')]
    if bibliography == 'biber':
        names.extend((stem + '.blg', stem + '.bbl'))
    return names + ['console.log']


def inspect_output(directory, stem, bibliography='biber', *, legacy=False):
    names = artifact_names(stem, bibliography)
    if legacy:
        names.remove('console.log')
    errors = []
    for name in names:
        path = directory / name
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            errors.append('missing or invalid output: ' + name)
    tex_pattern = LEGACY_TEX_DIAGNOSTIC if legacy else TEX_DIAGNOSTIC
    bib_pattern = LEGACY_BIBER_DIAGNOSTIC if legacy else BIBER_DIAGNOSTIC
    errors.extend(log_diagnostics(directory / (stem + '.log'), tex_pattern))
    if bibliography == 'biber':
        errors.extend(log_diagnostics(directory / (stem + '.blg'), bib_pattern))
    return errors


def pdf_metadata(path, lualatex, timeout):
    # Reject truncated files even if the PDF reader can recover their page tree.
    with path.open('rb') as stream:
        if not re.fullmatch(rb'%PDF-\d\.\d', stream.read(8)):
            raise ValueError('invalid PDF header: ' + path.name)
        stream.seek(max(0, path.stat().st_size - 1024))
        if not stream.read().rstrip().endswith(b'%%EOF'):
            raise ValueError('missing PDF end marker: ' + path.name)
    with tempfile.TemporaryDirectory(prefix='neruda-pdf-') as scratch:
        script = Path(scratch) / 'metadata.lua'
        script.write_text(PDF_METADATA_LUA)
        result = subprocess.run([str(lualatex), '--luaonly', str(script), str(path.resolve())],
                                cwd=scratch, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'},
                                capture_output=True, text=True, errors='replace', timeout=timeout)
    match = re.fullmatch(r'(\d+\.\d+) ([1-9]\d*)', result.stdout.strip())
    if result.returncode or not match or result.stderr.strip():
        detail = (result.stderr or result.stdout).strip()
        raise ValueError('LuaLaTeX could not read PDF: ' + path.name + (': ' + detail if detail else ''))
    return {'version': match[1], 'page_count': int(match[2])}


def recorder_paths(fls, cwd=None):
    if fls.is_file():
        for line in fls.read_text(encoding='utf-8', errors='surrogateescape').splitlines():
            if line.startswith('PWD '):
                cwd = Path(line[4:])
            if line.startswith('INPUT '):
                path = Path(line[6:])
                if path.is_absolute():
                    yield path
                elif cwd is not None:
                    yield cwd / path


def file_signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def snapshot_file(path):
    # Open without following a last-component symlink or blocking on a FIFO.
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f'expected a regular input file: {path}')
        before = file_signature(info)
        hash_value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hash_value.update(block)
        if before != file_signature(os.stat(path, follow_symlinks=False)):
            raise ValueError(f'input changed while measuring: {path}')
    return before, hash_value.hexdigest()


def snapshot_project(project):
    inputs = {}

    def raise_walk_error(error):
        raise error

    for directory, children, names in os.walk(project, onerror=raise_walk_error):
        children[:] = sorted(name for name in children if name not in PROJECT_EXCLUDES)
        for name in sorted(set(names) - PROJECT_EXCLUDES):
            path = Path(directory) / name
            if stat.S_ISREG(path.lstat().st_mode):
                inputs[path] = snapshot_file(path)
    return inputs


def external_inputs(manifest, project, root):
    if manifest is None:
        return {}
    declarations = json.loads(manifest.read_text())
    if not isinstance(declarations, list):
        raise ValueError('external-input manifest must contain a JSON array of id, path and sha256 objects')
    files, ids = {}, set()
    for item in declarations:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str)
                                                for key in ('id', 'path', 'sha256')):
            raise ValueError('external inputs require string id, path and sha256 fields')
        label = item['id']
        original = Path(item['path'])
        if not original.is_absolute() or not label.strip() or label in ids:
            raise ValueError(f'external input requires a unique ID and an absolute path: {label}')
        path = original.resolve(strict=True)
        if path.is_relative_to(project) or path.is_relative_to(root) or path in files:
            raise ValueError(f'external input must identify a unique file outside the project and TeX Live: {path}')
        measured = snapshot_file(path)
        if measured[1] != item['sha256']:
            raise ValueError(f'external input hash mismatch: {label} ({path})')
        files[path] = (label, measured)
        ids.add(label)
    return files


def biber_control_errors(path):
    if not path.is_file():
        return [f'missing Biber control file: {path}']
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        return [f'malformed Biber control file: {error}']
    errors = []
    for source in root.findall('.//{*}datasource'):
        name = (source.text or '').strip()
        if re.match(r'^[a-z][a-z0-9+.-]*:', name, re.I):
            errors.append(f'Biber remote bibliography source refused: {name}')
        elif source.get('type') != 'file' or source.get('datatype') != 'bibtex' or not name:
            errors.append(f'unsupported Biber datasource: {name}')
    return errors


def biber_paths(log, cwd):
    for line in log.read_text(encoding='utf-8', errors='surrogateescape').splitlines():
        match = BIBER_SOURCE.search(line)
        if match:
            yield cwd / match[1]


def capture_tool(arguments):
    """Run one compiler rule and archive its dependency record before the next rule."""
    family, directory, stem, *command = arguments
    run = Path(directory)
    cwd = Path.cwd()
    evidence = run / 'passes'
    sequence = len(list(evidence.glob('*.json'))) + 1
    prefix = evidence / f'{sequence:04d}-{family}'
    archive = []
    errors = []
    original = run / (stem + ('.fls' if family == 'tex' else '.blg'))
    before = file_signature(original.stat()) if original.is_file() else None
    if family == 'biber':
        control = run / (stem + '.bcf')
        if control.is_file():
            archived_control = prefix.with_suffix('.bcf')
            shutil.copyfile(control, archived_control)
            archive.append(str(archived_control.relative_to(run)))
        errors.extend(biber_control_errors(control))
    code = 1
    if not errors:
        try:
            code = subprocess.run(command).returncode
        except OSError as error:
            errors.append(f'{family} could not run: {error}')
    observed = []
    if original.is_file() and file_signature(original.stat()) != before:
        saved = prefix.with_suffix(original.suffix)
        shutil.copyfile(original, saved)
        archive.append(str(saved.relative_to(run)))
        paths = recorder_paths(saved, cwd) if family == 'tex' else biber_paths(saved, cwd)
        if family == 'biber':
            paths = [control, *paths]
        for path in dict.fromkeys(paths):
            observed.append({'path': str(path), 'resolved': str(path.resolve())})
        if code == 0 and family == 'tex' and not observed:
            errors.append(f'TeX produced an empty input record: {original.name}')
    elif code == 0:
        errors.append(f'{family} did not refresh its dependency record: {original.name}')
    prefix.with_suffix('.json').write_text(json.dumps(
        {'tool': family, 'evidence': archive, 'inputs': observed, 'errors': errors}, indent=2) + '\n')
    for error in errors:
        print(error, file=sys.stderr)
    return code or int(bool(errors))


def audit_inputs(run, project, root, locked, sources, externals, bibliography):
    by_kind = {kind: {} for kind in ('project', 'distribution', 'intermediate', 'external')}
    errors, passes, tex_paths, tex_project = [], [], [], {}
    tools_seen = set()
    for record in sorted((run / 'passes').glob('*.json')):
        data = json.loads(record.read_text())
        tool = data['tool']
        tools_seen.add(tool)
        passes.extend([str(record.relative_to(run)), *data['evidence']])
        errors.extend(data['errors'])
        for item in data['inputs']:
            observed = Path(item['path'])
            path = Path(item['resolved'])
            if tool == 'tex':
                tex_paths.append(observed)
            try:
                if observed.resolve() != path:
                    raise ValueError('input path changed during compilation')
                if path.is_relative_to(run):
                    name = str(path.relative_to(run))
                    by_kind['intermediate'][name] = digest(path) if path.is_file() else None
                    continue
                if path.is_relative_to(root):
                    name = str(path.relative_to(root))
                    actual = snapshot_file(path)[1]
                    if locked.get(name) != actual:
                        raise ValueError('unverified consumed resource')
                    by_kind['distribution'][name] = actual
                    continue
                if path.is_relative_to(project):
                    kind, name, expected = 'project', str(path.relative_to(project)), sources.get(path)
                elif path in externals:
                    kind = 'external'
                    name, expected = externals[path]
                else:
                    raise ValueError('undeclared external dependency; declare it with --external-inputs')
                if expected is None or snapshot_file(path) != expected:
                    raise ValueError('input changed during compilation or was outside the project snapshot')
                by_kind[kind][name] = expected[1]
                if tool == 'tex' and kind == 'project':
                    tex_project[name] = expected[1]
            except (OSError, ValueError, RuntimeError) as error:
                errors.append(f'{tool} input {observed}: {error}')
    for required in ('tex', 'biber') if bibliography == 'biber' else ('tex',):
        if required not in tools_seen:
            errors.append(f'missing {required} dependency records')
    return by_kind, list(dict.fromkeys(errors)), passes, tex_paths, tex_project


def verify_figure(project, path):
    receipt = json.loads(path.read_text())
    if not isinstance(receipt, dict) or type(receipt.get('version')) is not int or receipt['version'] != 1:
        raise ValueError(f'unsupported figure receipt version: {path}')
    runtime = receipt.get('runtime')
    if not isinstance(runtime, str) or not runtime.strip():
        raise ValueError(f'missing figure runtime: {path}')
    for role in ('generator', 'data', 'output'):
        item = receipt.get(role)
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError(f'missing figure {role} path: {path}')
        relative = Path(item['path'])
        target = contained(project, relative)
        if '..' in relative.parts or target != project / relative:
            raise ValueError(f'figure {role} must use a project-relative path without symlinks: {relative}')
        if role == 'output' and not relative.is_relative_to(GENERATED_FIGURES):
            raise ValueError(f'figure output must be under {GENERATED_FIGURES}: {relative}')
        if not target.is_file() or digest(target) != item.get('sha256'):
            raise ValueError(f'missing or stale figure {role}: {relative}')
    return receipt


def figure_diagnostics(project, paths, consumed, receipts):
    verified = {}
    errors = []
    for path, receipt in receipts.items():
        output = receipt['output']
        relative = str(Path(output['path']))
        try:
            if verify_figure(project, path) != receipt:
                raise ValueError(f'figure receipt changed during compilation: {path}')
            if consumed.get(relative) != output['sha256']:
                raise ValueError(f'declared figure was not consumed: {relative}')
        except (ValueError, OSError) as error:
            errors.append(str(error))
        else:
            verified[relative] = receipt
    generated = {Path(relative) for relative in consumed if Path(relative).is_relative_to(GENERATED_FIGURES)}
    # Catch inputs referred to by a generated-tree alias as well as canonical paths.
    for path in paths:
        lexical = Path(os.path.abspath(path))
        if lexical.is_relative_to(project / GENERATED_FIGURES):
            generated.add(lexical.relative_to(project))
    errors.extend(f'consumed generated figure has no matching receipt: {relative}'
                  for relative in sorted(generated) if str(relative) not in verified)
    return verified, errors


def read_receipt(directory):
    path = directory / 'receipt.json'
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing or invalid build receipt')
    receipt = json.loads(path.read_text())
    if not isinstance(receipt, dict) or type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0:
        raise ValueError('successful build receipt required')
    version = receipt.get('version', 0)
    if type(version) is not int or version not in (0, 1, RECEIPT_VERSION):
        raise ValueError('unsupported build receipt version')
    mode = receipt.get('bibliography') if version == RECEIPT_VERSION else 'biber'
    if mode not in ('biber', 'none'):
        raise ValueError('invalid bibliography mode in build receipt')
    return receipt, mode


def check_output(directory, stem, entry, lock_sha256, lualatex, timeout, receipt, bibliography):
    try:
        version = receipt.get('version', 0)
        errors = inspect_output(directory, stem, bibliography, legacy=version == 0)
        if version == 0:
            names = {stem + '.pdf': receipt.get('pdf_sha256')}
        else:
            if receipt.get('entry') != entry or receipt.get('lock_sha256') != lock_sha256:
                raise ValueError('receipt entry or dependency lock does not match')
            names = receipt.get('artifacts')
            expected = set(artifact_names(stem, bibliography))
            if version == RECEIPT_VERSION:
                pass_files = receipt.get('pass_evidence')
                if (not isinstance(pass_files, list) or not pass_files
                        or not all(isinstance(name, str) and re.fullmatch(
                            r'passes/[0-9]+-(?:tex|biber)\.(?:json|fls|bcf|blg)', name) for name in pass_files)):
                    raise ValueError('invalid compiler pass evidence inventory')
                if (directory / 'passes').is_symlink():
                    raise ValueError('compiler pass evidence directory must not be a symlink')
                actual_pass_files = {str(path.relative_to(directory)) for path in (directory / 'passes').iterdir()}
                if len(pass_files) != len(set(pass_files)) or set(pass_files) != actual_pass_files:
                    raise ValueError('compiler pass evidence inventory does not match the run directory')
                expected.update(pass_files)
            if not isinstance(names, dict) or set(names) != expected:
                raise ValueError('incomplete receipt artifact inventory')
            if names[stem + '.pdf'] != receipt.get('pdf_sha256'):
                raise ValueError('inconsistent receipt PDF hashes')
        for name, expected in names.items():
            path = directory / name
            if path.is_symlink() or not path.is_file():
                errors.append('missing or invalid artifact: ' + name)
            elif digest(path) != expected:
                errors.append('artifact hash mismatch: ' + name)
        if not errors and version:
            if pdf_metadata(directory / (stem + '.pdf'), lualatex, timeout) != receipt.get('pdf_metadata'):
                errors.append('PDF metadata does not match receipt: ' + stem + '.pdf')
        return errors
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return [str(error)]


def cache_inventory(state):
    inventory = {}
    for name in ('font-cache', 'var-texmf'):
        directory = state / name
        if directory.is_symlink():
            raise ValueError('cache symlink refused')
        if not directory.exists():
            continue
        for path in directory.rglob('*'):
            if path.is_symlink() or (not path.is_file() and not path.is_dir()):
                raise ValueError('unsupported cache entry')
            if path.is_file():
                inventory[str(path.relative_to(state))] = digest(path)
    return inventory


def project_sources(project, sources):
    return {str(path.relative_to(project)): measured[1] for path, measured in sources.items()
            if path.suffix in LEGACY_SOURCE_SUFFIXES}


def project_git_metadata(project):
    # Discover the worktree from the project path even when invoked by a Git hook.
    git_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    git_env['GIT_OPTIONAL_LOCKS'] = '0'
    options = dict(cwd=project, env=git_env, capture_output=True, timeout=30)
    root = subprocess.run(['/usr/bin/git', 'rev-parse', '--show-toplevel'], **options)
    metadata = dict(source_revision=None, dirty_state=None, git_diagnostics=os.fsdecode(root.stderr))
    if root.returncode:
        return metadata
    worktree = Path(os.fsdecode(root.stdout.removesuffix(b'\n'))).resolve()
    if worktree != project:
        metadata['git_diagnostics'] = 'Git worktree root differs from the document project'
        return metadata

    revision = subprocess.run(['/usr/bin/git', 'rev-parse', '--verify', 'HEAD^{commit}'], **options)
    value = os.fsdecode(revision.stdout).strip()
    if revision.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}', value):
        metadata['source_revision'] = value
    metadata['git_diagnostics'] = os.fsdecode(revision.stderr)
    dirty = subprocess.run(['/usr/bin/git', 'status', '--porcelain'], **options)
    if dirty.returncode == 0:
        metadata['dirty_state'] = os.fsdecode(dirty.stdout)
    return metadata


def cache_baseline(directory, lock_sha256):
    receipt_path = directory / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    seal = json.loads((directory / 'cache-seal.json').read_text())
    if (receipt.get('exit_code') != 0 or receipt.get('lock_sha256') != lock_sha256
            or seal['receipt_sha256'] != digest(receipt_path)
            or seal['inventory'] != cache_inventory(directory / 'state')):
        raise ValueError('cache baseline integrity mismatch')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('preflight', 'build', 'check', 'seal-cache'))
    parser.add_argument('--tex-root', type=Path, default=os.environ.get('NERUDA_TEX_ROOT'))
    parser.add_argument('--lock', required=True, type=Path)
    parser.add_argument('--biber', type=Path, default=os.environ.get('NERUDA_BIBER'),
                        help='Explicit separately provisioned binary pinned in the lock')
    parser.add_argument('--cache-from', type=Path, help='Successful run with an explicitly sealed cache')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--entry', default='src/main.tex')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--figure-receipt', type=Path, action='append', default=[],
                        help='Explicit figure receipt, repeatable for multiple outputs')
    parser.add_argument('--external-inputs', type=Path, help='JSON manifest of pinned external input files')
    parser.add_argument('--bibliography', choices=('biber', 'none'), help='Bibliography mode, default biber')
    parser.add_argument('--output', type=Path, help='Existing run directory for check')
    args = parser.parse_args(argv)
    receipt = {'version': RECEIPT_VERSION, 'policy': 'texlive-local-v1', 'status': 'not_run', 'exit_code': 2,
               'driver_sha256': DRIVER_SHA256,
               'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    run = None
    try:
        if (args.figure_receipt or args.external_inputs) and args.operation != 'build':
            raise ValueError('--figure-receipt and --external-inputs are only supported by build')
        bibliography = args.bibliography or 'biber'
        if args.operation in ('check', 'seal-cache'):
            if not args.output:
                raise ValueError('--output required')
            if args.bibliography:
                raise ValueError('bibliography mode is taken from the build receipt')
            try:
                previous_receipt, bibliography = read_receipt(args.output)
            except (ValueError, OSError) as error:
                if args.operation != 'check':
                    raise
                print(json.dumps({'errors': [str(error)]}))
                return 1
        receipt['bibliography'] = bibliography
        if args.timeout <= 0:
            raise ValueError('--timeout must be positive')
        if not args.tex_root:
            raise ValueError('--tex-root or NERUDA_TEX_ROOT required. ' + DEPENDENCY_HELP)
        root = args.tex_root.resolve()
        lock = verify(root, args.lock, bibliography)
        if bibliography == 'biber' and args.biber:
            expected = lock.get('biber_override', {}).get('sha256')
            if not expected:
                raise ValueError('this lock does not pin a Biber override. ' + DEPENDENCY_HELP)
            if not args.biber.is_file() or not os.access(args.biber, os.X_OK):
                raise ValueError('missing or non-executable pinned Biber override: ' + str(args.biber) +
                                 '. ' + DEPENDENCY_HELP)
            if digest(args.biber) != expected:
                raise ValueError('Biber override integrity mismatch. ' + DEPENDENCY_HELP)
        elif bibliography == 'biber' and lock.get('biber_override'):
            raise ValueError('this lock requires --biber or NERUDA_BIBER. ' + DEPENDENCY_HELP)
        receipt['lock_sha256'] = digest(args.lock)
        receipt['release'] = lock['release']
        if args.operation == 'preflight':
            print(json.dumps(receipt | {'status': 'integrity_verified', 'exit_code': 0}, indent=2))
            return 0
        if args.operation == 'seal-cache':
            previous = args.output / 'receipt.json'
            if previous_receipt.get('lock_sha256') != receipt['lock_sha256']:
                raise ValueError('successful run with identical lock required')
            seal = {'receipt_sha256': digest(previous), 'inventory': cache_inventory(args.output / 'state')}
            with (args.output / 'cache-seal.json').open('x') as stream:
                json.dump(seal, stream, indent=2)
            return 0
        if not args.project:
            raise ValueError('--project required')
        project = args.project.resolve(strict=True)
        relative = Path(args.entry)
        if relative.is_absolute():
            relative = relative.relative_to(project)
        entry = contained(project, relative)
        if not entry.is_file() or entry.suffix != '.tex':
            raise ValueError('missing .tex entry')
        entry_relative = str(entry.relative_to(project))
        # Preserve the lualatex alias so LuaHBTeX selects the LaTeX format.
        tools = {name: root / path for name, path in lock['tools'].items()
                 if name != 'biber' or bibliography == 'biber'}
        tool_hashes = {name: lock['files'][lock['tools'][name]] for name in tools}
        if bibliography == 'biber' and args.biber:
            tools['biber'] = args.biber.resolve()
            tool_hashes['biber'] = expected
        if args.operation == 'check':
            errors = check_output(args.output, entry.stem, entry_relative, receipt['lock_sha256'],
                                  tools['lualatex'], args.timeout, previous_receipt, bibliography)
            print(json.dumps({'errors': errors}))
            return int(bool(errors))
        figures = {path.resolve(): verify_figure(project, path) for path in args.figure_receipt}
        outputs = {Path(figure['output']['path']) for figure in figures.values()}
        if len(outputs) != len(figures):
            raise ValueError('duplicate figure output in supplied receipts')
        receipt.update(entry=entry_relative, tool_identities={
            name: {'path': str(path), 'sha256': tool_hashes[name], 'version': lock['versions'].get(name)}
            for name, path in tools.items()
        })
        externals = external_inputs(args.external_inputs, project, root)
        sources = snapshot_project(project)
        source_inputs = project_sources(project, sources)
        receipt['source_inputs'] = source_inputs
        origin = sources.get(project / 'scaffold-origin.json')
        if origin is not None:
            receipt['scaffold_origin_sha256'] = origin[1]
        declared = {label: measured[1] for label, measured in externals.values()}
        receipt['declared_external_inputs'] = declared
        build = project / 'build'
        if build.is_symlink():
            raise ValueError('build directory must not be a symlink')
        directory = build / (str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        directory.mkdir(parents=True)
        run = directory
        config = run / 'latexmkrc'
        # Generated from verified paths only; Perl literals need their own escaping.
        def quote(value):
            return "'" + str(value).replace('\\', '\\\\').replace("'", "\\'") + "'"
        import shlex

        def rule(tool):
            return shlex.join([sys.executable, str(Path(__file__).resolve()), '--capture-tool',
                               'tex' if tool == 'lualatex' else 'biber', str(run), entry.stem,
                               str(tools[tool])])

        (run / 'passes').mkdir()
        compiler = rule('lualatex') + ' -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 -recorder %O %S'
        settings = '$lualatex = ' + quote(compiler) + ';\n'
        command = [str(tools['latexmk']), '-norc', '-r', str(config), '-lualatex',
                   '-outdir=' + str(run), './' + entry.name]
        if bibliography == 'biber':
            bib_command = rule('biber') + ' --noconf %O %B'
            settings += '$biber = ' + quote(bib_command) + ';\n'
        else:
            command.insert(-1, '-bibtex-')
        config.write_text(settings)
        env = environment(root, run / 'state', tools['lualatex'].parent)
        receipt.update(environment_policy='constructed-local-tex-v2', shell_escape=False,
                       font_config_sha256=digest(run / 'state/config/luaotfload/luaotfload.conf'),
                       source_date_epoch=env['SOURCE_DATE_EPOCH'])
        if args.cache_from:
            previous = cache_baseline(args.cache_from, receipt['lock_sha256'])
            if previous.get('entry_sha256') != digest(entry):
                raise ValueError('cache entry source mismatch')
            if previous.get('source_inputs') != source_inputs:
                raise ValueError('cache project source mismatch')
            if previous.get('bibliography', 'biber') != bibliography:
                raise ValueError('cache bibliography mode mismatch')
            if previous.get('version') == RECEIPT_VERSION:
                for relative, expected_hash in previous['consumed_project_files'].items():
                    if sources.get(contained(project, relative), (None, None))[1] != expected_hash:
                        raise ValueError(f'cache consumed project input mismatch: {relative}')
                if previous['declared_external_inputs'] != declared:
                    raise ValueError('cache external input mismatch')
            for name in ('font-cache', 'var-texmf'):
                source = args.cache_from / 'state' / name
                if source.exists():
                    shutil.copytree(source, run / 'state' / name, dirs_exist_ok=True)
            receipt['cache_baseline_receipt_sha256'] = digest(args.cache_from / 'receipt.json')
            receipt['cache_baseline_receipt_version'] = previous.get('version', 0)
        receipt.update(command=command, entry_sha256=digest(entry), status='fail', exit_code=1)
        receipt.update(project_git_metadata(project))
        code = None
        invocation_error = None
        try:
            code = execute(command, entry.parent, env, run / 'console.log', args.timeout)
        except subprocess.TimeoutExpired:
            invocation_error = 'compilation timed out'
        except OSError as error:
            invocation_error = str(error)
        errors = inspect_output(run, entry.stem, bibliography)
        if bibliography == 'biber':
            errors.extend(log_diagnostics(run / 'console.log', MISSING_BIB_INPUT))
        else:
            requests_bibtex = any(log_diagnostics(path, re.compile(r'^\\bib(?:data|style)\{', re.M))
                                  for path in run.glob('*.aux'))
            if requests_bibtex or any(path.suffix in ('.bcf', '.bbl', '.blg') for path in run.iterdir()):
                errors.append('document requests bibliography processing with --bibliography none')
        if invocation_error:
            receipt['error'] = invocation_error
            errors.insert(0, invocation_error)
        elif code:
            errors.insert(0, f'latexmk exited {code}; see console.log')
        inputs, input_errors, evidence, tex_paths, consumed_tex = audit_inputs(
            run, project, root, lock['files'], sources, externals, bibliography)
        errors.extend(input_errors)
        receipt.update(compiler_exit_code=code, errors=errors, pass_evidence=evidence, artifacts={
            name: digest(run / name) for name in [*artifact_names(entry.stem, bibliography), *evidence]
            if (run / name).is_file()
        })
        receipt['consumed_project_files'] = inputs['project']
        receipt['consumed_resources'] = inputs['distribution']
        receipt['consumed_run_files'] = inputs['intermediate']
        receipt['consumed_external_inputs'] = inputs['external']
        receipt['verified_figures'], figure_errors = figure_diagnostics(project, tex_paths, consumed_tex, figures)
        errors.extend(figure_errors)
        receipt['cache_inventory'] = cache_inventory(run / 'state')
        pdf = run / (entry.stem + '.pdf')
        if 'missing or invalid output: ' + pdf.name not in errors:
            receipt['pdf_sha256'] = receipt['artifacts'][pdf.name]
            try:
                receipt['pdf_metadata'] = pdf_metadata(pdf, tools['lualatex'], args.timeout)
            except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                errors.append(str(error))
        if not errors:
            receipt.update(status='partial', exit_code=0, limitation='Visual and independent acceptance pending')
        else:
            for error in errors:
                print(error, file=sys.stderr)
        return receipt['exit_code']
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        receipt['error'] = str(error)
        print(str(error), file=sys.stderr)
        return receipt['exit_code']
    finally:
        if run:
            pending = run / '.receipt.json.tmp'
            pending.write_text(json.dumps(receipt, indent=2) + '\n')
            pending.replace(run / 'receipt.json')
            print('Build receipt: ' + str(run / 'receipt.json'))


if __name__ == '__main__':
    if sys.argv[1:2] == ['--capture-tool']:
        sys.exit(capture_tool(sys.argv[2:]))
    sys.exit(main())

"""Candidate standalone LuaLaTeX driver. Never installs or repairs dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

DRIVER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
RECEIPT_VERSION = 1
GENERATED_FIGURES = Path('src/figures/generated')
REQUIRED_SUFFIXES = ('.pdf', '.log', '.blg', '.bbl', '.fls')
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


def verify(root, lock_path):
    if not root.is_dir():
        raise ValueError('missing TeX Live root: ' + str(root) + '; see docs/latex-stack.md')
    lock = json.loads(lock_path.read_text())
    if not isinstance(lock, dict) or lock.get('policy') != 'texlive-local-v1' or not lock.get('verification_reference'):
        raise ValueError('reviewed texlive-local-v1 lock required')
    files = lock['files']
    tools = lock['tools']
    if not files or set(tools) != {'latexmk', 'lualatex', 'biber'}:
        raise ValueError('incomplete dependency inventory')
    for relative, expected in files.items():
        path = contained(root, relative)
        if not path.is_file():
            raise ValueError('missing pinned dependency: ' + str(root / relative))
        if digest(path) != expected:
            raise ValueError('dependency integrity mismatch: ' + relative)
    for name, relative in tools.items():
        if relative not in files or not os.access(contained(root, relative), os.X_OK):
            raise ValueError('unverified executable: ' + name)
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


def artifact_names(stem):
    return [stem + suffix for suffix in REQUIRED_SUFFIXES] + ['console.log']


def inspect_output(directory, stem, *, legacy=False):
    names = artifact_names(stem)
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
        for line in fls.read_text(errors='replace').splitlines():
            if line.startswith('PWD '):
                cwd = Path(line[4:])
            if line.startswith('INPUT '):
                path = Path(line[6:])
                if path.is_absolute():
                    yield path
                elif cwd is not None:
                    yield cwd / path


def consumed_inputs(fls, root, cwd=None):
    """Record installed resources opened by TeX."""
    paths = {path.resolve() for path in recorder_paths(fls, cwd)}
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)
            if path.is_relative_to(root) and path.is_file()}


def consumed_project_files(paths, project):
    inventory = {}
    for path in sorted(set(paths)):
        resolved = path.resolve()
        if (resolved.is_relative_to(project) and not resolved.is_relative_to(project / 'build')
                and resolved.is_file()):
            inventory[str(resolved.relative_to(project))] = digest(resolved)
    return inventory


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


def check_output(directory, stem, entry, lock_sha256, lualatex, timeout):
    try:
        receipt_path = directory / 'receipt.json'
        if receipt_path.is_symlink():
            raise ValueError('receipt must be a regular file')
        receipt = json.loads(receipt_path.read_text())
        if not isinstance(receipt, dict) or type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0:
            raise ValueError('successful build receipt required')
        if 'version' not in receipt:
            errors = inspect_output(directory, stem, legacy=True)
            names = {stem + '.pdf': receipt.get('pdf_sha256')}
        elif type(receipt['version']) is int and receipt['version'] == RECEIPT_VERSION:
            if receipt.get('entry') != entry or receipt.get('lock_sha256') != lock_sha256:
                raise ValueError('receipt entry or dependency lock does not match')
            errors = inspect_output(directory, stem)
            names = receipt.get('artifacts')
            if not isinstance(names, dict) or set(names) != set(artifact_names(stem)):
                raise ValueError('incomplete receipt artifact inventory')
            if names[stem + '.pdf'] != receipt.get('pdf_sha256'):
                raise ValueError('inconsistent receipt PDF hashes')
        else:
            raise ValueError('unsupported build receipt version')
        for name, expected in names.items():
            path = directory / name
            if path.is_file() and not path.is_symlink() and digest(path) != expected:
                errors.append('artifact hash mismatch: ' + name)
        if not errors and 'version' in receipt:
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


def project_sources(project):
    inventory = {}
    for directory, children, names in os.walk(project):
        children[:] = sorted(name for name in children
                             if name not in ('build', '.git', '.tools', '.cache', '__pycache__'))
        for name in sorted(names):
            path = Path(directory) / name
            if path.is_file() and path.suffix in ('.tex', '.bib', '.sty', '.cls'):
                inventory[str(path.relative_to(project))] = digest(path)
    return inventory


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
    parser.add_argument('--output', type=Path, help='Existing run directory for check')
    args = parser.parse_args(argv)
    receipt = {'version': RECEIPT_VERSION, 'policy': 'texlive-local-v1', 'status': 'not_run', 'exit_code': 2,
               'driver_sha256': DRIVER_SHA256,
               'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    run = None
    try:
        if args.figure_receipt and args.operation != 'build':
            raise ValueError('--figure-receipt is only supported by build')
        if args.timeout <= 0:
            raise ValueError('--timeout must be positive')
        if not args.tex_root:
            raise ValueError('--tex-root or NERUDA_TEX_ROOT required')
        root = args.tex_root.resolve()
        lock = verify(root, args.lock)
        if args.biber:
            expected = lock.get('biber_override', {}).get('sha256')
            if not expected:
                raise ValueError('this lock does not pin a Biber override')
            if not args.biber.is_file() or not os.access(args.biber, os.X_OK):
                raise ValueError('missing or non-executable pinned Biber override: ' + str(args.biber) +
                                 '; see docs/latex-stack.md')
            if digest(args.biber) != expected:
                raise ValueError('Biber override integrity mismatch')
        elif lock.get('biber_override'):
            raise ValueError('this lock requires --biber or NERUDA_BIBER; see docs/latex-stack.md')
        receipt['lock_sha256'] = digest(args.lock)
        receipt['release'] = lock['release']
        if args.operation == 'preflight':
            print(json.dumps(receipt | {'status': 'integrity_verified', 'exit_code': 0}, indent=2))
            return 0
        if args.operation == 'seal-cache':
            if not args.output:
                raise ValueError('--output required')
            previous = args.output / 'receipt.json'
            raw = json.loads(previous.read_text())
            if raw.get('exit_code') != 0 or raw.get('lock_sha256') != receipt['lock_sha256']:
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
        tools = {name: root / path for name, path in lock['tools'].items()}
        tool_hashes = {name: lock['files'][path] for name, path in lock['tools'].items()}
        if args.biber:
            tools['biber'] = args.biber.resolve()
            tool_hashes['biber'] = expected
        if args.operation == 'check':
            if not args.output:
                raise ValueError('--output required for check')
            errors = check_output(args.output, entry.stem, entry_relative, receipt['lock_sha256'],
                                  tools['lualatex'], args.timeout)
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
        compiler = shlex.quote(str(tools['lualatex'])) + ' -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -synctex=1 -recorder %O %S'
        bibliography = shlex.quote(str(tools['biber'])) + ' --noconf %O %B'
        config.write_text('$lualatex = ' + quote(compiler) + ';\n$biber = ' + quote(bibliography) + ';\n')
        command = [str(tools['latexmk']), '-norc', '-r', str(config), '-lualatex',
                   '-outdir=' + str(run), './' + entry.name]
        env = environment(root, run / 'state', tools['lualatex'].parent)
        receipt.update(environment_policy='constructed-local-tex-v1', shell_escape=False,
                       source_date_epoch=env['SOURCE_DATE_EPOCH'])
        if args.cache_from:
            import shutil
            previous = cache_baseline(args.cache_from, receipt['lock_sha256'])
            if previous.get('entry_sha256') != digest(entry):
                raise ValueError('cache entry source mismatch')
            for name in ('font-cache', 'var-texmf'):
                source = args.cache_from / 'state' / name
                if source.exists():
                    shutil.copytree(source, run / 'state' / name, dirs_exist_ok=True)
            receipt['cache_baseline_receipt_sha256'] = digest(args.cache_from / 'receipt.json')
        receipt.update(command=command, entry_sha256=digest(entry), status='fail', exit_code=1)
        receipt['source_inputs'] = project_sources(project)
        receipt.update(project_git_metadata(project))
        if args.cache_from and previous.get('source_inputs') != receipt['source_inputs']:
            receipt.update(status='not_run', exit_code=2)
            raise ValueError('cache project source mismatch')
        code = None
        invocation_error = None
        try:
            code = execute(command, entry.parent, env, run / 'console.log', args.timeout)
        except subprocess.TimeoutExpired:
            invocation_error = 'compilation timed out'
        except OSError as error:
            invocation_error = str(error)
        errors = inspect_output(run, entry.stem)
        errors.extend(log_diagnostics(run / 'console.log', MISSING_BIB_INPUT))
        if invocation_error:
            receipt['error'] = invocation_error
            errors.insert(0, invocation_error)
        elif code:
            errors.insert(0, f'latexmk exited {code}; see console.log')
        fls = run / (entry.stem + '.fls')
        receipt.update(compiler_exit_code=code, errors=errors, artifacts={
            name: digest(run / name) for name in artifact_names(entry.stem) if (run / name).is_file()
        })
        receipt['consumed_resources'] = consumed_inputs(fls, root, entry.parent)
        for relative, actual in receipt['consumed_resources'].items():
            if lock['files'].get(relative) != actual:
                errors.append('unverified consumed resource: ' + relative)
        tex_paths = list(recorder_paths(fls, entry.parent))
        consumed_tex = consumed_project_files(tex_paths, project)
        blg = run / (entry.stem + '.blg')
        bib_paths = []
        if blg.is_file():
            for line in blg.read_text(errors='replace').splitlines():
                match = BIBER_SOURCE.search(line)
                if match:
                    bib_paths.append(entry.parent / match[1])
        receipt['consumed_project_files'] = consumed_tex | consumed_project_files(bib_paths, project)
        for relative, actual in receipt['consumed_project_files'].items():
            if relative in receipt['source_inputs'] and receipt['source_inputs'][relative] != actual:
                errors.append('project input changed during compilation: ' + relative)
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
    sys.exit(main())

"""Candidate standalone LuaLaTeX driver. Never installs or repairs dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

DRIVER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


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
    lock = json.loads(lock_path.read_text())
    if lock.get('policy') != 'texlive-local-v1' or not lock.get('verification_reference'):
        raise ValueError('reviewed texlive-local-v1 lock required')
    files = lock['files']
    tools = lock['tools']
    if not files or set(tools) != {'latexmk', 'lualatex', 'biber'}:
        raise ValueError('incomplete dependency inventory')
    for relative, expected in files.items():
        path = contained(root, relative)
        if not path.is_file() or digest(path) != expected:
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


def inspect_output(directory, stem):
    errors = []
    for suffix in ('.pdf', '.log', '.blg', '.bbl', '.fls'):
        path = directory / (stem + suffix)
        if not path.is_file() or not path.stat().st_size:
            errors.append('missing output: ' + path.name)
    log = directory / (stem + '.log')
    if log.exists():
        import re
        if re.search(r'undefined|Please \(re\)run Biber|Rerun to get|Missing character|Font .*not found',
                     log.read_text(errors='replace'), re.I):
            errors.append('unresolved references, fonts or rerun request')
    blg = directory / (stem + '.blg')
    if blg.exists() and 'ERROR' in blg.read_text(errors='replace'):
        errors.append('Biber reported errors')
    return errors


def consumed_inputs(fls, root):
    """Record installed resources actually opened, using recorder paths verbatim."""
    inventory = {}
    if fls.is_file():
        for line in fls.read_text(errors='replace').splitlines():
            if line.startswith('INPUT '):
                path = Path(line[6:])
                if path.is_absolute() and path.is_file() and path.resolve().is_relative_to(root):
                    inventory[str(path.resolve().relative_to(root))] = digest(path)
    return inventory


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
    parser.add_argument('--output', type=Path, help='Existing run directory for check')
    args = parser.parse_args(argv)
    receipt = {'policy': 'texlive-local-v1', 'status': 'not_run', 'exit_code': 2,
               'driver_sha256': DRIVER_SHA256,
               'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    run = None
    try:
        if not args.tex_root:
            raise ValueError('--tex-root or NERUDA_TEX_ROOT required')
        root = args.tex_root.resolve()
        lock = verify(root, args.lock)
        if args.biber:
            expected = lock.get('biber_override', {}).get('sha256')
            if not expected or digest(args.biber) != expected or not os.access(args.biber, os.X_OK):
                raise ValueError('Biber override integrity mismatch')
        elif lock.get('biber_override'):
            raise ValueError('this lock requires an explicit --biber executable')
        receipt['lock_sha256'] = digest(args.lock)
        receipt['release'] = lock['release']
        if args.operation == 'preflight':
            print(json.dumps(receipt | {'status': 'integrity_verified'}, indent=2))
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
        if args.operation == 'check':
            if not args.output:
                raise ValueError('--output required for check')
            errors = inspect_output(args.output, entry.stem)
            print(json.dumps({'errors': errors}))
            return int(bool(errors))
        build = project / 'build'
        if build.is_symlink():
            raise ValueError('build directory must not be a symlink')
        run = build / (str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        run.mkdir(parents=True)
        # Preserve executable alias names: invoking resolved luahbtex instead of
        # lualatex changes the selected format. verify() already checks targets.
        tools = {name: root / path for name, path in lock['tools'].items()}
        if args.biber:
            tools['biber'] = args.biber.resolve()
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
        git = subprocess.run(['/usr/bin/git', 'rev-parse', '--verify', 'HEAD^{commit}'],
                             cwd=project, capture_output=True, text=True, timeout=30)
        import re
        receipt['source_revision'] = git.stdout.strip() if git.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}', git.stdout.strip()) else None
        receipt['git_diagnostics'] = git.stderr
        dirty = subprocess.run(['/usr/bin/git', 'status', '--porcelain'], cwd=project,
                               capture_output=True, text=True, timeout=30)
        receipt['dirty_state'] = dirty.stdout if dirty.returncode == 0 else None
        if args.cache_from and previous.get('source_inputs') != receipt['source_inputs']:
            receipt.update(status='not_run', exit_code=2)
            raise ValueError('cache project source mismatch')
        code = execute(command, entry.parent, env, run / 'console.log', args.timeout)
        errors = inspect_output(run, entry.stem)
        receipt['consumed_resources'] = consumed_inputs(run / (entry.stem + '.fls'), root)
        for relative, actual in receipt['consumed_resources'].items():
            if lock['files'].get(relative) != actual:
                errors.append('unverified consumed resource: ' + relative)
        receipt.update(compiler_exit_code=code, errors=errors)
        receipt['cache_inventory'] = cache_inventory(run / 'state')
        if code == 0 and not errors:
            receipt.update(status='partial', exit_code=0,
                           limitation='Compilation only; consumed-input and visual acceptance pending')
            receipt['pdf_sha256'] = digest(run / (entry.stem + '.pdf'))
        return receipt['exit_code']
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        receipt['error'] = str(error)
        print(str(error), file=sys.stderr)
        return receipt['exit_code']
    except subprocess.TimeoutExpired:
        receipt.update(error='compilation timed out', exit_code=1, status='fail')
        return 1
    finally:
        if run:
            (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
            print('Build receipt: ' + str(run / 'receipt.json'))


if __name__ == '__main__':
    sys.exit(main())

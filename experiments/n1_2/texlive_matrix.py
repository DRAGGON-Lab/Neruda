"""Native macOS cache/network experiment on public synthetic fixtures only."""
import argparse
import json
from pathlib import Path
import platform
import os
import shutil
import subprocess
import sys
import hashlib
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
DRIVER = HERE.parents[1] / 'scripts' / 'latex.py'
POLICY = '(version 1) (allow default) (deny network*)'


def matrix_exit(cases):
    def matches(case):
        expected = case['expected_exit_code']
        return case['exit_code'] in expected if isinstance(expected, list) else case['exit_code'] == expected
    return 0 if cases and all(matches(case) for case in cases) else 1


def network_prefix():
    if platform.system() == 'Darwin':
        return ['/usr/bin/sandbox-exec', '-p', POLICY]
    if platform.system() == 'Linux':
        return ['/usr/bin/sudo', '-n', '/usr/bin/unshare', '--net', '--', '/usr/bin/setpriv',
                '--reuid', str(os.getuid()), '--regid', str(os.getgid()),
                '--init-groups', '--no-new-privs']
    raise ValueError('no OS network-denial adapter for this platform')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--tex-root', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--biber', type=Path)
    args = parser.parse_args(argv)
    try:
        boundary = network_prefix()
    except ValueError as error:
        parser.error(str(error))
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    harness_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    selection = ['--lock', str(args.lock.resolve())]
    if args.biber:
        selection += ['--biber', str(args.biber.resolve())]
    common = ['--tex-root', str(args.tex_root.resolve()), *selection]
    cases = []
    fixtures = [('article', 'article', 'main.tex'), ('slides', 'slides', 'main.tex'),
                ('handout', 'slides', 'handout.tex')]
    baselines = {}
    for name, source, entry in fixtures:
        shutil.copytree(HERE / source / 'src', root / name / 'src')

    def execute(label, command, expected=0):
        console_path = root / (label + '.console.log')
        with console_path.open('w') as console:
            result = subprocess.run(command, stdout=console, stderr=subprocess.STDOUT, timeout=900)
        case = {'case': label, 'command': command, 'exit_code': result.returncode,
                'expected_exit_code': expected, 'status': 'executed'}
        if result.returncode:
            text = console_path.read_text(errors='replace')
            case['diagnostic'] = text[-2000:]
            for line in text.splitlines():
                if line.startswith('Build receipt: '):
                    path = Path(line[len('Build receipt: '):]).resolve()
                    if path.is_relative_to(root) and path.is_file():
                        receipt = json.loads(path.read_text())
                        case['diagnostic'] = '\n'.join(receipt.get('errors', [])) or receipt.get('error', text[-2000:])
                        compiler_log = path.parent / 'console.log'
                        if compiler_log.is_file():
                            import re
                            lines = [value for value in compiler_log.read_text(errors='replace').splitlines()
                                     if re.search(r'^!|:[0-9]+:|ERROR|Fatal|Latexmk:.*failed', value)]
                            case['diagnostic'] += '\n' + '\n'.join(lines[:10])
        return case

    try:
        probe = ['/usr/bin/curl', '--head', '--fail', '--max-time', '15',
                 'https://tug.ctan.org/systems/mac/mactex/mactex-20260324.pkg.sha512']
        cases.append(execute('network-control', probe))
        cases.append(execute('network-boundary-ready', [*boundary, '/usr/bin/true']))
        denied = execute('network-denied', [*boundary, *probe], [6, 7, 28])
        cases.append(denied)
        if matrix_exit(cases):
            raise ValueError('network-denial control failed; refusing offline claims')
        for scenario in ('cold', 'warm', 'offline', 'offline-empty'):
            commands = []
            for name, source, entry in fixtures:
                command = [sys.executable, str(DRIVER), 'build', *common,
                           '--project', str(root / name), '--entry', 'src/' + entry]
                if scenario in ('warm', 'offline'):
                    if name not in baselines:
                        cases.append({'case': scenario + '-' + name, 'exit_code': None,
                                      'expected_exit_code': 0, 'status': 'not_run',
                                      'diagnostic': 'No successful sealed cold cache is available'})
                        continue
                    command.extend(['--cache-from', str(baselines[name])])
                if scenario.startswith('offline'):
                    command = [*boundary, *command]
                commands.append((scenario + '-' + name, command))
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda pair: execute(*pair), commands))
            cases.extend(results)
            if scenario == 'cold':
                for name, source, entry in fixtures:
                    result = next(c for c in results if c['case'] == 'cold-' + name)
                    runs = list((root / name / 'build').iterdir())
                    if result['exit_code'] == 0 and len(runs) == 1:
                        run = runs[0]
                        seal = execute('seal-' + name, [sys.executable, str(DRIVER), 'seal-cache', *common, '--output', str(run)])
                        cases.append(seal)
                        if seal['exit_code'] == 0:
                            baselines[name] = run
        cases.append(execute('missing-dependency', [sys.executable, str(DRIVER), 'preflight',
                     '--tex-root', str(root / 'missing-tex'), *selection], 2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        cases.append({'case': 'orchestration', 'exit_code': 1, 'expected_exit_code': 0, 'error': str(error)})
    finally:
        summary = {'cases': cases, 'exit_code': matrix_exit(cases),
                   'harness_sha256': harness_sha256,
                   'platform': platform.platform(), 'visual_review': 'separate required check'}
        (root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary, indent=2))
    return summary['exit_code']


if __name__ == '__main__':
    sys.exit(main())

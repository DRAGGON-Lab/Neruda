import importlib.util
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('latex', Path(__file__).resolve().parents[1] / 'scripts/latex.py')
latex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latex)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'tex root'
        self.root.mkdir()
        tools = {}
        files = {}
        for name in ('lualatex', 'latexmk', 'biber'):
            path = self.root / name
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o700)
            tools[name] = name
            files[name] = latex.digest(path)
        self.lock = self.base / 'lock.json'
        self.lock.write_text(json.dumps(dict(policy='texlive-local-v1', files=files, tools=tools,
            architecture=platform.machine(), release='test-only', versions={'test': 'fixture'},
            media={'test': 'fixture'}, verification_reference='test-only')))
        self.project = self.base / 'project with spaces'
        (self.project / 'src').mkdir(parents=True)
        (self.project / 'src/main.tex').write_text('synthetic')
        self.args = ['--tex-root', str(self.root), '--lock', str(self.lock), '--project', str(self.project)]

    def test_missing_lock_refuses_without_build_directory(self):
        self.lock.unlink()
        self.assertEqual(latex.main(['build', *self.args]), 2)
        self.assertFalse((self.project / 'build').exists())

    def test_corrupt_dependency_refuses(self):
        (self.root / 'biber').write_text('corruption')
        self.assertEqual(latex.main(['build', *self.args]), 2)

    def test_foreign_architecture_refuses(self):
        lock = json.loads(self.lock.read_text())
        lock['architecture'] = 'foreign'
        self.lock.write_text(json.dumps(lock))
        self.assertEqual(latex.main(['preflight', *self.args]), 2)

    def test_path_traversal_refuses(self):
        with self.assertRaises(ValueError):
            latex.contained(self.root, '../lock.json')

    def test_environment_excludes_host_overrides(self):
        with patch.dict(os.environ, {'TEXINPUTS': '/poison', 'BIBINPUTS': '/poison'}):
            env = latex.environment(self.root, self.base / 'state', self.root)
        self.assertNotIn('TEXINPUTS', env)
        self.assertNotIn('BIBINPUTS', env)
        self.assertNotEqual(env['HOME'], os.environ['HOME'])
        self.assertEqual(env['TEXMFOUTPUT'], str(self.base))

    def test_unpinned_biber_override_refused(self):
        self.assertEqual(latex.main(['build', *self.args, '--biber', str(self.root / 'biber')]), 2)

    def test_build_failure_keeps_diagnostics_and_receipt(self):
        self.assertEqual(latex.main(['build', *self.args]), 1)
        run = next((self.project / 'build').iterdir())
        self.assertTrue((run / 'console.log').exists())
        receipt = json.loads((run / 'receipt.json').read_text())
        self.assertEqual(receipt['exit_code'], 1)
        self.assertTrue(receipt['errors'])

    def test_success_selects_verified_tools_and_disables_shell_escape(self):
        def execute(command, cwd, env, console, timeout):
            directory = console.parent
            for suffix in ('.pdf', '.log', '.blg', '.bbl', '.fls'):
                (directory / ('main' + suffix)).write_text('fixture output')
            console.write_text('fixture console')
            self.assertEqual(command[0], str((self.root / 'latexmk').resolve()))
            self.assertIn('-norc', command)
            self.assertIn('-no-shell-escape', (directory / 'latexmkrc').read_text())
            self.assertIn('--noconf', (directory / 'latexmkrc').read_text())
            return 0
        with patch.object(latex, 'execute', side_effect=execute):
            self.assertEqual(latex.main(['build', *self.args]), 0)

    def test_timeout_keeps_partial_evidence(self):
        import subprocess
        with patch.object(latex, 'execute', side_effect=subprocess.TimeoutExpired('fixture', 1)):
            self.assertEqual(latex.main(['build', *self.args]), 1)
        run = next((self.project / 'build').iterdir())
        self.assertEqual(json.loads((run / 'receipt.json').read_text())['error'], 'compilation timed out')

    def test_lualatex_alias_is_preserved(self):
        binary = self.root / 'luahbtex'
        (self.root / 'lualatex').rename(binary)
        (self.root / 'lualatex').symlink_to('luahbtex')
        def execute(command, cwd, env, console, timeout):
            config = (console.parent / 'latexmkrc').read_text()
            self.assertIn('/lualatex', config)
            self.assertNotIn('/luahbtex', config)
            return 1
        with patch.object(latex, 'execute', side_effect=execute):
            self.assertEqual(latex.main(['build', *self.args]), 1)

    def test_cache_tampering_is_detected(self):
        run = self.base / 'baseline'
        cache = run / 'state/font-cache'
        cache.mkdir(parents=True)
        (cache / 'data').write_text('original')
        receipt = run / 'receipt.json'
        receipt.write_text(json.dumps({'exit_code': 0, 'lock_sha256': 'fixture-lock'}))
        (run / 'cache-seal.json').write_text(json.dumps({'receipt_sha256': latex.digest(receipt),
                'inventory': latex.cache_inventory(run / 'state')}))
        self.assertEqual(latex.cache_baseline(run, 'fixture-lock')['exit_code'], 0)
        (cache / 'data').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            latex.cache_baseline(run, 'fixture-lock')

    def test_cache_symlink_is_refused(self):
        state = self.base / 'cache-state'
        state.mkdir()
        (state / 'font-cache').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            latex.cache_inventory(state)

    def test_recorder_paths_with_spaces_are_preserved(self):
        path = self.root / 'font with spaces.otf'
        path.write_text('font fixture')
        fls = self.base / 'input.fls'
        fls.write_text('INPUT ' + str(path.resolve()) + '\n')
        self.assertEqual(latex.consumed_inputs(fls, self.root.resolve()),
                         {'font with spaces.otf': latex.digest(path)})

    def test_generated_dependency_sources_do_not_contaminate_project_identity(self):
        for name in ('build', '.tools'):
            path = self.project / name
            path.mkdir()
            (path / 'unrelated.tex').write_text('generated dependency source')
        self.assertEqual(set(latex.project_sources(self.project)), {'src/main.tex'})

    def test_entry_name_is_not_interpreted_as_a_latexmk_option(self):
        (self.project / 'src/-e.tex').write_text('fixture')
        def execute(command, *args):
            self.assertEqual(command[-1], './-e.tex')
            return 1
        with patch.object(latex, 'execute', side_effect=execute):
            self.assertEqual(latex.main(['build', *self.args, '--entry', 'src/-e.tex']), 1)

    def test_real_timeout_preserves_partial_console(self):
        import subprocess
        import sys
        console = self.base / 'timeout.log'
        with self.assertRaises(subprocess.TimeoutExpired):
            latex.execute([sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(10)'],
                          self.base, {'PATH': '/usr/bin:/bin'}, console, 1)
        self.assertEqual(console.read_text().strip(), 'started')


if __name__ == '__main__':
    unittest.main()

import importlib.util
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import platform
import subprocess
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
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'tex root'
        self.root.mkdir()
        tools = {}
        files = {}
        for name in ('lualatex', 'latexmk', 'biber'):
            path = self.root / name
            script = "echo '1.7 1'\n" if name == 'lualatex' else 'exit 0\n'
            path.write_text('#!/bin/sh\n' + script)
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

    def test_successful_preflight_reports_zero_in_receipt(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch.object(latex, 'execute') as execute:
            self.assertEqual(latex.main(['preflight', *self.args]), 0)
        receipt = json.loads(stdout.getvalue())
        self.assertEqual((receipt['status'], receipt['exit_code']), ('integrity_verified', 0))
        execute.assert_not_called()

    def test_corrupt_dependency_refuses(self):
        (self.root / 'biber').write_text('corruption')
        self.assertEqual(latex.main(['build', *self.args]), 2)

    def test_missing_distribution_file_reports_path_without_launching(self):
        missing = self.root / 'lualatex'
        missing.unlink()
        stderr = io.StringIO()
        with redirect_stderr(stderr), patch.object(latex, 'execute') as execute:
            self.assertEqual(latex.main(['build', *self.args]), 2)
        self.assertIn('missing pinned dependency:', stderr.getvalue())
        self.assertIn(str(missing), stderr.getvalue())
        self.assertFalse((self.project / 'build').exists())
        execute.assert_not_called()

    def test_pinned_biber_override_is_required_and_reports_missing_path(self):
        lock = json.loads(self.lock.read_text())
        lock['biber_override'] = {'sha256': latex.digest(self.root / 'biber')}
        self.lock.write_text(json.dumps(lock))
        missing = self.base / 'missing arm64 biber'
        for args, expected in [([], '--biber or NERUDA_BIBER'),
                               (['--biber', str(missing)], str(missing))]:
            stderr = io.StringIO()
            with self.subTest(args=args), redirect_stderr(stderr), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(latex.main(['preflight', *self.args, *args]), 2)
            self.assertIn(expected, stderr.getvalue())

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

    def initialize_repository(self, directory):
        def git(*args):
            return subprocess.check_output(
                ['/usr/bin/git', *args], cwd=directory, text=True,
                stderr=subprocess.PIPE,
            ).strip()

        git('init', '-q')
        (directory / '.gitignore').write_text('build/\n')
        git('add', '.')
        git('-c', 'user.name=Neruda Test', '-c', 'user.email=neruda@example.test',
            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Initial fixture')
        return git('rev-parse', 'HEAD')

    def build_receipt(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(latex.main(['build', *self.args]), 1)
        path = stdout.getvalue().strip().removeprefix('Build receipt: ')
        return json.loads(Path(path).read_text())

    def test_standalone_directory_has_null_git_provenance(self):
        receipt = self.build_receipt()
        self.assertIsNone(receipt['source_revision'])
        self.assertIsNone(receipt['dirty_state'])

    def test_independent_repository_records_its_revision_and_dirty_state(self):
        revision = self.initialize_repository(self.project)
        clean = self.build_receipt()
        self.assertEqual(clean['source_revision'], revision)
        self.assertEqual(clean['dirty_state'], '')

        (self.project / 'src/main.tex').write_text('edited fixture')
        dirty = self.build_receipt()
        self.assertEqual(dirty['source_revision'], revision)
        self.assertIn(' M src/main.tex', dirty['dirty_state'])

    def test_nested_project_has_null_git_provenance(self):
        self.initialize_repository(self.base)
        (self.base / 'ancestor-only.txt').write_text('untracked ancestor file')
        receipt = self.build_receipt()
        self.assertIsNone(receipt['source_revision'])
        self.assertIsNone(receipt['dirty_state'])

    def test_git_environment_cannot_attribute_another_repository_to_the_project(self):
        self.initialize_repository(self.base)
        with patch.dict(os.environ, {'GIT_DIR': str(self.base / '.git'),
                                    'GIT_WORK_TREE': str(self.project)}):
            receipt = self.build_receipt()
        self.assertIsNone(receipt['source_revision'])
        self.assertIsNone(receipt['dirty_state'])

    def test_success_selects_verified_tools_and_disables_shell_escape(self):
        def execute(command, cwd, env, console, timeout):
            directory = console.parent
            for suffix in ('.pdf', '.log', '.blg', '.bbl', '.fls'):
                (directory / ('main' + suffix)).write_text('fixture output')
            self.fake_compile(command, cwd, env, console, timeout)
            self.assertEqual(command[0], str((self.root / 'latexmk').resolve()))
            self.assertIn('-norc', command)
            self.assertIn('-no-shell-escape', (directory / 'latexmkrc').read_text())
            self.assertIn('--noconf', (directory / 'latexmkrc').read_text())
            return 0
        with patch.object(latex, 'execute', side_effect=execute):
            self.assertEqual(latex.main(['build', *self.args]), 0)

    def cli(self, operation, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = latex.main([operation, *self.args, *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def fake_compile(self, command, cwd, env, console, timeout):
        self.run = console.parent
        for suffix in ('.bbl', '.log', '.blg'):
            (self.run / ('main' + suffix)).write_text('fixture output')
        (self.run / 'main.pdf').write_bytes(b'%PDF-1.7\n%%EOF\n')
        (self.run / 'main.fls').write_text(f'PWD {cwd}\nINPUT ./main.tex\n')
        console.write_text('fixture console')
        self.record_pass('tex', [cwd / 'main.tex'])
        self.record_pass('biber', [])
        return 0

    def record_pass(self, family, paths, number=None):
        directory = self.run / 'passes'
        sequence = number or len(list(directory.glob('*.json'))) + 1
        prefix = directory / f'{sequence:04d}-{family}'
        suffix = '.fls' if family == 'tex' else '.blg'
        archived = prefix.with_suffix(suffix)
        archived.write_bytes((self.run / ('main' + suffix)).read_bytes())
        prefix.with_suffix('.json').write_text(json.dumps({
            'tool': family, 'evidence': [str(archived.relative_to(self.run))],
            'inputs': [{'path': str(p), 'resolved': str(p.resolve())} for p in paths], 'errors': [],
        }))

    def new_figure(self):
        receipt = {'version': 1, 'runtime': 'fixture runtime'}
        for role, relative in [('generator', 'figures/source/g.py'), ('data', 'figures/source/data.json'),
                               ('output', 'src/figures/generated/figure with spaces.png')]:
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(role)
            receipt[role] = {'path': relative, 'sha256': latex.digest(path)}
        path = self.project / 'figure.json'
        path.write_text(json.dumps(receipt))
        return path, receipt

    def test_generated_figure_requires_matching_consumed_receipt(self):
        path, figure = self.new_figure()
        relative = figure['output']['path']
        def compile_with_figure(*args):
            self.fake_compile(*args)
            (self.run / 'main.fls').write_text(f'PWD {args[1]}\nINPUT ../{relative}\n')
            self.record_pass('tex', [args[1] / '..' / relative], 1)
            return 0
        for options, compiler, code, diagnostic in [
            ([], compile_with_figure, 1, 'consumed generated figure has no matching receipt'),
            (['--figure-receipt', str(path)], self.fake_compile, 1, 'declared figure was not consumed'),
            (['--figure-receipt', str(path)], compile_with_figure, 0, ''),
        ]:
            with self.subTest(options=options, diagnostic=diagnostic):
                with patch.object(latex, 'execute', side_effect=compiler):
                    result, _, stderr = self.cli('build', *options)
                self.assertEqual(result, code, stderr)
                self.assertIn(diagnostic, stderr)
                receipt = json.loads((self.run / 'receipt.json').read_text())
                if not code:
                    self.assertEqual(receipt['verified_figures'], {relative: figure})
                    self.assertEqual(receipt['consumed_project_files'][relative], figure['output']['sha256'])

    def declared_input(self, path):
        manifest = self.base / 'external.json'
        manifest.write_text(json.dumps([{'id': 'study-input', 'path': str(path),
                                        'sha256': latex.digest(path)}]))
        return manifest

    def test_external_first_pass_and_symlink_require_declaration(self):
        target = self.base / 'outside data.csv'
        target.write_text('x,y')
        alias = self.project / 'src/data.csv'
        alias.symlink_to(target)
        manifest = self.declared_input(target)

        def first_pass(*args):
            self.fake_compile(*args)
            self.record_pass('tex', [alias], 1)
            self.record_pass('tex', [args[1] / 'main.tex'])
            return 0

        with patch.object(latex, 'execute', side_effect=first_pass):
            code, _, diagnostic = self.cli('build')
            self.assertEqual(code, 1)
            self.assertIn('tex input ' + str(alias), diagnostic)
            self.assertIn('undeclared external dependency', diagnostic)
            self.assertEqual(self.cli('build', '--external-inputs', str(manifest))[0], 0)
        raw = json.loads((self.run / 'receipt.json').read_text())
        self.assertEqual(raw['consumed_external_inputs'], {'study-input': latex.digest(target)})
        self.assertEqual(len(raw['pass_evidence']), 6)
        target.write_text('changed')
        with patch.object(latex, 'execute') as execute:
            code, _, diagnostic = self.cli('build', '--external-inputs', str(manifest))
        self.assertEqual(code, 2)
        self.assertIn('external input hash mismatch', diagnostic)
        execute.assert_not_called()

    def test_biber_external_bibliography_is_classified(self):
        outside = self.base / 'external.bib'
        outside.write_text('bibliography')
        manifest = self.declared_input(outside)

        def compile_document(*args):
            self.fake_compile(*args)
            (self.run / 'main.blg').write_text(f"INFO - Found BibTeX data source '{outside}'\n")
            self.record_pass('biber', list(latex.biber_paths(self.run / 'main.blg', args[1])), 2)
            return 0

        with patch.object(latex, 'execute', side_effect=compile_document):
            code, _, diagnostic = self.cli('build')
            self.assertEqual(code, 1)
            self.assertIn(f'biber input {outside}: undeclared external dependency', diagnostic)
            self.assertEqual(self.cli('build', '--external-inputs', str(manifest))[0], 0)
        raw = json.loads((self.run / 'receipt.json').read_text())
        self.assertEqual(raw['consumed_external_inputs']['study-input'], latex.digest(outside))

    def test_changed_unlisted_extension_fails_build(self):
        source = self.project / 'src/measurements.csv'
        source.write_text('initial')

        def compile_document(*args):
            self.fake_compile(*args)
            self.record_pass('tex', [source], 1)
            # Rename changes file identity even when replacement bytes match.
            replacement = source.with_suffix('.tmp')
            replacement.write_bytes(source.read_bytes())
            replacement.replace(source)
            return 0

        with patch.object(latex, 'execute', side_effect=compile_document):
            code, _, diagnostic = self.cli('build')
        self.assertEqual(code, 1)
        self.assertIn('measurements.csv: input changed during compilation', diagnostic)

    def test_capture_archives_each_tex_pass_and_blocks_remote_bibliography(self):
        run = self.base / 'capture'
        (run / 'passes').mkdir(parents=True)
        fls = run / 'main.fls'
        for filename in ('first.dat', 'second.dat'):
            def fake_tool(*args):
                fls.write_text(f'PWD {self.project}\nINPUT {filename}\n')
                return subprocess.CompletedProcess([], 0)
            with patch.object(latex.subprocess, 'run', side_effect=fake_tool):
                self.assertEqual(latex.capture_tool(['tex', str(run), 'main', 'fixture']), 0)
        for index, filename in enumerate(('first.dat', 'second.dat'), 1):
            evidence = run / 'passes' / f'{index:04d}-tex.fls'
            self.assertIn(f'INPUT {filename}', evidence.read_text())
        (run / 'main.bcf').write_text(
            '<controlfile><datasource type="file" datatype="bibtex">https://example.org/a.bib'
            '</datasource></controlfile>')
        with patch.object(latex.subprocess, 'run') as execute, redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(latex.capture_tool(['biber', str(run), 'main', 'fixture']), 1)
        execute.assert_not_called()
        self.assertIn('remote bibliography source refused', stderr.getvalue())
        self.assertTrue((run / 'passes/0003-biber.bcf').is_file())

    def test_bibliography_none_skips_biber_and_checks_receipt(self):
        (self.root / 'biber').unlink()

        def no_bibliography(command, *args):
            self.assertIn('-bibtex-', command)
            self.fake_compile(command, *args)
            for path in (self.run / 'passes').glob('*-biber.*'):
                path.unlink()
            for name in ('main.blg', 'main.bbl'):
                (self.run / name).unlink()
            return 0

        args = ('--bibliography', 'none')
        self.assertEqual(self.cli('preflight', *args)[0], 0)
        with patch.object(latex, 'execute', side_effect=no_bibliography):
            self.assertEqual(self.cli('build', *args)[0], 0)
        raw = json.loads((self.run / 'receipt.json').read_text())
        self.assertEqual(raw['bibliography'], 'none')
        self.assertNotIn('biber', raw['tool_identities'])
        self.assertEqual(self.cli('check', '--output', str(self.run))[0], 0)
        self.assertEqual(self.cli('seal-cache', '--output', str(self.run))[0], 0)

        def unexpected_bibliography(*args):
            no_bibliography(*args)
            (self.run / 'main.bcf').write_text('unexpected bibliography')
            return 0

        with patch.object(latex, 'execute', side_effect=unexpected_bibliography):
            code, _, diagnostic = self.cli('build', '--bibliography', 'none')
        self.assertEqual(code, 1)
        self.assertIn('document requests bibliography processing', diagnostic)

    def test_version_one_receipt_and_cache_still_work(self):
        with patch.object(latex, 'execute', side_effect=self.fake_compile):
            self.assertEqual(self.cli('build')[0], 0)
            baseline = self.run
            path = baseline / 'receipt.json'
            receipt = json.loads(path.read_text())
            receipt['version'] = 1
            receipt.pop('bibliography')
            receipt['artifacts'] = {name: value for name, value in receipt['artifacts'].items()
                                    if not name.startswith('passes/')}
            path.write_text(json.dumps(receipt))
            self.assertEqual(self.cli('check', '--output', str(baseline))[0], 0)
            self.assertEqual(self.cli('seal-cache', '--output', str(baseline))[0], 0)
            self.assertEqual(self.cli('build', '--cache-from', str(baseline))[0], 0)
        self.assertEqual(json.loads((self.run / 'receipt.json').read_text())['cache_baseline_receipt_version'], 1)

    def test_missing_or_stale_figure_refuses_before_compile(self):
        path, figure = self.new_figure()
        with patch.object(latex, 'execute') as execute:
            result, _, stderr = self.cli('build', '--figure-receipt', str(path.with_name('absent.json')))
            self.assertEqual(result, 2)
            self.assertIn('absent.json', stderr)
            for role in ('generator', 'data', 'output'):
                target = self.project / figure[role]['path']
                original = target.read_bytes()
                target.write_text('changed')
                result, _, stderr = self.cli('build', '--figure-receipt', str(path))
                self.assertEqual(result, 2)
                self.assertIn('stale figure ' + role, stderr)
                target.write_bytes(original)
        execute.assert_not_called()
        self.assertFalse((self.project / 'build').exists())

    def test_final_logs_preserve_specific_diagnostics_in_failure(self):
        tex = ('Package biblatex Warning: Please (re)run Biber on the file:\n'
               "LaTeX Warning: Citation 'missing' on page 1 undefined on input line 5.\n"
               "LaTeX Warning: Reference 'missing' on page 1\n"
               '  undefined on input line 7.\n'
               'LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.\n'
               'Missing character: There is no Q in font Fixture!\n')
        biber = "[4] Biber.pm:8> ERROR - Cannot find 'bib/missing.bib'!\n"
        def broken(*args):
            self.fake_compile(*args)
            (self.run / 'main.log').write_text(tex)
            (self.run / 'main.blg').write_text(biber)
            args[3].write_text('Bib file(s) not found in search path:\n  bib/missing.bib\n')
            return 1
        with patch.object(latex, 'execute', side_effect=broken):
            code, _, stderr = self.cli('build')
        self.assertEqual(code, 1)
        receipt = json.loads((self.run / 'receipt.json').read_text())
        for message in ('Please (re)run Biber', "Citation 'missing'", "Reference 'missing'",
                        'Label(s) may have changed', 'Missing character', "Cannot find 'bib/missing.bib'",
                        'Bib file(s) not found in search path:'):
            self.assertIn(message, stderr)
            self.assertTrue(any(message in error for error in receipt['errors']), message)
        self.assertEqual((self.run / 'main.log').read_text(), tex)
        self.assertEqual((self.run / 'main.blg').read_text(), biber)

    def test_pdf_metadata_requires_parser_and_rejects_malformed_output(self):
        path = self.base / 'broken.pdf'
        path.write_bytes(b'not a PDF')
        with self.assertRaisesRegex(ValueError, 'invalid PDF header'):
            latex.pdf_metadata(path, self.root / 'lualatex', 1)
        path.write_bytes(b'%PDF-1.7\ntruncated')
        with self.assertRaisesRegex(ValueError, 'missing PDF end marker'):
            latex.pdf_metadata(path, self.root / 'lualatex', 1)
        path.write_bytes(b'%PDF-1.7\n%%EOF\n')
        reader = self.root / 'lualatex'
        reader.write_text('#!/bin/sh\nexit 1\n')
        with self.assertRaisesRegex(ValueError, 'LuaLaTeX could not read PDF'):
            latex.pdf_metadata(path, reader, 1)

    def test_check_validates_artifacts_and_leaves_run_unchanged(self):
        with patch.object(latex, 'execute', side_effect=self.fake_compile):
            self.assertEqual(self.cli('build')[0], 0)
        args = ('--output', str(self.run))
        before = {path: path.stat().st_mtime_ns for path in self.run.rglob('*')}
        code, stdout, _ = self.cli('check', *args)
        self.assertEqual((code, json.loads(stdout)), (0, {'errors': []}))
        self.assertEqual({path: path.stat().st_mtime_ns for path in self.run.rglob('*')}, before)
        raw = json.loads((self.run / 'receipt.json').read_text())
        self.assertEqual(raw['version'], 2)
        self.assertEqual(raw['entry'], 'src/main.tex')
        self.assertEqual(raw['pdf_metadata'], {'version': '1.7', 'page_count': 1})
        for name in raw['artifacts']:
            path = self.run / name
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            code, stdout, _ = self.cli('check', *args)
            self.assertEqual(code, 1)
            self.assertIn('artifact hash mismatch: ' + name, json.loads(stdout)['errors'])
            path.write_bytes(original)

    def test_legacy_receipt_still_checks_pdf_hash_and_logs(self):
        with patch.object(latex, 'execute', side_effect=self.fake_compile):
            self.assertEqual(self.cli('build')[0], 0)
        path = self.run / 'receipt.json'
        pdf = self.run / 'main.pdf'
        path.write_text(json.dumps({'exit_code': 0, 'pdf_sha256': latex.digest(pdf)}))
        (self.run / 'console.log').unlink()
        args = ('--output', str(self.run))
        self.assertEqual(self.cli('check', *args)[0], 0)
        (self.run / 'main.log').write_text('LaTeX Warning: There were undefined references.')
        pdf.write_bytes(b'changed')
        code, stdout, _ = self.cli('check', *args)
        self.assertEqual(code, 1)
        self.assertIn('undefined references', stdout)
        self.assertIn('artifact hash mismatch: main.pdf', stdout)

    def test_timeout_keeps_partial_evidence(self):
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
        self.assertEqual(list(latex.recorder_paths(fls)), [path.resolve()])

    def test_generated_dependency_sources_do_not_contaminate_project_identity(self):
        for name in ('build', '.tools'):
            path = self.project / name
            path.mkdir()
            (path / 'unrelated.tex').write_text('generated dependency source')
        self.assertEqual(set(latex.project_sources(self.project, latex.snapshot_project(self.project))), {'src/main.tex'})

    def test_entry_name_is_not_interpreted_as_a_latexmk_option(self):
        (self.project / 'src/-e.tex').write_text('fixture')
        def execute(command, *args):
            self.assertEqual(command[-1], './-e.tex')
            return 1
        with patch.object(latex, 'execute', side_effect=execute):
            self.assertEqual(latex.main(['build', *self.args, '--entry', 'src/-e.tex']), 1)

    def test_real_timeout_preserves_partial_console(self):
        import sys
        console = self.base / 'timeout.log'
        with self.assertRaises(subprocess.TimeoutExpired):
            latex.execute([sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(10)'],
                          self.base, {'PATH': '/usr/bin:/bin'}, console, 1)
        self.assertEqual(console.read_text().strip(), 'started')


if __name__ == '__main__':
    unittest.main()

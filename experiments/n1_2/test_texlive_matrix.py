import unittest
import texlive_matrix
import run
from pathlib import Path
import tempfile
from unittest.mock import patch


class MatrixExitTests(unittest.TestCase):
    def test_generated_build_outputs_are_not_fixture_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'article/src').mkdir(parents=True)
            (root / 'article/build').mkdir()
            (root / 'article/src/main.tex').write_text('source')
            (root / 'article/build/main.pdf').write_text('old output')
            with patch.object(run, 'HERE', root):
                inventory = run.fixture_inputs()
            self.assertEqual(set(inventory), {'article/src/main.tex'})

    def test_success_includes_expected_dependency_refusal(self):
        cases = [{'exit_code': 0, 'expected_exit_code': 0},
                 {'exit_code': 2, 'expected_exit_code': 2}]
        self.assertEqual(texlive_matrix.matrix_exit(cases), 0)

    def test_failed_or_empty_matrix_cannot_pass(self):
        self.assertEqual(texlive_matrix.matrix_exit([]), 1)
        self.assertEqual(texlive_matrix.matrix_exit([
            {'exit_code': 1, 'expected_exit_code': 0}]), 1)

    def test_network_tool_errors_are_not_accepted_as_denial(self):
        self.assertEqual(texlive_matrix.matrix_exit([
            {'exit_code': 1, 'expected_exit_code': [6, 7, 28]}]), 1)
        self.assertEqual(texlive_matrix.matrix_exit([
            {'exit_code': None, 'expected_exit_code': 0}]), 1)

    def test_linux_boundary_creates_namespace_and_drops_privileges(self):
        with patch.object(texlive_matrix.platform, 'system', return_value='Linux'):
            command = texlive_matrix.network_prefix()
        self.assertIn('--net', command)
        self.assertIn('--reuid', command)
        self.assertIn('--no-new-privs', command)

    def test_unknown_platform_has_no_permissive_network_fallback(self):
        with patch.object(texlive_matrix.platform, 'system', return_value='unsupported'):
            with self.assertRaises(ValueError):
                texlive_matrix.network_prefix()


if __name__ == '__main__':
    unittest.main()

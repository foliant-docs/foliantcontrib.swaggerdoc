import os

from pathlib import Path
from foliant_test.preprocessor import PreprocessorTestFramework
from unittest import TestCase

def rel_name(path:str):
    return os.path.join(os.path.dirname(__file__), path)

def data_file_content(path: str) -> str:
    '''read data file by path relative to this module and return its contents'''
    with open(rel_name(path), encoding='utf8') as f:
        return f.read()

class TestSwaggerdoc(TestCase):
    def setUp(self):
        self.ptf = PreprocessorTestFramework('swaggerdoc')
        self.ptf.context['project_path'] = Path('.')
        self.ptf.options = {
            'json_path': rel_name(os.path.join('data', 'petstore_spec.json')),
        }

    def test_petstore_spec(self):
        input_content = data_file_content(os.path.join('data', 'input', 'test1.md'))
        expected_content = data_file_content(os.path.join('data', 'expected', 'test1.md'))
        self.ptf.test_preprocessor(
            input_mapping = {
                'index.md': input_content
            },
            expected_mapping = {
                'index.md': expected_content
            }
        )
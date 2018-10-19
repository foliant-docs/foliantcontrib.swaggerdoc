'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from Swagger.
'''

import os
import traceback
import json
import yaml
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import HTTPError, URLError
from distutils.dir_util import remove_tree
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_filename
from subprocess import run, PIPE, STDOUT
from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    tags = ('swaggerdoc',)

    defaults = {
        'json_url': '',
        'json_path': '',
        'mode': 'jinja',
        'template': 'swagger.j2'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('swaggerdoc')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

        self._env = \
            Environment(loader=FileSystemLoader(str(self.project_path)),
                        extensions=["jinja2.ext.do"])

        self._modes = {'jinja': self._process_jinja,
                       'widdershins': self._process_widdershins}

        self._swagger_tmp = self.project_path / '.swaggercache/'
        if self._swagger_tmp.exists():
            remove_tree(self._swagger_tmp)
        os.makedirs(self._swagger_tmp)

        self._counter = 0

    def _gather_jsons(self,
                      url: str,
                      path_: str) -> Path:
        """
        Download all swagger JSONs from the url; copy all files into the
        temp dir and return list with files in the same order they are declared
        in options. (first url, then path)
        """

        if url:
            try:
                self._counter += 1
                filename = self._swagger_tmp / f'swagger{self._counter}.json'
                urlretrieve(url, filename)
                return filename
            except (HTTPError, URLError):
                err = traceback.format_exc()
                self.logger.debug(f'Cannot retrieve swagger json from url {url}.\n{err}')
                print(f'\nCannot retrieve swagger json from url {url}. Skipping.')

        if path_:
            self._counter += 1
            file = self.project_path / path_
            dest = self._swagger_tmp / f'swagger{self._counter}.json'
            if not file.exists():
                self.logger.debug(f'{file} not found')
                print(f"\nCan't find file {file}. Skipping.")
            else:  # file exists
                copyfile(str(file), str(dest))
                return dest

    def _process_jinja(self,
                       json_: Path or str,
                       tag_options: dict) -> str:
        """Process swagger.json with jinja and return the resulting string"""

        data = json.load(open(json_, encoding="utf8"))

        template = tag_options.get('template', self.options['template'])
        if template == self.defaults['template'] and\
                not os.path.exists(self.project_path / template):
            copyfile(resource_filename(__name__, 'template/' +
                                       self.defaults['template']),
                     self.project_path / template)
        return self._to_md(data, template)

    def _process_widdershins(self,
                             json_: Path or str,
                             tag_options: dict) -> str:
        """
        Process swagger.json with widdershins and return the resulting string
        """

        environment = tag_options.get('environment') or \
            self.options.get('environment')
        if environment:
            if type(environment) is str:
                env_str = f'--environment {environment}'
            else:  # inline config in foliant.yaml
                env_yaml = str(self._swagger_tmp / 'emv.yaml')
                with open(env_yaml, 'w') as f:
                    f.write(yaml.dump(environment))
                env_str = f'--environment {env_yaml}'
        else:  # not environment
            env_str = ''
        in_str = str(json_)
        out_str = str(self._swagger_tmp / f'swagger{self._counter}.md')
        run(
            f'widdershins {env_str} {in_str} -o {out_str}',
            shell=True,
            check=True,
            stdout=PIPE,
            stderr=STDOUT
        )
        return open(out_str).read()

    def _to_md(self,
               data: dict,
               template: str) -> str:
        """generate markdown string from 'data' dict using jinja 'template'"""

        try:
            template = self._env.get_template(template)
            result = template.render(swagger_data=data, dumps=json.dumps)
        except Exception as e:
            print(f'\nFailed to render doc template {template}:', e)
            info = traceback.format_exc()
            self.logger.debug(f'Failed to render doc template:\n\n{info}')
            return ''
        return result

    def _gen_docs(self,
                  filters: dict,
                  draw: bool,
                  doc_template: str,
                  scheme_template: str) -> str:
        data = self._collect_datasets(filters, draw)
        docs = self._to_md(data, doc_template)
        if draw:
            docs += '\n\n' + self._to_diag(data, scheme_template)
        return docs

    def process_pgsqldoc_blocks(self, content: str) -> str:
        def _sub(block: str) -> str:
            if block.group('options'):
                tag_options = self.get_options(block.group('options'))
            else:
                tag_options = {}

            json_url = tag_options.get('json_url') or self.options['json_url']
            json_path = tag_options.get('json_path') or self.options['json_path']

            if not (json_path or json_url):
                print('\nError: No swagger json specified!')
                return ''

            mode = tag_options.get('mode') or self.options['mode']
            if mode not in self._modes:
                print(f'\nError: Unrecognised mode {mode}.'
                      f' Should be one of {self._modes}')
                return ''

            json_ = self._gather_jsons(json_url, json_path)
            if not json_:
                raise RuntimeError("No valid swagger.json specified")

            return self._modes[mode](json_, tag_options)
        return self.pattern.sub(_sub, content)

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing Markdown file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                content = markdown_file.read()

            with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                markdown_file.write(self.process_pgsqldoc_blocks(content))

        self.logger.info('Preprocessor applied')

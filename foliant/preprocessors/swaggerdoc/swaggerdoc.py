'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from Swagger.
'''

import os
import traceback
import json
from urllib.request import urlretrieve
from urllib.error import HTTPError
from distutils.dir_util import remove_tree
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_filename
from foliant.preprocessors.base import BasePreprocessor


class Preprocessor(BasePreprocessor):
    tags = ('swaggerdoc',)

    defaults = {
        'swagger_json_urls': [],
        'swagger_json_paths': [],
        'template': 'swagger.j2'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('swaggerdoc')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

        self._env = \
            Environment(loader=FileSystemLoader(str(self.project_path)),
                        extensions=["jinja2.ext.do"])

        self._swagger_tmp = self.project_path / '.swagger/'
        if self._swagger_tmp.exists():
            remove_tree(self._swagger_tmp)
        os.makedirs(self._swagger_tmp)

        self._counter = 0

    def _gather_jsons(self,
                      urls: list,
                      paths: list) -> list:
        """
        Download all swagger JSONs from the urls list; copy all files into the
        temp dir and return list with files in the same order they are declared
        in options. (first urls, then paths)
        """

        result = []

        for url in urls:
            try:
                self._counter += 1
                filename = self._swagger_tmp / f'swagger{self._counter}.json'
                urlretrieve(url, filename)
                result.append(filename)
            except HTTPError:
                err = traceback.format_exc()
                self.logger.debug(f'Cannot retrieve swagger json from url {url}.\n{err}')
                print(f'Cannot retrieve swagger json from url {url}.')

        for path_ in paths:
            self._counter += 1
            file = self.project_path / path_
            dest = self._swagger_tmp / f'swagger{self._counter}.json'
            if not file.exists:
                self.logger.debug(f'{file} not found')
                print(f"Can't find file {file}. Skipping.")
                continue
            copyfile(str(file), str(dest))
            result.append(dest)
        return result

    def _read_jsons(self,
                    jsons: list) -> dict:
        """
        Subsequently read each JSON-file from jsons param and unpack its
        contents into result dict.

        jsons - list with paths to json files
        """
        result = {}
        _ = [result.update(json.load(open(i, encoding="utf8"))) for i in jsons]
        return result

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

            if 'swagger_json_urls' in tag_options:
                json_urls = [j.strip() for j in
                             tag_options['swagger_json_urls'].split(',')]
            else:
                json_urls = self.options['swagger_json_urls']
                if type(json_urls) == str:
                    json_urls = [json_urls]

            if 'swagger_json_paths' in tag_options:
                json_paths = [j.strip() for j in
                              tag_options['swagger_json_paths'].split(',')]
            else:
                json_paths = self.options['swagger_json_paths']
                if type(json_paths) == str:
                    json_paths = [json_paths]

            if not (json_paths or json_urls):
                print(' Error: No swagger json specified!')
                return ''

            data = self._read_jsons(self._gather_jsons(json_urls, json_paths))

            template = tag_options.get('template', self.options['template'])
            if template == self.defaults['template'] and\
                    not os.path.exists(self.project_path / template):
                copyfile(resource_filename(__name__, 'template/' +
                                           self.defaults['template']),
                         self.project_path / template)
            return self._to_md(data, template)
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

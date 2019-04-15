'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from Swagger.
'''

import os
import traceback
import json
from ruamel import yaml
from pathlib import PosixPath
from urllib.request import urlretrieve
from urllib.error import HTTPError, URLError
from distutils.dir_util import remove_tree
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_filename
from subprocess import run, PIPE

from foliant.preprocessors.base import BasePreprocessor
from foliant.utils import output


class Preprocessor(BasePreprocessor):
    tags = ('swaggerdoc',)

    defaults = {
        'json_url': '',
        'additional_json_path': '',
        'json_path': '',
        'mode': 'widdershins',
        'template': 'swagger.j2'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = self.logger.getChild('swaggerdoc')

        self.logger.debug(f'Preprocessor inited: {self.__dict__}')

        # '/' for abspaths
        self._env = \
            Environment(loader=FileSystemLoader([str(self.project_path), '/']),
                        extensions=["jinja2.ext.do"])

        self._modes = {'jinja': self._process_jinja,
                       'widdershins': self._process_widdershins}

        self._swagger_tmp = self.project_path / '.swaggercache/'
        if self._swagger_tmp.exists():
            remove_tree(self._swagger_tmp)
        os.makedirs(self._swagger_tmp)

        self._counter = 0

    def _gather_specs(self,
                      urls: list,
                      path_: PosixPath) -> PosixPath:
        """
        Download first swagger spec from the url list; copy it into the
        temp dir and return path to it. If all urls fail — check path_ and
        return it.

        Return None if everything fails
        """

        if urls:
            for url in urls:
                try:
                    filename = self._swagger_tmp / f'swagger_spec'
                    urlretrieve(url, filename)
                    return filename
                except (HTTPError, URLError):
                    err = traceback.format_exc()
                    self.logger.debug(f'Cannot retrieve swagger spec file from url {url}.\n{err}')
                    print(f'\nCannot retrieve swagger spec file from url {url}. Skipping.')

        if path_:
            dest = self._swagger_tmp / f'swagger_spec'
            if not path_.exists():
                self.logger.debug(f'{path_} not found')
                print(f"\nCan't find file {path_}. Skipping.")
            else:  # file exists
                copyfile(str(path_), str(dest))
                return dest

    def _process_jinja(self,
                       spec: PosixPath,
                       tag_options: dict) -> str:
        """Process swagger.json with jinja and return the resulting string"""
        data = yaml.safe_load(open(spec, encoding="utf8"))
        additional = tag_options.get('additional_json_path') or \
            self.options['additional_json_path']
        if additional:
            if type(additional) is str:
                additional = self.project_path / additional
            if not additional.exists():
                print(f'Additional swagger spec file {additional} is missing. Skipping')
            else:
                add = yaml.safe_load(open(additional, encoding="utf8"))
                data = {**add, **data}

        template = tag_options.get('template', self.options['template'])
        if type(template) is str:
            template = self.project_path / template
        if template == self.project_path / self.defaults['template'] and\
                not template.exists():
            copyfile(resource_filename(__name__, 'template/' +
                                       self.defaults['template']), template)
        return self._to_md(data, template)

    def _process_widdershins(self,
                             spec: PosixPath,
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
        log_path = self._swagger_tmp / 'widdershins.log'
        in_str = str(spec)
        out_str = str(self._swagger_tmp / f'swagger{self._counter}.md')
        cmd = f'widdershins {env_str} {in_str} -o {out_str}'
        self.logger.info(f'Constructed command: \n {cmd}')
        result = run(
            cmd,
            shell=True,
            check=True,
            stdout=PIPE,
            stderr=PIPE
        )
        with open(log_path, 'w') as f:
            f.write(result.stdout.decode())
            f.write('\n\n')
            f.write(result.stderr.decode())
        self.logger.info(f'Build log saved at {log_path}')
        if result.stderr:
            error_fragment = '\n'.join(result.stderr.decode().split("\n")[:3])
            self.logger.warning('Widdershins builder returned error or warning:\n'
                                f'{error_fragment}\n...\n'
                                f'Full build log at {log_path.absolute()}')
            output('Widdershins builder returned error or warning:\n'
                   f'{error_fragment}\n...\n'
                   f'Full build log at {log_path.absolute()}', self.quiet)
        return open(out_str).read()

    def _to_md(self,
               data: dict,
               template_path: PosixPath or str) -> str:
        """generate markdown string from 'data' dict using jinja 'template'"""

        try:
            o = open(str(template_path), 'r')
            template = self._env.get_template(str(template_path))
            result = template.render(swagger_data=data, dumps=json.dumps)
        except Exception as e:
            info = traceback.format_exc()
            print(f'\nFailed to render doc template {template_path}:', info)
            self.logger.debug(f'Failed to render doc template:\n\n{info}')
            return ''
        return result

    def process_swaggerdoc_blocks(self, content: str) -> str:
        def _sub(block: str) -> str:
            if block.group('options'):
                tag_options = self.get_options(block.group('options'))
            else:
                tag_options = {}

            spec_url = tag_options.get('json_url') or self.options['json_url']
            if spec_url and type(spec_url) is str:
                spec_url = [spec_url]
            spec_path = tag_options.get('json_path') or self.options['json_path']
            if spec_path and type(spec_path) is str:
                spec_path = self.project_path / spec_path

            if not (spec_path or spec_url):
                print('\nError: No swagger spec file specified!')
                return ''

            mode = tag_options.get('mode') or self.options['mode']
            if mode not in self._modes:
                print(f'\nError: Unrecognised mode {mode}.'
                      f' Should be one of {self._modes}')
                return ''

            spec = self._gather_specs(spec_url, spec_path)
            if not spec:
                raise RuntimeError("No valid swagger spec file specified")

            return self._modes[mode](spec, tag_options)
        return self.pattern.sub(_sub, content)

    def apply(self):
        self.logger.info('Applying preprocessor')

        for markdown_file_path in self.working_dir.rglob('*.md'):
            self.logger.debug(f'Processing Markdown file: {markdown_file_path}')

            with open(markdown_file_path, encoding='utf8') as markdown_file:
                content = markdown_file.read()

            with open(markdown_file_path, 'w', encoding='utf8') as markdown_file:
                markdown_file.write(self.process_swaggerdoc_blocks(content))

        self.logger.info('Preprocessor applied')

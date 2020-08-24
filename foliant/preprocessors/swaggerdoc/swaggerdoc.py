'''
Preprocessor for Foliant documentation authoring tool.
Generates documentation from Swagger.
'''

import os
import traceback
import json
from ruamel import yaml
from pathlib import Path, PosixPath
from urllib.request import urlretrieve
from urllib.error import HTTPError, URLError
from distutils.dir_util import remove_tree
from shutil import copyfile
from jinja2 import Environment, FileSystemLoader
from pkg_resources import resource_filename
from subprocess import run, PIPE

from foliant.preprocessors.utils.preprocessor_ext import (BasePreprocessorExt,
                                                          allow_fail)
from foliant.preprocessors.utils.combined_options import (Options,
                                                          CombinedOptions,
                                                          validate_exists,
                                                          validate_in,
                                                          rel_path_convertor)
from foliant.utils import output


class Preprocessor(BasePreprocessorExt):
    tags = ('swaggerdoc',)

    defaults = {
        'json_url': [],  # deprecated
        'spec_url': [],
        'additional_json_path': '',
        'json_path': '',  # deprecated
        'spec_path': '',
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
        self.options = Options(self.options,
                               validators={'json_path': validate_exists,
                                           'spec_path': validate_exists})

    def _gather_specs(self,
                      urls: list,
                      path_: str or PosixPath or None) -> PosixPath:
        """
        Download first swagger spec from the url list; copy it into the
        temp dir and return path to it. If all urls fail — check path_ and
        return it.

        Return None if everything fails
        """
        self.logger.debug(f'Gathering specs. Got list of urls: {urls}, path: {path_}')
        if urls:
            for url in urls:
                try:
                    filename = self._swagger_tmp / f'swagger_spec'
                    urlretrieve(url, filename)
                    self.logger.debug(f'Using spec from {url} ({filename})')
                    return filename
                except (HTTPError, URLError) as e:
                    self._warning(f'\nCannot retrieve swagger spec file from url {url}. Skipping.',
                                  error=e)
        local_path = Path(path_)
        if local_path:
            # dest = self._swagger_tmp / f'swagger_spec'
            if not local_path.exists():
                self._warning(f"Can't find file {path_}. Skipping.")
            else:  # file exists
                return local_path.resolve()
                # copyfile(str(path_), str(dest))
                # return dest

    def _process_jinja(self,
                       spec: PosixPath,
                       options: CombinedOptions) -> str:
        """Process swagger.json with jinja and return the resulting string"""
        self.logger.debug('Using jinja mode')
        data = yaml.safe_load(open(spec, encoding="utf8"))
        additional = options.get('additional_json_path')
        if additional:
            if not additional.exists():
                self._warning(f'Additional swagger spec file {additional} is missing. Skipping')
            else:
                add = yaml.safe_load(open(additional, encoding="utf8"))
                data = {**add, **data}
        if options.is_default('template') and not Path(options['template']).exists():
            copyfile(
                resource_filename(
                    __name__,
                    'template/' + self.defaults['template']
                ),
                options['template']
            )
        return self._to_md(data, options['template'])

    def _process_widdershins(self,
                             spec: PosixPath,
                             options: CombinedOptions) -> str:
        """
        Process swagger.json with widdershins and return the resulting string
        """

        self.logger.debug('Using widdershins mode')
        environment = options.get('environment')
        if environment:
            if isinstance(environment, str) or isinstance(environment, PosixPath):
                env_str = f'--environment {environment}'
            else:  # inline config in foliant.yaml
                env_yaml = str(self._swagger_tmp / 'env.yaml')
                with open(env_yaml, 'w') as f:
                    yaml.dump(environment, f)
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
            self._warning('Widdershins builder returned error or warning:\n'
                          f'{error_fragment}\n...\n'
                          f'Full build log at {log_path.absolute()}')
        with open(out_str) as f:
            return f.read()

    def _to_md(self,
               data: dict,
               template_path: PosixPath or str) -> str:
        """generate markdown string from 'data' dict using jinja 'template'"""

        try:
            template = self._env.get_template(str(template_path))
            result = template.render(swagger_data=data, dumps=json.dumps)
        except Exception as e:
            self._warning(f'\nFailed to render doc template {template_path}',
                          error=e)
            return ''
        return result

    @allow_fail()
    def process_swaggerdoc_blocks(self, block) -> str:
        tag_options = Options(self.get_options(block.group('options')),
                              convertors={'json_path': rel_path_convertor(self.current_filepath.parent),
                                          'spec_path': rel_path_convertor(self.current_filepath.parent),
                                          'additional_json_path': rel_path_convertor(self.current_filepath.parent)})
        options = CombinedOptions(options={'config': self.options,
                                           'tag': tag_options},
                                  priority='tag',
                                  required=[('json_url',),
                                            ('json_path',),
                                            ('spec_url',),
                                            ('spec_path',)],
                                  validators={'mode': validate_in(self._modes)},
                                  defaults=self.defaults)
        self.logger.debug(f'Processing swaggerdoc tag in {self.current_filepath}')
        spec_url = options['spec_url'] or options['json_url']
        if spec_url and isinstance(spec_url, str):
            spec_url = [spec_url]
        spec_path = options['spec_path'] or options['json_path']
        spec = self._gather_specs(spec_url, spec_path)
        if not spec:
            raise RuntimeError("No valid swagger spec file specified")

        return self._modes[options['mode']](spec, options)

    def apply(self):
        self._process_tags_for_all_files(func=self.process_swaggerdoc_blocks)
        self.logger.info('Preprocessor applied')

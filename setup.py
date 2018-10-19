from setuptools import setup


SHORT_DESCRIPTION = 'Documentation generator for Swagger API'

try:
    with open('README.md', encoding='utf8') as readme:
        LONG_DESCRIPTION = readme.read()

except FileNotFoundError:
    LONG_DESCRIPTION = SHORT_DESCRIPTION


setup(
    name='foliantcontrib.swaggerdoc',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    version='1.1.0',
    author='Daniil Minukhin',
    author_email='ddddsa@gmail.com',
    packages=['foliant.preprocessors.swaggerdoc'],
    package_data={'foliant.preprocessors.swaggerdoc': ['template/*.j2']},
    license='MIT',
    platforms='any',
    install_requires=[
        'foliant>=1.0.5',
        'jinja2',
        'PyYAML'
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Documentation",
        "Topic :: Utilities",
    ]
)

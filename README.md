# Swagger API Docs Generator for Foliant

This preprocessor generates Markdown documentation from JSON generated by [Swagger](https://swagger.io/). It uses [Jinja2](http://jinja.pocoo.org/) templating engine or [widdershins](https://github.com/mermade/widdershins) for generating Markdown from JSON.

## Installation

```bash
$ pip install foliantcontrib.swaggerdoc
```

## Config

To enable the preprocessor, add `pgsqldoc` to `preprocessors` section in the project config:

```yaml
preprocessors:
    - swaggerdoc
```

The preprocessor has a number of options:

```yaml
preprocessors:
    - swaggerdoc:
        json_url: http://localhost/swagger.json
        json_path: swagger.json
        mode: 'jinja'
        template: swagger.j2
        environment: env.yaml

```

`json_url`
:    URL to JSON generated by Swagger. Has priority over loading json by path.

`json_path`
:    local path to JSON generated by Swagger (relative to project dir).

> If both url and path are specified — preprocessor first tries to fetch JSON from url, and then (if that fails) looks for the file on local path.

`mode`
:   Determines how the Swagger JSON would be converted to markdown. Should be one of: `jinja`, `widdershins`. Default: `jinja`

`template`
:   Only for `jinja` mode. Path to jinja-template for rendering the generated documentation. Path is relative to the project directory. If no template is specified preprocessor will use default template (and put it into project dir if it was missing). Default: `swagger.j2`

`environment`
:   Only for `widdershins` mode. Parameters for widdershins converter. You can either pass a string containing relative path to YAML or JSON file with all parameters (like in example above) or specify all parameters in YAML format under this key. More [info](https://github.com/mermade/widdershins) on widdershins parameters.

## Usage

Add a `<<swaggerdoc></swaggerdoc>` tag at the position in the document where the generated documentation should be inserted:

```markdown
# Introduction

This document contains the automatically generated documentation of our API.

<<swaggerdoc></swaggerdoc>
```

Each time the preprocessor encounters the tag `<<swaggerdoc></swaggerdoc>` it inserts the whole generated documentation text instead of it. The path or url to swagger.json are taken from foliant.yml.

You can also specify some parameters (or all of them) in the tag options:

```markdown
# Introduction

Introduction text for API documentation.

<swaggerdoc json_url="http://localhost/swagger.json"
            mode="jinja"
            template="swagger.j2">
</swaggerdoc>

<swaggerdoc json_url="http://localhost/swagger.json"
            mode="widdershins"
            environment="env.yml">
</swaggerdoc>
```

Tag parameters have the highest priority.

This way you can have documentation from several different JSON files in one foliant project (even in one md-file if you like it so).

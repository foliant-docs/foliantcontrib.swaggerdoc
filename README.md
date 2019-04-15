# Swagger API Docs Generator for Foliant

This preprocessor generates Markdown documentation from [Swagger](https://swagger.io/) spec files . It uses [Jinja2](http://jinja.pocoo.org/) templating engine or [widdershins](https://github.com/mermade/widdershins) for generating Markdown from swagger spec files.

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
        additional_json_path: tags.json
        mode: 'jinja'
        template: swagger.j2
        environment: env.yaml

```

`json_url`
:    URL to Swagger spec file. If it is a list — preprocessor takes the first url which works.

> even though the parameters are called *json*\_url and *json*\_path, yaml format is supported too. Parameters may be softly renamed in future.

`json_path`
:    Local path to Swagger spec file (relative to project dir).

> If both url and path are specified — preprocessor first tries to fetch JSON from url, and then (if that fails) looks for the file on local path.

`additional_json_path`
:    Only for `jinja` mode. Local path to swagger spec file with additional info (relative to project dir). It will be merged into original spec file, *not overriding existing fields*.

`mode`
:   Determines how the Swagger spec file would be converted to markdown. Should be one of: `jinja`, `widdershins`. Default: `widdershins`

> `jinja` mode is deprecated. It may be removed in future

`template`
:   Only for `jinja` mode. Path to jinja-template for rendering the generated documentation. Path is relative to the project directory. If no template is specified preprocessor will use default template (and put it into project dir if it was missing). Default: `swagger.j2`

`environment`
:   Only for `widdershins` mode. Parameters for widdershins converter. You can either pass a string containing relative path to YAML or JSON file with all parameters (like in example above) or specify all parameters in YAML format under this key. [More info](https://github.com/mermade/widdershins) on widdershins parameters.

## Usage

Add a `<<swaggerdoc></swaggerdoc>` tag at the position in the document where the generated documentation should be inserted:

```markdown
# Introduction

This document contains the automatically generated documentation of our API.

<<swaggerdoc></swaggerdoc>
```

Each time the preprocessor encounters the tag `<<swaggerdoc></swaggerdoc>` it inserts the whole generated documentation text instead of it. The path or url to Swagger spec file are taken from foliant.yml.

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

This way you can have documentation from several different Swagger spec files in one foliant project (even in one md-file if you like it so).

## Customizing output

### Jinja

> `jinja` mode is deprecated. It may be removed in future

In `jinja` mode the output markdown is generated by the [Jinja2](http://jinja.pocoo.org/) template. In this template all fields from Swagger spec file are available under the dictionary named `swagger_data`.

To customize the output just supply a template which suits your needs. If you wish to use the default template as a starting point, build the foliant project with `swaggerdoc` preprocessor turned on. After the first build the default template will appear in your foliant project dir under name `swagger.j2`.

### Widdershins

In `widdershins` mode the output markdown is generated by [widdershins](https://github.com/mermade/widdershins) Node.js application. It supports customizing the output with [doT.js](https://github.com/olado/doT) templates.

1. Clone the original widdershins [repository](https://github.com/mermade/widdershins) and modify the templates located in one of the subfolders in the **templates** folder.
2. Save the modified templates somewhere near your foliant project.
3. Specify the path to modified templates in the `user_templates` field of the `environment` configuration. For example, like this:

```yaml
preprocessors:
    - swaggerdoc:
        json_path: swagger.yml
        environment:
            user_templates: !path ./widdershins_templates/
```

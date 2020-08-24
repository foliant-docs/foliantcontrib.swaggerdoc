# 1.2.3

- Fix: build failed when spec referenced to other files with $ref.

# 1.2.2

- Fix spec path issue.
- Fix: jinja mode default template wansn't copied.

# 1.2.0

- Add `spec_path` and `spec_url` parameters.
- All path tag parameters are now loaded relative to current file.
- Better logging and error reporting

# 1.1.3

- Fix issues with json and yaml. All spec files are now loaded with yaml loader.
- Change PyYAML to ruamel.yaml
- jinja mode is deprecated, widdershins is the default mode

# 1.1.2

- Bug fixes
- All path parameters in config now accept either strings or !path strings

# 1.1.1

- Add 'additional_json_path' param for jinja mode
- Add support for several json_urls

# 1.1.0

- Change parameter names and behavior uncompatible with 1.0.0
- Add conversion to md with widdershins
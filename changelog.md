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
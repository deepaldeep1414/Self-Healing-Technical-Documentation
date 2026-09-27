# Configuration

## Loading Config

Use `load_configuration()` to read a YAML config file from disk. It takes a single
`path` argument and returns a dict.

## Validating Config

Use `ConfigValidator.validate()` to check that a loaded config has all required
top-level keys (`name` and `version`).

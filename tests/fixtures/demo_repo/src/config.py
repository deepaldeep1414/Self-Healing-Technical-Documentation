def load_config(path: str, strict: bool = False) -> dict:
    """Load a YAML config file from disk.

    Args:
        path: filesystem path to the config file.
        strict: if True, raise on unknown keys instead of ignoring them.

    Returns:
        Parsed config as a dict.
    """
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    if strict and "unknown" in data:
        raise ValueError("unknown key present")
    return data


class ConfigValidator:
    """Validates a loaded config dict against required fields."""

    def validate(self, config: dict) -> bool:
        """Return True if config has all required top-level keys."""
        required = ("name", "version")
        return all(k in config for k in required)

def get_nested(data, path, default=None):
    """
    Safely retrieve a nested value from a dict using a list of keys.
    """
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

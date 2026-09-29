import yaml

def load_config(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def get_value(key, default=None):
    loaded_config = load_config('config.yml')
    keys = key.split('.')
    for k in keys:
        if isinstance(loaded_config, dict) and k in loaded_config:
            loaded_config = loaded_config[k]
        else:
            return default
    return loaded_config.get(key, default) if isinstance(loaded_config, dict) else loaded_config
import os
import shutil
import yaml

_SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.environ.get('PATHMIND_DATA_DIR', _SOURCE_DIR)
CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')
CONFIG_EXAMPLE_PATH = os.path.join(_SOURCE_DIR, 'config.yaml.example')

DEFAULT_CONFIG = {
    'obsidian': {
        'vault_path': '',
        'products_folder': 'Products',
    },
    'ai': {
        'base_url': 'https://api.openai.com/v1',
        'api_key': '',
        'model': 'gpt-4o',
        'max_tokens': 4096,
        'temperature': 0.7,
    },
    'sync': {
        'instance_id': '',
        'instance_name': 'default',
        'backup_keep_days': 3,
    },
    'server': {
        'host': '127.0.0.1',
        'port': 5000,
        'debug': True,
    },
    'recording': {
        'hotkey_start': '',
        'hotkey_stop': '',
        'snipaste_path': '',
    },
}


class ConfigManager:
    def __init__(self):
        self._config = None

    def load(self):
        if not os.path.exists(CONFIG_PATH):
            if os.path.exists(CONFIG_EXAMPLE_PATH):
                shutil.copy(CONFIG_EXAMPLE_PATH, CONFIG_PATH)
            else:
                self._config = DEFAULT_CONFIG.copy()
                self.save(self._config)
                return self._config

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}

        # Merge with defaults for missing keys
        for section, defaults in DEFAULT_CONFIG.items():
            if section not in self._config:
                self._config[section] = defaults
            elif isinstance(defaults, dict):
                for key, value in defaults.items():
                    if key not in self._config[section]:
                        self._config[section][key] = value

        return self._config

    def save(self, data):
        self._config = data
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def get(self):
        if self._config is None:
            self.load()
        return self._config

    def get_obsidian_config(self):
        config = self.get()
        return config.get('obsidian', {})

    def get_ai_config(self):
        config = self.get()
        return config.get('ai', {})

    def get_recording_config(self):
        config = self.get()
        return config.get('recording', {})

    def get_safe_config(self):
        """Return config with api_key masked for frontend display."""
        config = self.get()
        import copy
        safe = copy.deepcopy(config)
        api_key = safe.get('ai', {}).get('api_key', '')
        if api_key and len(api_key) > 8:
            safe['ai']['api_key'] = api_key[:4] + '****' + api_key[-4:]
        elif api_key:
            safe['ai']['api_key'] = '****'
        return safe


config_manager = ConfigManager()

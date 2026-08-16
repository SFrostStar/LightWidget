import sys
import os
import json
import copy
from .crypto import encrypt_value, decrypt_value, DATA_DIR

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "telegram": {
        "api_id": "",
        "api_hash": "",
        "phone": "",
        "bot_username": "dtek_odeski_elektromerezhi_bot",
        "filter_address": "",
        "auto_connect": False
    },
    "account_number": "",
    "server": {
        "host": "0.0.0.0",
        "port": 8088,
        "enabled": True
    },
    "appearance": {
        "theme": "midnight",
        "accent": "blue",
        "show_seconds": True,
        "show_pulse": True
    },
    "notifications": {
        "sound": True,
        "banner": True,
        "macos_sound": True,
        "macos_banner": True
    }
}

class ConfigManager:
    def __init__(self, filepath=CONFIG_PATH):
        self.filepath = filepath
        self.config = self.load()

    def _decrypt_cfg(self, cfg: dict) -> dict:
        if not isinstance(cfg, dict):
            return cfg
        if "account_number" in cfg:
            cfg["account_number"] = decrypt_value(cfg["account_number"])
        if "telegram" in cfg and isinstance(cfg["telegram"], dict):
            tg = cfg["telegram"]
            if "filter_address" in tg:
                tg["filter_address"] = decrypt_value(tg["filter_address"])
            if "phone" in tg:
                tg["phone"] = decrypt_value(tg["phone"])
            if "api_hash" in tg:
                tg["api_hash"] = decrypt_value(tg["api_hash"])
        return cfg

    def _encrypt_cfg(self, cfg: dict) -> dict:
        out = copy.deepcopy(cfg)
        if "account_number" in out and out["account_number"]:
            out["account_number"] = encrypt_value(str(out["account_number"]))
        if "telegram" in out and isinstance(out["telegram"], dict):
            tg = out["telegram"]
            if "filter_address" in tg and tg["filter_address"]:
                tg["filter_address"] = encrypt_value(str(tg["filter_address"]))
            if "phone" in tg and tg["phone"]:
                tg["phone"] = encrypt_value(str(tg["phone"]))
            if "api_hash" in tg and tg["api_hash"]:
                tg["api_hash"] = encrypt_value(str(tg["api_hash"]))
        return out

    def load(self):
        if not os.path.exists(self.filepath):
            self.save(DEFAULT_CONFIG)
            return copy.deepcopy(DEFAULT_CONFIG)
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data = self._decrypt_cfg(data)
                cfg = copy.deepcopy(DEFAULT_CONFIG)
                for k, v in data.items():
                    if isinstance(v, dict) and k in cfg:
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
                return cfg
        except Exception:
            return copy.deepcopy(DEFAULT_CONFIG)

    def save(self, data=None):
        if data is not None:
            self.config = data
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        encrypted_data = self._encrypt_cfg(self.config)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(encrypted_data, f, ensure_ascii=False, indent=2)

    def update(self, new_data: dict):
        def _deep_update(target, src):
            for k, v in src.items():
                if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                    _deep_update(target[k], v)
                else:
                    target[k] = v
        _deep_update(self.config, new_data)
        self.save()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

import json
import os

class ConfigRepository:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self._ensure_config()

    def _ensure_config(self):
        if not os.path.exists(self.config_path):
            self.save_config({"tibia_log_dir": ""})

    def get_config(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_config(self, data):
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)

    def get_log_dir(self):
        return self.get_config().get("tibia_log_dir", "")

    def set_log_dir(self, path):
        data = self.get_config()
        data["tibia_log_dir"] = path
        self.save_config(data)

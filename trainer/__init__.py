import os
import json

import sys
from cyber_trainer.settings import BASE_DIR


# Load cases settings
class SettingsReader:
    def __init__(self, settings_dir=os.path.join(BASE_DIR, "trainer", "cases"), auto_load=True):
        self._settings_dir = settings_dir
        self._settings = {}
        if auto_load:
            self.load_settings()

    def load_file(self, json_file):
        with open(os.path.join(self._settings_dir, json_file)) as f:
            # Create a setting instance with the json file content
            self._settings[os.path.splitext(json_file)[0]] = json.load(f)

    def load_settings(self):
        # Load all settings file contained in the settings directory
        for f in os.listdir(self._settings_dir):
            if f.endswith(".json"):
                self.load_file(f)

    def get(self, setting_name):
        # Return the setting name
        return self._settings.get(setting_name)


# Create the settings reader
sr = SettingsReader()

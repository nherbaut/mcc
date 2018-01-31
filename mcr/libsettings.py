import yaml
import os
from pathlib import Path


def get_in_priodict(key, prioritary, secondary, required=True, default=None):
    if key in prioritary:
        return prioritary[key]

    if key in secondary:
        return secondary[key]

    if required:
        raise Exception("Please specify %s value in cli or config file" % key)
    else:
        return default


def merge_settings(config_path, cli_settings={}):
    if config_path is None:
        local_settings_path = os.path.join(os.getcwd(), "settings.yaml")
        user_settings_path = os.path.join(str(Path.home()), "mcc", "settings.yaml")
        if os.path.exists(local_settings_path):
            config_path = local_settings_path
        elif os.path.exists(user_settings_path):
            config_path = user_settings_path
        else:
            print("No config file provided and nor %s or %s exist" % (local_settings_path, user_settings_path))
            exit(2)

    with open(config_path) as settings_file:
        settings = yaml.load(settings_file)


        if settings is not None and "ssh_key_file_public" in  settings:
            with open(settings["ssh_key_file_public"]) as f:
                settings_ssh_key = f.read()
        else:
            raise Exception("Please specify a ssh_key_file_public in your settings")

        res = {**settings, **cli_settings}
        res["ssh_key"] = settings_ssh_key

        return res

    raise Exception("Can't find config file %s" % config_path)

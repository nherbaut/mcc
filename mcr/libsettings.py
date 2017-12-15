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


def load_settings(config_path, cli_settings={}):
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

        def g(key, required=True, default=None):
            return get_in_priodict(key, cli_settings, settings, required, default)

        settings_api_url = g("api-backend")
        settings_login = g("username")
        settings_pwd = g("password")
        settings_ssh_key_file_public = g("ssh_key_file_public")
        settings_ssh_key_file_private = g("ssh_key_file_private")
        settings_g5k_alias = g("grid5k_ProxyCommand_domain_alias")
        settings_environment = g("environment")
        settings_default_site = g("default_site", False, [])
        with open(settings_ssh_key_file_public) as f:
            settings_ssh_key = f.read()

        return settings_api_url, settings_login, settings_pwd, settings_ssh_key_file_public, settings_ssh_key_file_private, settings_g5k_alias, settings_environment, settings_default_site, settings_ssh_key

    raise Exception("Can't find config file %s" % config_path)

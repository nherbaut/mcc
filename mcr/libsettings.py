import yaml

with open("settings.yaml") as settings_file:
    settings = yaml.load(settings_file)

settings_api_url = settings["api-backend"]
settings_login = settings["username"]
settings_pwd = settings["password"]
settings_ssh_key_file_public = settings["ssh_key_file_public"]
settings_ssh_key_file_private = settings["ssh_key_file_private"]
settings_g5k_alias = settings["grid5k-ProxyCommand-domain-alias"]
settings_environment = settings["environment"]
settings_default_site = settings["default-site"]
with open(settings_ssh_key_file_public) as f:
    settings_ssh_key = f.read()

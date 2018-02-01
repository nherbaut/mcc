# configuration

Configuration can be done through the CLI

```bash
mcc -s default_site=nancy job list
```

or based on a configuration file 

```bash
mcc --config ./settings.yaml job list
```

by default mcc looks for `settings.yaml` in the working folder or in ~/mcc/settings.yaml

the provided `settings.yaml.tpl` can be used to know what are the parameters

# settings file

```yaml
#Common grid5000 parameters
login: nherbaut
pwd: MY_PASSWORD
api-backend: https://api.grid5000.fr/
ssh_key_file_public: /home/nherbaut/.ssh/g5k.pub
ssh_key_file_private: /home/nherbaut/.ssh/g5k
mailto: nicolas.herbaut@gmail.com
environment: debian9-x64-base
default_site: grenoble
```

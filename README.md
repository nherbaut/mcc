# Goal

provide a simple cli for grid5000 experiments. The CLi is based on modern syntax such as git, nftables or iproute2.
Users should be able to perform the following tasks in one line:

- allocate machines
- deploy system to machines
- wipe everything up


# prerequisites

- python2 or python3
- easy_install

# installation

- sudo make install

# usage

```bash

#create a new job for 10 machines in genepi 
%> JOB=(mcc job add genepi 10 for 3h)
#wait for the job to complete
%> mcc job wait $JOB
# create a new deployment to install the OSes on the allocated machines
# can select a subset of the jobs
%> DEP=(mcc dep add $JOB)
# wait for the deployment to complete
%> mcc dep wait $DEP
# install and configure saltstack master on one host, and saltstack minion on the other hosts
%> mcc job install $JOB salt
#remove the job when you're done.
%> mcc job del $JOB

```

# configuration

Configuration can be done through the CLI

```bash
mcc -s default_site=nancy job list
```

or based on a configuration file 

```bash
mcc --config ./settings.yaml job list
```

by default mcc looks for settings.yaml in the working folder or in ~/mcc/settings.yaml

the provided settings.yaml.tpl can be used to know what are the parameters

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

#salt installation parameters
#all variables can be injected in salt templates

salt_master_interface: eth0
salt_host_control_iface: eth0
salt_host_data_iface: eth0
salt_minion_template: /home/nherbaut/workspace/simple-g5k-wrapper/salt-templates/minion.tpl
salt_master_template: /home/nherbaut/workspace/simple-g5k-wrapper/salt-templates/master.tpl
salt_states_repo_url: https://gricad-gitlab.univ-grenoble-alpes.fr/vqgroup/salt-master.git
salt_states_repo_branch: auto_install
salt_state_dest_folder: /srv

# commands to execute before salt is installed
salt_pre_bootstrap_commands:
  - apt-get update
  - apt-get install git --yes

```

# help

All the commands are documented through the CLI

```
mcc job --help
```

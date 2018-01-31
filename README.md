# Goal

provide a simple cli for grid5000 experiments. The CLi is based on modern syntax such as git, nftables or iproute2.
Users should be able to perform the following tasks in one line:

- allocate machines
- deploy system to machines
- run an experiment and collect output data
- wipe everything up


# prerequisites

- python3
- easy_install

## installation on ubuntu/debian

``` bash
$ apt-get install python3 python3-dev libffi-dev python3-setuptools
$ make install
```

# installation

- sudo make install

# usage

```bash

#create a new job for 10 machines in genepi 
%> JOB=(mcc job add genepi 10 for 3h)
#wait for the job to complete
%> mcc job wait $JOB
# create a new deployment to install the OSes on the allocated machines
# can select a subset of the hosts from the job
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


# help

All the commands are documented through the CLI

```
mcc job --help
```

#Saltstack support

Saltstack is a configuration manager (such as ansible, puppet or chef) that can be used to install, configure and run complex orchestration operations to a cluster comprised of 1 master and several minions

MCC supports installing saltstack on target machines through the `mcc job install JOBID salt` command.

By default, MCC installs a vanilla saltstack. It can be tweaked thanks to specific parameters in the `settings.yaml` file:

```yaml

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

`salt_states_repo_url` can be used to clone a git repository at bootstrapping time containing the saltstack receipes so that the salt infrastructure is ready for the experiment.


## Minion templating

Every variable declared in the settings.yaml file will be resolved in the minion and master files. For example, to configure the salt-mine functions at the minion level, the salt minion template can be :

```yaml
rejected_retry: True
mine_interval: 1
hostsfile:
  alias: controlpath_ip
mine_functions:
  datapath_ip:
    - mine_function: network.ip_addrs
    - {{ salt_host_data_iface }}
  controlpath_ip:
    - mine_function: network.ip_addrs
    - {{ salt_host_control_iface }}
  docker_spy:
    - mine_function: dspy.dump
    - {{ salt_host_data_iface }}
```

in this case, mcc will pickup the `salt_host_data_iface` and `salt_host_control_iface` variables from the settings to install them in the minion.

## Master templating

The master can be templetized to add formulas or pillar data

```yaml
open_mode: True
auto_accept: True
file_roots:
  base:
    - /srv/salt
    - /srv/formulas/hostsfile-formula
    - /srv/formulas/openssh-formula
    - /srv/formulas/docker-formula
```

# Tools

extra tools to facilitate operations are provided.

## Alias-gen

calling this script with a `JOB_ID` createas a `experiment_alias.sh`. When sourced, you can connect to your experiment hosts easily:

```bash
$ alias-gen 1324354
alias generated. Type source ./experiment_alias.sh
$ . ./experiment_alias.sh
$ gh0 #open an ssh connection to the first host of the experiment
$ gh1 #open an ssh connection to the second host of the experiment
```
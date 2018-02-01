
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

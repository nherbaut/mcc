# Goal

provide a simple cli for grid5000 experiments. The CLi is based on modern syntax such as git, nftables or iproute2.
Users should be able to perform the following tasks in one line:

- allocate machine
- deploy system to machine
- wipe everything up


# prerequisites

- python2 or python3
- easy_install

# installation

- sudo make install

# usage

```bash

#create a new job for 10 machines in grenoble (you can also specify the cluster)
%> JOB=(mcc job add grenoble 10 for 3h)
#wait for the job to finish creating
%> mcc job wait $JOB
# create a new deployment for the previous job
%> DEP=(mcc dep add $JOB)
# wait foro the deployed to terminate
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

# help

All the commands are documented through the CLI

```
mcc job --help
```

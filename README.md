# Goal

provide a simple cli for grid5000 experiments. The CLi is based on modern syntax such as git, nftables or iproute2.
Users should be able to perform the following tasks in one line:

- allocate machines
- deploy system to machines
- run an experiment and collect output data
- wipe everything up

# Summary 
 - [Salstack Integration](SalStack.md)





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
%> JOB=(mcc job add genepi 10 for 3h now)
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


```


# help

All the commands are documented through the CLI

```
mcc job --help
```

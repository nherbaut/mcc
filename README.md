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


# commands

## root commands

```
usage: mcc [-h] [-q] [--format FORMAT] [--dry-run] {job,dep} ...

positional arguments:
  {job,dep}

optional arguments:
  -h, --help       show this help message and exit
  -q               quiet mode, just display the uids
  --format FORMAT  output formatting template, jinja
  --dry-run        just print the http requests
```

# job command

```
usage: mcc job [-h] {list,add,del} ...

positional arguments:
  {list,add,del}

optional arguments:
  -h, --help      show this help message and exit
```

## job list command

```
usage: mcc job list [-h] [--site [SITE [SITE ...]]]
                    [--filter [FILTER [FILTER ...]]]
                    [uid]

positional arguments:
  uid                   uid of the job to inspect

optional arguments:
  -h, --help            show this help message and exit
  --site [SITE [SITE ...]]
                        list of sites for job search
  --filter [FILTER [FILTER ...]]
                        list of filters to job seach, e.g. status=running

```

## job add command

```
usage: mcc job add [-h] [--walltime WALLTIME] site node_count

positional arguments:
  site                 site where to deploy the job
  node_count           how many node to book

optional arguments:
  -h, --help           show this help message and exit
  --walltime WALLTIME  wall time for the job

```

## job del command

```
usage: mcc job del [-h] [--site [SITE]] uid

positional arguments:
  uid            uid of the job to delete

optional arguments:
  -h, --help     show this help message and exit
  --site [SITE]  hint of where the site job is
```

# deployment command

```
usage: mcc dep [-h] {add,list} ...

positional arguments:
  {add,list}

optional arguments:
  -h, --help  show this help message and exit
```

## deployment list command

```
usage: mcc dep list [-h] [--site [SITE [SITE ...]]]
                    [--filter [FILTER [FILTER ...]]]
                    [uid]

positional arguments:
  uid                   uid of the dep to inspect

optional arguments:
  -h, --help            show this help message and exit
  --site [SITE [SITE ...]]
                        list of sites for dep search
  --filter [FILTER [FILTER ...]]
                        list of filters to dep seach, e.g. state=running
                        state!=error

```

## deployment add command

```
usage: mcc dep add [-h] [--site [SITE]] [--environment ENVIRONMENT]
                   uid [nodes [nodes ...]]

positional arguments:
  uid                   uid of the job on which to do the deployment
  nodes                 names of the nodes on which to perform the
                        deployement. all nodes from the job are deployed if
                        ommited

optional arguments:
  -h, --help            show this help message and exit
  --site [SITE]         hint of where the site job is
  --environment ENVIRONMENT
                        name of the environment to install

```

# Goal

provide a simple cli for grid5000 experiments. The CLi is based on modern syntax such as git, nftables or iproute2.
Users should be able to perform the following tasks in one line:

- allocate machine
- deploy system to machine
- wipe everything up

# usage

```

export SITE=nancy
#ask for resources creation
JOB=$(./mcc -q job add $SITE 10)

#wait while creating resources
while [ `./mcc --format "{{ state=='running' }}" job list $JOB --site $SITE` == 'False' ]; do ./mcc --format "{{ scheduled_at - now }}" job list $JOB --site $SITE; sleep 2; done

#resources created, now deploy
DEP_ID=$(./mcc -q dep add $JOB)

#wait while terminating deployment
while [ `./mcc --format="{{ status=='terminated' }}" dep list $DEP_ID --site $SITE` == 'False' ]; do ./mcc --format="{{ now-created_at }}" dep list $DEP_ID --site $SITE ; sleep 2; done

#terminated, get nodes address
./mcc --format='{{ assigned_nodes|join(" ") }}' job list $JOB|sed "s/grid5000.fr/g5k/g" | sed "s/ /\n/g"|xargs -I {} echo "ssh -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i ~/.ssh/g5k root@{}"|sort

# DO YOUR EXPERIMENT HERE

./mcc job del $JOB

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

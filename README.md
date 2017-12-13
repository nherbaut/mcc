# Goal

provide a simple cli for grid5000 experiments. The CLi is based on modern syntax such as git, nftables or iproute2.
Users should be able to perform the following tasks in one line:

- allocate machine
- deploy system to machine
- wipe everything up

# usage

```bash

export SITE=nancy
export NIC="eth0"



#ask for resources creation
JOB=$(./mcc -q job add $SITE 10 --walltime "05:00")

#wait while creating resources
while [ `./mcc --format "{{ state=='running' }}" job list $JOB --site $SITE` == 'False' ]; do ./mcc --format "{{ scheduled_at - now }}" job list $JOB --site $SITE; sleep 2; done

#resources created, now deploy
DEP_ID=$(./mcc -q dep add $JOB --site $SITE)

#wait while terminating deployment
while [ `./mcc --format="{{ status=='terminated' }}" dep list $DEP_ID --site $SITE` == 'False' ]; do ./mcc --format="elapsed time: {{ now - created_at }}" dep list $DEP_ID --site $SITE ; sleep 2; done

#tells the system which is the NIC though which the control is done (salt, monitoring traffic)
export NIC_CONTROL="eth0"

#tells the system which is the NIC though which the data flows (real payloads)
export NIC_DATA="eth0"

#build an array of all the hosts in the job
#to work it requires to setup the proxycommand as explained in grid500
#https://www.grid5000.fr/mediawiki/index.php/SSH#Using_SSH_with_ssh_proxycommand_setup_to_access_hosts_inside_Grid.275000
export HOSTS=($(./mcc --format="{{ assigned_nodes|join('\n')}}" -q job list $JOB --site $SITE|sed "s/grid5000.fr/g5k/g"))

#command to resolve the control IP on a host
export ip_resolver="ip a s $NIC_CONTROL |sed -rn \"s/ +inet ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}).*/\1/p\""

#clean up the alias file
echo "" > experiment_alias.sh

#for all hosts
for i in "${!HOSTS[@]}"
do
    #command used to connect in ssh seamlessly.
    ssh_g5k="ssh -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i /home/nherbaut/.ssh/g5k root@${HOSTS[$i]}"

    #h0 is always the master
    if [ $i == 0 ]
      then
       #get the master IP
       export MASTER_IP=$($ssh_g5k $ip_resolver)

       #bootstrap the master
       $ssh_g5k "wget -q https://gricad-gitlab.univ-grenoble-alpes.fr/vqgroup/salt-master/raw/master/vagrant/bootstrap_master.sh -O ./bootstrap.sh && bash bootstrap.sh $MASTER_IP $NIC_CONTROL $NIC_DATA h$i" &
    else

      #bootstrap the minions
      $ssh_g5k "wget -q https://gricad-gitlab.univ-grenoble-alpes.fr/vqgroup/salt-master/raw/master/vagrant/bootstrap_minion.sh -O ./bootstrap.sh && bash bootstrap.sh $MASTER_IP $NIC_CONTROL $NIC_DATA h$i" &

    fi

    #dump the alias in the alias file
    echo "alias gh$i=\"$ssh_g5k\""  >> experiment_alias.sh
done

#wait for all the bg bootstrapping tasks to complete
wait

echo "alias generated. Type source ./experiment_alias.sh"



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

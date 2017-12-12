simple cli for grid5000 experiments

# example:

```
#ask for resources creation
JOB=$(./mcc -q job add grenoble 2)

#wait while creating resources
while [ `./mcc --format "{{ state=='running' }}" job list $JOB` == 'False' ]; do sleep 2; done

#resources created, now deploy
DEP_ID=$(./mcc -q dep add $JOB)

#wait while terminating deployment
while [ `./mcc --format="{{ status=='terminated' }}" dep list $DEP_ID` == 'False' ]; do sleep 2; done

#terminated, get nodes address
./mcc --format='{{ assigned_nodes|join(" ") }}' job list $JOB|sed "s/grid5000.fr/g5k/g" | sed "s/ /\n/g"|xargs -I {} echo "ssh -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i ~/.ssh/g5k root@{}"|sort

# DO YOUR EXPERIMENT HERE

./mcc job del $JOB
```


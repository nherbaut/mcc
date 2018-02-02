# Goal

For complete documentation, [check the Wiki](../../../wikis)

Provide a simple cli for grid5000 experiments. The CLi is based on modern argument cli syntax.  Users should be able to perform the following tasks in one line:

- allocate machines
- deploy system to machines
- run an experiment and collect output data
- wipe everything up

# Supported backends

- Grid5000
- AWS EC2 (ongoing)


# Philosophy 

This project is very opinionated, and keep things as simple as possible. The main benefits are:

- do everything from your computer: no more sshing to an access points 
- do everything with one tool: no more using oarsub, kadeploy
- bash script-friendly: every output can be formatted, so that you can use mcc withing your favorite bash script
- scalable: deploy 1.000 nodes on 10 DC in one command.



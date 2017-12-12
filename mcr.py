#!/usr/bin/env python3

import logging
from mcr.libmcr import g5k
import sys
import time
from mcr.libsettings import *
from mcr.libsession import session as s
from mcr.libprint import print_jobs
import argparse

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

arger = argparse.ArgumentParser()
subparsers = arger.add_subparsers(dest="command")
arger.add_argument("-q", help="quiet mode, just display the uids", action="store_true", dest="quiet")
arger.add_argument("--dry-run", help="just print the http requests", action="store_true", dest="dry")

job_parser = subparsers.add_parser("job")

action_job_parser = job_parser.add_subparsers(dest="action")

list_job_parser = action_job_parser.add_parser("list")
list_job_parser.add_argument("uid", type=str, nargs='?', help='uid of the job to inspect', default=None)
list_job_parser.add_argument("--site", type=str, nargs='*', help='list of sites for job search')
list_job_parser.add_argument("--filter", type=str, nargs='*', help='list of filters to job seach, e.g. status=running',
                             default=[])

add_job_parser = action_job_parser.add_parser("add")
add_job_parser.add_argument("site", type=str, help='site where to deploy the job')
add_job_parser.add_argument("node_count", type=int, help='how many node to book')
add_job_parser.add_argument("--walltime", type=str, help='wall time for the job', default="00:30")

del_job_parser = action_job_parser.add_parser("del")
del_job_parser.add_argument("uid", type=str, help='uid of the job to delete')
del_job_parser.add_argument("--site", type=str, nargs='?', help='hint of where the site job is', default=None)
add_job_parser.add_argument("--environment", type=str, help='name of the environment to install',
                            default="debian9-x64-base")

dep_parser = subparsers.add_parser("dep")

action_dep_parser = dep_parser.add_subparsers(dest="action")

add_dep_parser = action_dep_parser.add_parser("add")
add_dep_parser.add_argument("job", type=str, help='uid of the job on which to do the deployment')
add_dep_parser.add_argument("nodes", type=str, nargs='*',
                            help='names of the nodes on which to perform the deployement. all nodes from the job are deployed if ommited')
add_dep_parser.add_argument("--site", type=str, nargs='?', help='hint of where the site job is', default=None)

# Parse
opts = arger.parse_args()


def find_job(job, sites_hints):
    if sites_hints is None or len(sites_hints) == 0:
        target_sites = g5k(s)("stable")("sites").get_items()
    else:
        target_sites = sites_hints

    for site in target_sites:
        jobs_for_site = g5k(s)("stable")("sites")(site)("jobs").get_items_filtered(data=True, user=settings_login,
                                                                                   uid=int(job))
        if len(jobs_for_site) == 1:
            return jobs_for_site[0]

    raise KeyError


try:

    if opts.command == "job":

        if opts.action == "list":
            kwargs = {splat[0]: splat[1] for splat in (item.split("=") for item in opts.filter)}
            kwargs["user"] = settings_login

            if opts.uid is None:
                for site in g5k(s)("stable")("sites").get_items():
                    if opts.site is None or site in opts.site:
                        jobs = g5k(s)("stable")("sites")(site)("jobs").get_items_filtered(data=not opts.quiet, **kwargs)
                        if len(jobs) > 0:
                            print_jobs(jobs)
            else:
                print_jobs([find_job(opts.uid, opts.site)])
                exit(0)


        elif opts.action == "add":
            job_uid = g5k(s)("stable")("sites")(opts.site).post_job(node_count=opts.node_count,
                                                                    walltime=opts.walltime)
            print(job_uid)
            pass

        elif opts.action == "del":

            job = find_job(opts.uid, opts.site)
            print(job)
            # g5k(s)("stable")("sites")(site)("jobs")(opts.uid).delete()
            # print("JOB %s/%s deleted" % (site, opts.uid))
            exit(0)

            # raise Exception("failed to delete job. Job missing or unauthorized")

    if opts.command == "dep":
        if opts.action == "add":
            pass




except KeyboardInterrupt:
    pass

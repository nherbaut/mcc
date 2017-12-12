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

# Make parser for "subcmds.py info ..."
list_parser = subparsers.add_parser("job")
list_parser.add_argument("action", choices=["list", "add", "delete"])
list_parser.add_argument("--site",
                         type=str, nargs='*',
                         help='list of sites for job search')
list_parser.add_argument("--filter",
                         type=str, nargs='*',
                         help='list of filters to job seach, e.g. status=running', default=[])

# Parse
opts = arger.parse_args()

if opts.command == "job":
    if opts.action == "list":
        for site in g5k(s)("stable")("sites").get_items():
            if opts.site is not None and site in opts.site:
                kwargs = {splat[0]: splat[1] for splat in (item.split("=") for item in opts.filter)}
                kwargs["user"] = settings_login
                jobs = g5k(s)("stable")("sites")(site)("jobs").get_items_filtered(data=not opts.quiet, **kwargs)
                if len(jobs) > 0:
                    print_jobs(jobs)

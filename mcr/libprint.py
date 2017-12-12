import sys
import yaml


def print_jobs(jobs):
    if len(jobs) == 0:
        return

    if type(jobs[0]) in [int, str]:
        print("\n".join([str(job) for job in jobs]))
    elif type(jobs[0]) == dict:
        for job in jobs:
            yaml.dump(job, sys.stdout, allow_unicode=True)
            print("--------------")

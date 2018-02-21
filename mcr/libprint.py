import sys
import yaml
import time
from jinja2 import Template


def print_items(items, print_template=None):
    if print_template is None:
        if len(items) == 0:
            return

        if type(items[0]) in [int, str]:
            print("\n".join([str(job) for job in items]))
        elif type(items[0]) == dict:
            for job in items:
                yaml.dump(job, sys.stdout, allow_unicode=True)
                print("--------------")

    else:

        template = Template(print_template)
        now = int(time.time())

        for item in items:
            item["now"] = now
            print(template.render(**item))

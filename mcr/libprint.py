import sys
import yaml
import jinja2
from jinja2 import Template


def print_items(items, print_template):
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
        for item in items:
            print(template.render(**item))

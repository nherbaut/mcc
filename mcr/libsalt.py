import os
import sys
import paramiko
import time
import logging
import re
import jinja2
import yaml, json


# logging.basicConfig(level=logging.DEBUG)


def get_ip(hostname, private_key, iface):
    command = 'ip a s %s ' % iface

    ip_res = str(exec_node_command(hostname, command, private_key))
    return re.findall(" +inet ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})", ip_res)[0]


def install_salt_minion(hostname, private_key, host_name, ip):
    return exec_node_command(hostname,
                             "curl -L https://bootstrap.saltstack.com | sh -s -- -i %s -A %s" % (host_name, ip),
                             private_key)


def install_salt_master(hostname, private_key, host_alias, ip, settings):
    if "salt_master_template" in settings:
        with open(settings["salt_master_template"]) as f:
            master_yaml_template = jinja2.Template(f.read()).render({**settings, **{"host_alias": host_alias}})
            master_json_template = json.dumps(yaml.load(master_yaml_template))

    return exec_node_command(hostname,
                             "curl -L https://bootstrap.saltstack.com | sh -s -- -M -i %s -A %s -J %s" % (host_alias, ip,master_json_template),
                             private_key)


def exec_node_command(host_name, command, private_key):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("access.grid5000.fr", key_filename=private_key)

    stdin, stdout, stderr = client.exec_command("ssh root@%s '%s'" % (host_name, command))
    res = stdout.read()
    return res

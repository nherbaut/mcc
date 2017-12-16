import os
import sys
import paramiko
import time
import logging
import re


# logging.basicConfig(level=logging.DEBUG)


def get_ip(hostname, private_key, iface):
    command = 'ip a s %s ' % iface

    ip_res = str(exec_node_command(hostname, command, private_key))
    return re.findall(" +inet ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})", ip_res)[0]


def install_salt_minion(hostname, private_key, host_name, ip):
    return exec_node_command(hostname,
                             "curl -L https://bootstrap.saltstack.com | sh -s -- -i %s -A %s" % (host_name, ip),
                             private_key)


def install_salt_master(hostname, private_key, host_name, ip):
    return exec_node_command(hostname,
                             "curl -L https://bootstrap.saltstack.com | sh -s -- -M -i %s -A %s" % (host_name, ip),
                             private_key)


def exec_node_command(host_name, command, private_key):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("access.grid5000.fr", key_filename=private_key)

    stdin, stdout, stderr = client.exec_command("ssh root@%s '%s'" % (host_name, command))
    res = stdout.read()
    return res

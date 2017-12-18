import os
import sys
import paramiko
import time
import logging
import re
import jinja2
import yaml, json

logging.getLogger("paramiko").setLevel(logging.WARNING)
install_states_command_template = "rm -rf {{ salt_state_dest_folder }}  && git  clone {{ salt_states_repo_url }}  --branch {{ salt_states_repo_branch }} --single-branch /{{ salt_state_dest_folder }}"


def get_ip(hostname, private_key, iface):
    command = 'ip a s %s ' % iface
    print(command)
    ip_res = str(exec_node_command(hostname, command, private_key))
    print(ip_res)
    return re.findall(" +inet ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})", ip_res)[0]


def install_salt_minion(hostname, private_key, host_alias, ip, settings):
    install_states_commands = []
    install_states_commands.append('curl -o bootstrap-salt.sh -L https://bootstrap.saltstack.com')

    if settings and "salt_minion_template" in settings:
        logging.info("installing salt minion with templates")

        with open(settings["salt_minion_template"]) as f:
            minion_yaml_template = jinja2.Template(f.read()).render({**settings, **{"host_alias": host_alias}})
            minion_json_template = json.dumps(yaml.load(minion_yaml_template))

        install_states_commands.append(install_states_commands.append(
            'sh bootstrap-salt.sh -F -i %s -A %s  -j \'"%s"\'' % (
                host_alias, ip,
                minion_json_template.replace("\"", "\\\""))))

    else:
        logging.info("installing vanilla salt minion")
        install_states_commands.append("sh bootstrap-salt.sh -F -i %s -A %s" % (host_alias, ip))

    for sub_command in install_states_commands:
        logging.info(exec_node_command(hostname, sub_command, private_key))


def install_salt_master(hostname, private_key, host_alias, ip, settings):
    # if precommand provided, add them to the stack
    install_states_commands = [jinja2.Template(command).render(**settings) for command in
                               settings.get("salt_pre_bootstrap_commands", [])]

    # if receipes provided,
    if "salt_state_dest_folder" in settings and "salt_states_repo_url" in settings and "salt_states_repo_branch" in settings:
        logging.info("cloning salt receipes to master")
        install_states_commands += jinja2.Template(install_states_command_template).render(**settings).split("&&")

    install_states_commands.append('curl -o bootstrap-salt.sh -L https://bootstrap.saltstack.com')
    # if template provided, use it
    if "salt_master_template" in settings and "salt_minion_template" in settings:
        logging.info("installing salt master with templates")
        with open(settings["salt_master_template"]) as f:
            master_yaml_template = jinja2.Template(f.read()).render({**settings, **{"host_alias": host_alias}})
            master_json_template = json.dumps(yaml.load(master_yaml_template))

        with open(settings["salt_minion_template"]) as f:
            minion_yaml_template = jinja2.Template(f.read()).render({**settings, **{"host_alias": host_alias}})
            minion_json_template = json.dumps(yaml.load(minion_yaml_template))

        install_states_commands.append(install_states_commands.append(
            'sh bootstrap-salt.sh -F -M -i %s -A %s -J \'"%s"\' -j \'"%s"\'' % (
                host_alias, ip, master_json_template.replace("\"", "\\\""),
                minion_json_template.replace("\"", "\\\""))))

    else:
        logging.info("installing vanilla salt master")
        install_states_commands.append("sh bootstrap-salt.sh -F -M -i %s -A %s" % (host_alias, ip))

    for sub_command in install_states_commands:
        logging.info(exec_node_command(hostname, sub_command, private_key))


def exec_node_command(host_name, command, private_key):
    if command is not None and command != "None" and len(command) > 0:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("access.grid5000.fr", key_filename=private_key)

        stdin, stdout, stderr = client.exec_command("ssh root@%s %s" % (host_name, command))
        res = stdout.read()
        logging.warning(stderr.read())
        stdin.close()
        stdout.close()
        stderr.close()
        return res

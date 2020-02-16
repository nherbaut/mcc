import os
import sys
import pathlib
import paramiko
import time
import logging
import re
import jinja2
import yaml, json
from subprocess import list2cmdline

logger = logging.getLogger('mcc_salt')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

logging.getLogger("paramiko").setLevel(logging.WARNING)
install_states_command_template_master = "&& rm -rf {{ salt_state_dest_folder }}  && rm -rf /tmp/salt_states_repo && git  clone {{ salt_states_repo_url }}  --branch {{ salt_states_repo_branch }} --single-branch /tmp/salt_states_repo && cp -R /tmp/salt_states_repo/{{ salt_states_repo_subfolder }} {{ salt_state_dest_folder }}"
install_states_command_template_minion = "rm -rf /tmp/*"


def get_ip(hostname, login, private_key, iface):
    command = 'ip -o -4 a s'
    ip_res = exec_node_command(hostname, login, command, private_key, log_output=False)
    all_ips = {}
    for ip_data in ip_res:
        for k, v in re.findall(".*[0-9]+: ([^ ]*) +inet ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})/.*$",
                               str(ip_data)):
            all_ips.update({k: v})
    if "lo" in all_ips:
        del all_ips["lo"]
    if iface in all_ips:
        return all_ips[iface]
    else:
        if len(all_ips) > 0:
            return list(all_ips.items())[0][1]

    raise Exception("failed to retreive master ip on interface %s. Available interfaces are: \n %s" % (
        iface, "\n".join(exec_node_command(hostname, login, "ip a", private_key))))


def install_salt_minion(hostname, interface_name, private_key, host_alias, ip, settings):
    install_states_commands = [shell_escape(jinja2.Template(command).render(**settings)) for command in
                               settings.get("salt_minion_precommands", [])]

    if "grisou-11" in hostname:
        print("salut")

    install_states_commands += jinja2.Template(install_states_command_template_minion).render(**settings).split("&&")

    install_states_commands.append('curl -o bootstrap-salt.sh -L https://bootstrap.saltstack.com')

    if settings and "salt_minion_template" in settings:
        logger.info("installing salt minion with templates")

        with open(settings["salt_minion_template"]) as f:

            minion_yaml_template = jinja2.Template(f.read()).render(
                {**settings, **{"host_alias": host_alias, "interface_name": interface_name}})
            minion_json_template = json.dumps(yaml.load(minion_yaml_template))

        install_states_commands.append(install_states_commands.append(
            'sh bootstrap-salt.sh -F -i %s -A %s  -j \'"%s"\'' % (
                host_alias, ip,
                minion_json_template.replace("\"", "\\\""))))

    else:
        logger.info("installing vanilla salt minion")
        install_states_commands.append(shell_escape("sh bootstrap-salt.sh -F -i %s -A %s" % (host_alias, ip)))

    install_states_commands += [shell_escape(jinja2.Template(command).render(**settings)) for command in
                                settings.get("salt_minion_postcommands", [])]

    for sub_command in install_states_commands:
        for res in exec_node_command(hostname, settings["login"], sub_command, private_key):
            logger.info(res)


def install_salt_master(hostname, interface_name, private_key, host_alias, ip, settings):
    # if precommand provided, add them to the stack
    install_states_commands = [shell_escape(jinja2.Template(command).render(**settings)) for command in
                               settings.get("salt_master_precommands", [])]

    if "salt_state_dest_folder" in settings and "salt_states_repo_url" in settings and "salt_states_repo_branch" in settings:
        logger.info("cloning salt receipes to master")
        install_states_commands += jinja2.Template(install_states_command_template_master).render(**settings).split(
            "&&")

    if "salt_master_file_managed" in settings:
        for file in settings["salt_master_file_managed"]:
            src = pathlib.Path(file["src"])
            dst = pathlib.Path(file["dst"])
            with src.open("r") as f:
                install_states_commands += [shell_escape("mkdir -p %s" % dst.parent)]
                install_states_commands += [shell_escape('echo "" > %s ' % dst)]
                processed_src_lines = jinja2.Template(f.read()).render(**settings).split("\n")
                for line in processed_src_lines:
                    install_states_commands += [shell_escape('echo "%s" >> %s' % (line, dst))]

                    # if receipes provided,

    install_states_commands.append('curl -o bootstrap-salt.sh -L https://bootstrap.saltstack.com')
    # if template provided, use it
    if "salt_master_template" in settings and "salt_minion_template" in settings:
        logger.info("installing salt master with templates")
        with open(settings["salt_master_template"]) as f:
            master_yaml_template = jinja2.Template(f.read()).render({**settings, **{"host_alias": host_alias}})
            master_json_template = json.dumps(yaml.load(master_yaml_template))

        with open(settings["salt_minion_template"]) as f:
            minion_yaml_template = jinja2.Template(f.read()).render(
                {**settings, **{"host_alias": host_alias, "interface_name": interface_name}})
            minion_json_template = json.dumps(yaml.load(minion_yaml_template))

        install_states_commands.append(install_states_commands.append(
            'sh bootstrap-salt.sh -F -M -i %s -A %s -J \'"%s"\' -j \'"%s"\'' % (
                host_alias, ip, master_json_template.replace("\"", "\\\""),
                minion_json_template.replace("\"", "\\\""))))

    else:
        logger.info("installing vanilla salt master")
        install_states_commands.append("sh bootstrap-salt.sh -F -M -i %s -A %s" % (host_alias, ip))

    for sub_command in install_states_commands:
        for res in exec_node_command(hostname, settings["login"], sub_command, private_key):
            logger.info(res)


# https://stackoverflow.com/questions/3163236/escape-arguments-for-paramiko-sshclient-exec-command/13786877#13786877
def shell_escape(arg):
    if arg is not None:
        return "'%s'" % (arg.replace(r"'", r"'\''"),)


def post_install_commands(hostname, private_key, settings):
    install_states_commands = [jinja2.Template(command).render(**settings) for command in
                               settings.get("salt_master_postcommands", [])]
    for sub_command in install_states_commands:
        for res in exec_node_command(hostname, settings["login"],
                                     shell_escape(jinja2.Template(sub_command).render(**settings)), private_key):
            logger.info(res)


def exec_node_command(host_name, login, command, private_key, log_output=True):
    if command is not None and command != "None" and len(command) > 0:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("access.grid5000.fr", key_filename=private_key, username=login)

        stdin, stdout, stderr = client.exec_command("ssh root@%s %s" % (host_name, command))
        res = stdout.read()
        for errline in str(stderr.read()).split("\\n"):
            logger.warning(" %s > " % host_name + str(errline))
        stdin.close()
        stdout.close()
        stderr.close()
        if log_output:
            return [" %s < " % host_name + str(command)] + [" %s > " % host_name + str(r) for r in str(res).split("\\n")
                                                            if
                                                            len(r) > 3]
        else:
            return [str(r) for r in str(res).split("\\n") if len(r) > 3]
    else:
        return []

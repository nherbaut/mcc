import copy
import datetime
import logging
import sys
import threading
import time

import dateutil.parser

import mcr.libsession

from mcr.libprint import print_items
from mcr.libsalt import get_ip, install_salt_master, install_salt_minion, post_install_commands

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

API_VER = "stable"


class ApiError(Exception):
    def __init__(self, return_code, return_text):
        self.return_code = return_code
        self.return_text = return_text

    def __str__(self):
        return "%d: %s" % (self.return_code, self.return_text)


def g5kparser(session, data, *args):
    if len(args) == 0:
        return data

    arg = args[0]

    if arg in data:
        if type(data[arg]) == dict:

            def _(*arg2):
                return g5kparser(session, data[arg], *arg2)

            return _
        else:
            return data[arg]

    if "items" in data:
        for v in data["items"]:
            if "uid" in v and v["uid"] == arg:
                def _(*arg2):
                    return g5kparser(session, v, *arg2)

                return _
    elif "links" in data:
        for v in data["links"]:
            if "rel" in v and v["rel"] == arg:
                url = g5kparser(session, v, "href")
                r = session.get(url)
                assert r.status_code == 200

                def _(*arg2):
                    return g5kparser(session, r.json(), *arg2)

                return _

    raise NameError


def is_dict_matching(d1, dfilter):
    '''

    :param d1: the dict which values will be tested
    :param dfilter: the dict which specifies the values to test. {"a":"b","c!":"d","e>":"f"} <=> d1["a"]=="b" and d1["c"]!="d" and int(d1["e"])>int('f')
    :return: True i
    '''
    for k, v in dfilter.items():
        if k[-1] == '!':
            if d1.get(k[:-1], None) == str(dfilter[k]):
                return False
        elif k[-1] == '>':
            if int(d1.get(k[:-1], 0)) <= int(dfilter[k]):
                return False
        elif k[-1] == '<':
            if int(d1.get(k[:-1], 0)) >= int(dfilter[k]):
                return False
        else:
            if d1.get(k, None) != str(dfilter[k]):
                return False

    return True


class Kolector:
    def __init__(self, session, *args):
        self.session = session
        self.path_elements = []
        for item in args:
            for subitem in item.split("/"):
                self.path_elements.append(subitem)

    def __call__(self, *args, **kwargs):
        for item in args:
            for subitem in str(item).split("/"):
                self.path_elements.append(subitem)
        if "q" in kwargs:
            self.path_elements[-1] = self.path_elements[-1] + "?" + "&".join(
                ["%s=%s" % (k, v) for k, v in kwargs["q"].items()])

        return self

    def get_items_filtered(self, **kwargs):
        res = []
        include_data = False
        if "data" in kwargs:
            include_data = kwargs["data"]
            del kwargs["data"]
        r = self.session.get("/".join(self.path_elements))
        if r.status_code < 299:
            json_data = r.json()
            for item in g5kparser(self.session, json_data, "items"):

                if is_dict_matching(item, kwargs):
                    if include_data:
                        res.append(item)
                    else:
                        res.append(item["uid"])
        else:
            raise ApiError(r.status_code, r.text)

        return res

    def get_raw(self, *args):
        r = self.session.get("/".join(self.path_elements))
        if r.status_code < 299:
            return g5kparser(self.session, r.json(), *args)
        raise ApiError(r.status_code, r.text)

    def get_items(self):
        r = self.session.get("/".join(self.path_elements))
        if r.status_code < 299:
            return [item["uid"] for item in g5kparser(self.session, r.json(), "items")]
        raise ApiError(r.status_code, r.text)

    def get_links(self):
        r = self.session.get("/".join(self.path_elements))
        if r.status_code < 299:
            logging.debug(r.json())
            return {item["rel"]: item["href"] for item in g5kparser(self.session, r.json(), "links")}
        raise ApiError(r.status_code, r.text)

    def url(self):
        return "/".join(self.path_elements)

    def post_job(self, resources={"node_count": "10", "walltime": "2:00"}, properties={}, types=["deploy"],
                 reservation=None, queue="default"):

        data = {}
        data["resources"] = ",".join(["%s=%s" % item for item in resources])
        data["properties"] = ",".join(["%s=%s" % item for item in properties])
        data["types"] = types
        data["queue"] = queue
        if reservation is not None:
            data["reservation"] = reservation
        h, m = resources[1][1].split(":")
        data["command"] = "sleep %d" % (int(h) * 3600 + int(m) * 60)
        r = self.session.post("/".join(self.path_elements + ["jobs"]), json=data)
        if not r.status_code == 201:
            logging.error(r.text)
            raise ApiError(r.status_code, r.text)

        return r.json()["uid"]

    def post_provision(self, node_list, key, environment,
                       notifications=["mailto:nicolas.herbaut@gmail.com"]):
        data = {}
        data["nodes"] = node_list
        data["environment"] = environment
        data["key"] = key
        data["notifications"] = notifications

        r = self.session.post("/".join(self.path_elements), json=data)

        if not r.status_code == 201:
            logging.error(r.status_code)
            logging.error(r.text)
            raise ApiError(r.status_code, r.text)

        return r.headers['Location'].split("/")[-1]

    def delete(self):
        r = self.session.delete("/".join(self.path_elements))
        if not r.status_code == 202:
            logging.error(r.status_code)
            logging.error(r.text)
            raise ApiError(r.status_code, r.text)
        return None

    def delete_job(self, uid):
        self.path_elements.append("job", str(uid))
        return self.delete()


def g5k(s):
    return Kolector(session=s)


class MCCClient:

    def __init__(self, **settings):
        self.settings = settings
        self.s = mcr.libsession.create_session(settings["api-backend"], self.settings["login"], self.settings["pwd"])

    def run(self):

        switch = {"job": self.handle_job, "dep": self.handle_dep,
                  "alias": self.handle_alias, "wait": self.handle_wait,
                  "env": self.handle_env, "site": self.handle_site}
        command = self.settings["command"]

        if command not in switch:
            raise Exception('please specify an action: %s' % ", ".join(switch))
        action = self.settings["action"]

        switch[command](action)

    def handle_env(self, action):
        switch = {"list": self.env_list_print}
        if action not in switch:
            raise Exception('please specify an action: %s' % ", ".join(switch))

        switch[action]()

    def handle_site(self, action):
        switch = {"list": self.site_list_print}
        if action not in switch:
            raise Exception('please specify an action: %s' % ", ".join(switch))

        switch[action]()

    def handle_alias(self, action):
        switch = {"list": self.alias_list_print}

        if action not in switch:
            raise Exception('please specify an action: %s' % ", ".join(switch))

        switch[action]()

    def handle_wait(self, action):

        import signal
        import time

        class GracefulKiller:
            kill_now = False

            def __init__(self):
                signal.signal(signal.SIGINT, self.exit_gracefully)
                signal.signal(signal.SIGTERM, self.exit_gracefully)

            def exit_gracefully(self, signum, frame):
                self.kill_now = True

        killer = GracefulKiller()
        while True:
            time.sleep(1)
            if killer.kill_now:
                self._job_del()
                break

    def handle_job(self, action):

        switch = {"list": self._job_list_print,
                  "add": self._job_add,
                  "del": self._job_del,
                  "wait": self._job_wait,
                  "hosts-list": self._job_host_list_print,
                  "install": self._job_install
                  }

        if action not in switch:
            raise Exception('please specify an action: %s' % ", ".join(switch))
        switch[action]()

    def handle_dep(self, action):
        switch = {"add": self._dep_add,
                  "list": self._dep_list,
                  "wait": self._dep_wait}

        if action not in switch:
            raise Exception('please specify an action: %s' % ", ".join(switch))

        switch[action]()

    def _job_install(self):
        application = self.settings["application"]
        uid = self.settings["uid"]
        site = self.settings["site"]
        login = self.settings["login"]
        salt_host_control_iface = self.settings["salt_host_control_iface"]
        ssh_key_file_private = self.settings["ssh_key_file_private"]
        session = self.s

        return MCCClient.job_install(session, application, uid, site, login, salt_host_control_iface,
                                     ssh_key_file_private,
                                     self.settings)

    @staticmethod
    def job_install(session, application, uid, site, login, salt_host_control_iface, ssh_key_file_private, settings):

        if application == "salt":
            threads = []
            # ssh_key_file_private = self.settings["ssh_key_file_private"] # not used here

            for i, host in enumerate(MCCClient.job_host_list(session, uid, site)):

                try:
                    cluster_name = host.split("-")[0]
                    interface_name = settings["g5k_interface_name_mapping"].get(cluster_name, "")
                except:
                    raise Exception("failed to computer interfacename")

                if i == 0:
                    master_ip = get_ip(host, login, ssh_key_file_private, interface_name  )
                    master_hostname = host

                    print("master ip: %s" % master_ip)
                    print("installing master in %s" % host)

                    # gk5 hack to get the cluster name, so we can infer the name of the interface

                    t = threading.Thread(target=install_salt_master,
                                         args=(
                                             host, interface_name, ssh_key_file_private, "h0", master_ip, settings))
                    t.start()
                    threads.append(t)
                else:

                    print("installing minion in %s" % host)
                    t = threading.Thread(target=install_salt_minion,
                                         args=(
                                             host, interface_name, ssh_key_file_private, "h%s" % i, master_ip,
                                             settings))
                    t.start()
                    threads.append(t)
            for t in threads:
                t.join()

                post_install_commands(master_hostname, ssh_key_file_private, settings)

            print("done")

    def _job_list(self):

        filters = copy.copy(self.settings["filter"])
        filters.insert(0, "user_uid=%s" % self.settings["login"])
        uid = self.settings["uid"]
        sites = self.settings["sites"]
        login = self.settings["login"]
        quiet = self.settings["quiet"]
        session = self.s

        return MCCClient.job_list(uid, sites, login, quiet, session)

    @staticmethod
    def job_list(filters, uid, sites, login, quiet, session):
        if uid == "planned":  # a job is planed in the future and without error
            filters.insert(0, "started_at>=%d" % int(time.time()))
            filters.insert(0, "state!=error")
            uid = None

        res = print_site_item(session, "jobs", uid, sites, filters, login, quiet)
        return res

    def site_list(self, uid=None):
        session = self.s

        res = []

        if uid is None:
            for site in g5k(session)(API_VER)("sites").get_items():
                res.append(site)
        else:
            res = [g5k(session)(API_VER)("sites")(uid).get_raw()]

        return res

    def cluster_list(self, uid):
        pass

    def site_list_print(self):
        print_items(self.site_list())

    def env_list_print(self):
        session = self.s

        for site in get_sites(session):

            for env in g5k(session)("sites")(site)("environments").get_raw():
                print(env)

    def alias_list_print(self):

        for index, host in enumerate(
                [host for uid in self.settings["uid"] for host in self._job_host_list(uid, self.settings["site"])]):
            if index == 0:
                cluster_name = host.split("-")[0]
                interface_name = self.settings["g5k_interface_name_mapping"].get(cluster_name, "")
                master_ip = get_ip(host, self.settings["login"], self.settings["ssh_key_file_private"],
                                   self.settings["salt_host_control_iface"])
                print(
                    "alias ssh%d=\"ssh -L 0.0.0.0:5011:%s:5011 -L 8888:%s:8888 -L 8086:%s:0886 -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i %s root@%s\"" % (
                        index, master_ip, master_ip, master_ip, self.settings["g5k_ssh_key_file_private"],
                        host.replace("grid5000.fr", "g5k")))
            else:
                print(
                    "alias ssh%d=\"ssh -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i %s root@%s\"" % (
                        index, self.settings["g5k_ssh_key_file_private"], host.replace("grid5000.fr", "g5k")))

    def _job_list_print(self):
        format = self.settings["format"]
        filters = copy.copy(self.settings["filter"])
        filters.insert(0, "user_uid=%s" % self.settings["login"])
        uid = self.settings["uid"]
        sites = self.settings["sites"]
        login = self.settings["login"]
        quiet = self.settings["quiet"]
        session = self.s

        MCCClient.job_list_print(filters, uid, sites, login, quiet, session, format)

    @staticmethod
    def job_list_print(filters, uid, sites, login, quiet, session, format):
        res = MCCClient.job_list(filters, uid, sites, login, quiet, session)
        print_items(res, format)

    def _job_add(self):

        default_queue = self.settings.get("default_queue", "default")
        wallt_time = get_wall_time(self.settings["duration_adv"], self.settings["duration"])
        properties = []
        resources = []
        effect_date = self.settings["effect_date"]
        user_date = self.settings.get("date", None)
        site = self.settings["site"]
        session = self.s
        node_count = self.settings["node_count"]

        MCCClient.job_add(default_queue, wallt_time, properties, resources, effect_date, user_date, site, session,
                          node_count)

    @staticmethod
    def job_add(default_queue, wallt_time, properties, resources, effect_date, user_date, site, session, node_count):

        # it sucks that we cannot have a dict, but we need to preserve key ordering for OAR
        resources.append(("nodes", node_count))
        resources.append(("walltime", wallt_time))

        if effect_date == "on":
            reservation = user_date.strftime("%Y-%m-%d %H:%M:%S")  # in the future
        else:
            reservation = None  # now

        if not site in get_sites(session):
            properties.append(("cluster", "'%s'" % site))
            site = find_site_for_cluster(session, site)

        job_uid = g5k(session)(API_VER)("sites")(site).post_job(resources=resources, properties=properties,
                                                                reservation=reservation,
                                                                queue=default_queue)
        print(job_uid)

    def _job_del(self):
        uids = self.settings["uid"]
        session = self.s
        site = self.settings["site"]
        MCCClient.job_del(uids, session, site)

    @staticmethod
    def job_del(uids, session, site):

        for uid in uids:
            job_href = find_job(session, uid, None if site is None else [site])
            job_state = g5k(session)(job_href).get_raw()["state"]
            if job_state != "error":
                g5k(session)(job_href).delete()
                print("Job %s has been deleted " % job_href)
            else:
                print("Cannot del job %s since its state is %s " % (uid, job_state))

    def _job_wait(self):
        session = self.s
        uid = self.settings["uid"]
        sites = [self.settings["site"]]
        filter_ = self.settings["filter"]
        quiet = self.settings["quiet"]
        MCCClient.job_wait(session, uid, sites, filter_, quiet)

    @staticmethod
    def job_wait(session, uid, sites, filter_, quiet):

        job_href = find_job(session, uid, sites)
        filter_label, filter_value = filter_.split("=")
        job = g5k(session)(job_href).get_raw()
        while job[filter_label] != filter_value:
            if not quiet:
                if "scheduled_at" in job:
                    minutes_remaining = (int(job["scheduled_at"]) - int(time.time())) // 60
                else:
                    minutes_remaining = "?"
                sys.stdout.write(
                    "\b" * 80 + " %s minutes remaining (is %s)" % (minutes_remaining, job["state"]))
                sys.stdout.flush()
                time.sleep(5)
                job = g5k(session)(job_href).get_raw()

    def _job_host_list_print(self):
        uid, site = self.settings["uid"], self.settings["site"]
        session = self.s
        hosts = MCCClient.job_host_list(session, uid, site)
        print("\n".join(hosts))

    @staticmethod
    def job_host_list_print(uid, site):
        return MCCClient._job_host_list(uid, site)

    def _job_host_list(self, uid, site):
        session = self.s
        return MCCClient.job_host_list(session, uid, site)

    @staticmethod
    def job_host_list(session, uid, site):
        job_href = find_job(session, uid, [site])
        job = g5k(session)(job_href).get_raw()
        if job["state"] == "running":
            return job["assigned_nodes"]
        else:
            raise Exception("Cannot show hosts, job is %s " % job["state"])

    def _dep_add(self):
        session = self.s
        uid = self.settings["uid"]
        site = self.settings["site"]
        nodes = self.settings["nodes"]
        environment = self.settings["environment"]
        mailto = self.settings["mailto"]
        ssh_key = self.settings["ssh_key"]

        return MCCClient.dep_add(session, uid, site, nodes, environment, mailto, ssh_key)

    @staticmethod
    def dep_add(session, uid, site, nodes, environment, mailto, ssh_key):
        job = g5k(session)(
            find_job(session, uid,
                     None if site is None else [site])).get_raw()
        if len(nodes) == 0:
            node_list = job["assigned_nodes"]
        else:
            node_list = list(set(job["assigned_nodes"]) & set(nodes))
        dep_uid = g5k(session)(get_link_href(job, "parent"))("deployments").post_provision(node_list=node_list,
                                                                                           key=ssh_key,
                                                                                           environment=environment,
                                                                                           notifications=["mailto:%s" %
                                                                                                          mailto])
        print(dep_uid)

    def _dep_list(self):
        uid = self.settings["uid"]
        sites = self.settings["sites"]
        filter_ = self.settings["filter"]
        format_ = self.settings["format"]
        login = self.settings["login"]
        quiet = self.settings["quiet"]
        session = self.s

        MCCClient.dep_list(uid, sites, filter_, format_, login, quiet, session)

    @staticmethod
    def dep_list(uid, sites, filter_, format_, login, quiet, session):
        res = print_site_item(session, "deployments", uid, sites, filter_, login, quiet)
        print_items(res, format_)

    def _dep_wait(self):
        uid = self.settings["uid"]
        site = self.settings["site"]
        filter_ = self.settings["filter"]
        session = self.s
        quiet = self.settings["quiet"]
        MCCClient.dep_wait(uid, site, filter_, session, quiet)

    @staticmethod
    def dep_wait(uid, site, filter_, session, quiet):
        dep_href = find_dep(session, uid, [site])
        k, v = filter_.split("=")
        dep = g5k(session)(dep_href).get_raw()
        while dep[k] != v:
            if not quiet:
                minutes_elapsed = (int(time.time()) - int(dep["created_at"])) // 60
                sys.stdout.write(
                    "\b" * 80 + "%s minutes elapsed (is %s)" % (minutes_elapsed, dep["status"]))
                sys.stdout.flush()
            time.sleep(10)
            dep = g5k(session)(dep_href).get_raw()


def get_sites(session):
    return g5k(session)("stable/sites").get_items()


def find_site_for_cluster(session, cluster):
    for site in g5k(session)("stable/sites").get_items():
        if cluster in g5k(session)("stable/sites")(site)("clusters").get_items():
            return site
    raise ApiError(404, "Cluster not found")


def get_link_href(entity, rel="self"):
    for item in entity["links"]:

        if item["rel"] == rel:
            return item["href"]
    return ""


def find_job(session, job, sites_hints=None):
    return find_sub_item(session, "jobs", int(job), sites_hints)


def find_dep(session, dep, sites_hints=None):
    return find_sub_item(session, "deployments", dep, sites_hints)


def print_site_item(session, items_name, uid, sites, filter, login, quiet):
    kwargs = {splat[0]: splat[1] for splat in (item.split("=") for item in filter)}
    kwargs["user_uid"] = login

    if uid is None:
        for site in g5k(session)(API_VER)("sites").get_items():
            if sites is None or site in sites:
                return g5k(session)(API_VER)("sites")(site)(items_name).get_items_filtered(
                    data=not quiet,
                    **kwargs)

    else:

        return [g5k(session)(find_sub_item(session, items_name, uid, sites)).get_raw()]


def find_sub_item(session, item, uid, sites_hints):
    '''

    :param job: job uid
    :param sites_hints: list of possible sites to look for. If list is empty of None, all g5k sites are inspected
    :return: the url of the job
    '''

    if sites_hints is None or len(sites_hints) == 0:
        target_sites = g5k(session)(API_VER)("sites").get_items()
    else:
        target_sites = sites_hints

    for site in target_sites:
        try:
            items_for_site = g5k(session)(API_VER)("sites")(site)(item)(uid).get_raw()
            return get_link_href(items_for_site, rel="self")
        except ApiError as e:
            if e.return_code == 404:
                continue
            else:
                raise e

    return ""


def get_wall_time(duraction_adv, duration):
    if duraction_adv == "for":
        dt = (dateutil.parser.parse(duration) - dateutil.parser.parse("0h"))

    elif duraction_adv == "until":
        dt = (dateutil.parser.parse(duration) - datetime.datetime.now())

    return "%02d:%02d" % ((dt.seconds // 3600), (dt.seconds // 60) % 60)

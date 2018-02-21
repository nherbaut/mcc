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
            return [item["rel"] for item in g5kparser(self.session, r.json(), "links")]
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


class MCCClient():

    def __init__(self, **settings):
        self.settings = settings
        self.s = mcr.libsession.create_session(settings["api-backend"], self.settings["login"], self.settings["pwd"])

    def run(self):

        switch = {"job": self.handle_job, "dep": self.handle_dep, "alias": self.handle_alias, "wait": self.handle_wait}
        command = self.settings["command"]

        if command not in switch:
            parser.error('please specify an action: %s' % ", ".join(switch))
        action = self.settings["action"]

        switch[command](action)

    def handle_alias(self, action):
        switch = {"list": self.alias_list_print}

        if action not in switch:
            parser.error('please specify an action: %s' % ", ".join(switch))

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
                self.job_del()
                break

    def handle_job(self, action):

        switch = {"list": self.job_list_print,
                  "add": self.job_add,
                  "del": self.job_del,
                  "wait": self.job_wait,
                  "hosts-list": self.job_host_list_print,
                  "install": self.job_install
                  }

        if action not in switch:
            parser.error('please specify an action: %s' % ", ".join(switch))
        switch[action]()

    def handle_dep(self, action):
        switch = {"add": self.dep_add,
                  "list": self.dep_list,
                  "wait": self.dep_wait}

        if action not in switch:
            parser.error('please specify an action: %s' % ", ".join(switch))

        switch[action]()

    def job_install(self):
        application = self.settings["application"]
        uid = self.settings["uid"]
        site = self.settings["site"]
        login = self.settings["login"]

        if application == "salt":
            threads = []
            ssh_key_file_private = self.settings["ssh_key_file_private"]
            salt_host_control_iface = self.settings["salt_host_control_iface"]
            ssh_key_file_private = self.settings["ssh_key_file_private"]

            for i, host in enumerate(self.job_host_list(uid, site)):
                if i == 0:
                    master_ip = get_ip(host, login, ssh_key_file_private, salt_host_control_iface
                                       )
                    master_hostname = host

                    print("master ip: %s" % master_ip)
                    print("installing master in %s" % host)

                    t = threading.Thread(target=install_salt_master,
                                         args=(
                                             host, ssh_key_file_private, "h0", master_ip, self.settings))
                    t.start()
                    threads.append(t)
                else:

                    print("installing minion in %s" % host)
                    t = threading.Thread(target=install_salt_minion,
                                         args=(
                                             host, ssh_key_file_private, "h%s" % i, master_ip, self.settings))
                    t.start()
                    threads.append(t)
            for t in threads:
                t.join()

                post_install_commands(master_hostname, ssh_key_file_private, self.settings)

            print("done")

    def job_list(self):

        filters = copy.copy(self.settings["filter"])
        filters.insert(0, "user_uid=%s" % self.settings["login"])
        uid = self.settings["uid"]
        sites = self.settings["sites"]
        login = self.settings["login"]
        quiet = self.settings["quiet"]

        if uid == "planned":  # a job is planed in the future and without error
            filters.insert(0, "started_at>=%d" % int(time.time()))
            filters.insert(0, "state!=error")
            uid = None

        res = print_site_item(self.s, "jobs", uid, sites, filters, login, quiet)
        return res

    def alias_list_print(self):

        for index, host in enumerate(
                [host for uid in self.settings["uid"] for host in self.job_host_list(uid, self.settings["site"])]):
            if index == 0:
                master_ip = get_ip(host, self.settings["login"], self.settings["ssh_key_file_private"],
                                   self.settings["salt_host_control_iface"])

                print(
                    "alias ssh%d=\"ssh -L 5011:%s:5011 -L 8888:%s:8888 -L 8086:%s:0886 -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i %s root@%s\"" % (
                        index, master_ip, master_ip, master_ip, self.settings["g5k_ssh_key_file_private"],
                        host.replace("grid5000.fr", "g5k")))



            else:
                print(
                    "alias ssh%d=\"ssh -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i %s root@%s\"" % (
                        index, self.settings["g5k_ssh_key_file_private"], host.replace("grid5000.fr", "g5k")))

    def job_list_print(self):
        res = self.job_list()
        print_items(res, self.settings["format"])

    def job_add(self):

        default_queue = self.settings.get("default_queue", "default")
        wt = get_wall_time(self.settings["duration_adv"], self.settings["duration"])
        properties = []
        resources = []
        # it sucks that we cannot have a dict, but we need to preserve key ordering for OAR
        resources.append(("nodes", self.settings["node_count"]))
        resources.append(("walltime", wt))

        if self.settings["effect_date"] == "on":
            reservation = self.settings["date"].strftime("%Y-%m-%d %H:%M:%S")  # in the future
        else:
            reservation = None  # now

        if self.settings["site"] in get_sites(self.s):
            site = self.settings["site"]
        else:
            properties.append(("cluster", "'%s'" % self.settings["site"]))
            site = find_site_for_cluster(self.s, self.settings["site"])

        job_uid = g5k(self.s)("stable")("sites")(site).post_job(resources=resources, properties=properties,
                                                                reservation=reservation,
                                                                queue=default_queue)
        print(job_uid)

    def job_del(self):
        for uid in self.settings["uid"]:
            job_href = find_job(self.s, uid, None if self.settings["site"] is None else [self.settings["site"]])
            job_state = g5k(self.s)(job_href).get_raw()["state"]
            if job_state != "error":
                g5k(self.s)(job_href).delete()
                print("Job %s has been deleted " % job_href)
            else:
                print("Cannot del job %s since its state is %s " % (uid, job_state))

    def job_wait(self):
        job_href = find_job(self.s, self.settings["uid"], [self.settings["site"]])
        k, v = self.settings["filter"].split("=")
        job = g5k(self.s)(job_href).get_raw()
        while job[k] != v:
            if not self.settings["quiet"]:
                if "scheduled_at" in job:
                    minutes_remaining = (int(job["scheduled_at"]) - int(time.time())) // 60
                else:
                    minutes_remaining = "?"
                sys.stdout.write(
                    "\b" * 80 + " %s minutes remaining (is %s)" % (minutes_remaining, job["state"]))
                sys.stdout.flush()
                time.sleep(5)
                job = g5k(self.s)(job_href).get_raw()

    def job_host_list_print(self):
        hosts = self.job_host_list(self.settings["uid"], self.settings["site"])
        print("\n".join(hosts))

    def job_host_list(self, uid, site):
        job_href = find_job(self.s, uid, [site])
        job = g5k(self.s)(job_href).get_raw()
        if job["state"] == "running":
            return job["assigned_nodes"]
        else:
            raise Exception("Cannot show hosts, job is %s " % job["state"])

    def dep_add(self):
        session = self.s
        uid = self.settings["uid"]
        site = self.settings["site"]
        nodes = self.settings["nodes"]
        environment = self.settings["environment"]
        mailto = self.settings["mailto"]

        job = g5k(session)(
            find_job(session, uid,
                     None if site is None else [site])).get_raw()
        if len(nodes) == 0:
            node_list = job["assigned_nodes"]
        else:
            node_list = list(set(job["assigned_nodes"]) & set(nodes))
        dep_uid = g5k(session)(get_link_href(job, "parent"))("deployments").post_provision(node_list=node_list,
                                                                                           key=settings["ssh_key"],
                                                                                           environment=environment,
                                                                                           notifications=["mailto:%s" %
                                                                                                          mailto])
        print(dep_uid)

    def dep_list(self):
        uid = self.settings["uid"]
        sites = self.settings["sites"]
        filter_ = self.settings["filter"]
        format_ = self.settings["format"]
        login = self.settings["login"]
        quiet = self.settings["quiet"]
        session = self.s
        res = print_site_item(session, "deployments", uid, sites, filter_, login, quiet)
        print_items(res, format_)

    def dep_wait(self):
        uid = self.settings["uid"]
        site = self.settings["site"]
        filter_ = self.settings["filter"]
        session = self.s
        quiet = self.settings["quiet"]
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
        for site in g5k(session)("stable")("sites").get_items():
            if sites is None or site in sites:
                return g5k(session)("stable")("sites")(site)(items_name).get_items_filtered(data=not quiet,
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
        target_sites = g5k(session)("stable")("sites").get_items()
    else:
        target_sites = sites_hints

    for site in target_sites:
        try:
            items_for_site = g5k(session)("stable")("sites")(site)(item)(uid).get_raw()
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

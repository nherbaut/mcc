import logging
import sys

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
    :param dfilter: the dict which specifies the values to test. {"a":"b","c!":"d"} <=> d1["a"]=="b" and d2["a"]!="d"
    :return: True i
    '''
    for k, v in dfilter.items():
        if k[-1] == '!':
            if d1.get(k[:-1], None) == dfilter[k]:
                return False
        else:
            if d1.get(k, None) != dfilter[k]:
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
                 reservation=None):

        data = {}
        data["resources"] = ",".join(["%s=%s" % item for item in resources])
        data["properties"] = ",".join(["%s=%s" % item for item in properties])
        data["types"] = types
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

import requests
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
                if {ka: va for ka, va in item.items() for kb, vb in item.items() if
                    ka in kwargs and kwargs[ka] == vb} == kwargs:
                    if include_data:
                        res.append(item)
                    else:
                        res.append(item["uid"])

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

    def post_job(self, node_count=10, walltime="2:00", types=["deploy"], command="sleep 7200"):
        # '{"resources": "nodes=2,walltime=02:00", "command": "sleep 7200", "types": ["deploy"]}'
        resources_values = "nodes=%d,walltime=%s" % (node_count, walltime)
        r = self.session.post("/".join(self.path_elements + ["jobs"]),
                              json={"resources": resources_values, "command": command, "types": types})
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

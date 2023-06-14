import requests

class api_ops:
    @staticmethod
    def api_get(endpoint, header, param):
        if header is None and param is None:
            resp = requests.get(url=endpoint)
        elif header is not None and param is None:
            resp = requests.get(url=endpoint, headers=header)
        elif header is None and param is not None:
            resp = requests.get(url=endpoint, params=param)
        else:
            resp = requests.get(url=endpoint, params=param, headers=header)
        return resp

    @staticmethod
    def api_post(endpoint, header, payload, param):
        resp = None
        if header is None and payload is None and param is None:
            resp = requests.post(url=endpoint)
        elif header is not None and payload is None and param is None:
            resp = requests.post(url=endpoint, headers=header)
        elif header is not None and payload is None and param is not None:
            resp = requests.post(url=endpoint, headers=header, params=param)
        elif header is None and payload is not None and param is None:
            resp = requests.post(url=endpoint, json=payload)
        elif header is None and payload is not None and param is not None:
            resp = requests.post(url=endpoint, json=payload, params=param)
        elif header is not None and payload is not None and param is None:
            resp = requests.post(url=endpoint, json=payload, headers=header)
        elif header is not None and payload is not None and param is not None:
            resp = requests.post(url=endpoint, json=payload, headers=header, params=param)
        return resp

    @staticmethod
    def api_put(endpoint, header, payload, param):
        resp = None
        if header is None and payload is None and param is None:
            resp = requests.put(url=endpoint)
        elif header is not None and payload is None and param is None:
            resp = requests.put(url=endpoint, headers=header)
        elif header is not None and payload is None and param is not None:
            resp = requests.put(url=endpoint, headers=header, params=param)
        elif header is None and payload is not None and param is None:
            resp = requests.put(url=endpoint, json=payload)
        elif header is None and payload is not None and param is not None:
            resp = requests.put(url=endpoint, json=payload, params=param)
        elif header is not None and payload is not None and param is None:
            resp = requests.put(url=endpoint, json=payload, headers=header)
        elif header is not None and payload is not None and param is not None:
            resp = requests.put(url=endpoint, json=payload, headers=header, params=param)
        return resp

    @staticmethod
    def api_delete(endpoint, header, param):
        if header is None and param is None:
            resp = requests.delete(url=endpoint)
        elif header is not None and param is None:
            resp = requests.delete(url=endpoint, headers=header)
        elif header is None and param is not None:
            resp = requests.delete(url=endpoint, params=param)
        else:
            resp = requests.delete(url=endpoint, headers=header, params=param)
        return resp

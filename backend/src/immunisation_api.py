import requests


class ImmunisationApi:
    def __init__(self, url):
        self.url = url

    def post_event(self, payload):
        headers = {
            "Content-Type": "application/fhir+json",
        }
        endpoint = f"{self.url}/event"
        response = requests.post(url=endpoint, json=payload, headers=headers)

        return response

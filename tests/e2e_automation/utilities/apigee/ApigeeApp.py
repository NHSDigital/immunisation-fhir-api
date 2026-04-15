"""Simple data class to hold the required attributes of an Apigee App"""

from dataclasses import dataclass


@dataclass
class ApigeeApp:
    callback_url: str
    client_id: str
    client_secret: str
    supplier: str

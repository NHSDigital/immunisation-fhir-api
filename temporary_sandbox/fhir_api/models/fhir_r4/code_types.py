"""Literal Code types used by data models"""

from typing import Literal

contact_point_system_types = Literal[
    "phone", "fax", "email", "pager", "url", "sms", "other"
]
contact_point_use_types = Literal["home", "work", "temp", "old", "mobile"]

address_use_type = Literal["home", "work", "temp", "old", "billing"]
address_type_type = Literal["postal", "physical", "both"]

human_name_use = Literal[
    "usual", "official", "temp", "nickname", "anonymous", "old", "maiden"
]

gender = Literal["male", "female", "other", "unknown"]

patient_type = Literal["replaced-by", "replaces", "refer", "seealso"]

status_codes = Literal["completed", "entered-in-error", "not-done"]

link_code = Literal["replaced-by", "replaces", "refer", "seealso"]

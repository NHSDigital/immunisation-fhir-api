from collections import OrderedDict

import copy

from batch.decorators import decorate

"""Transform the raw records into FHIR immunization resource
Design notes: The record stays as a OrderedDict to preserve the order of the fields. At no point we impose
type constraints on the fields or the record as a whole. This is because the batch data can contain legacy data and data
with various quality. A decorate function receives a dictionary of current immunization object and adds the appropriate
fields to it. This decorate function is also in charge of validation if any and raises an exception. The caller will
collect the exceptions and carries on. So at then end we either have a list of errors with raises the final exception or
we return immunization object.
`decorate` function can be considered an integral part of the transformer. It's been placed in its own module to keep
the transformer module clean and focused on the transformation logic.
"""

RecordDict = OrderedDict[str, str]
"""A record of fields with the same order as headers"""


class DataRecordTransformer:
    raw_imms: dict

    def __init__(self):
        # Initialise the immunization resource with the base model
        self.raw_imms = {
            "resourceType": "Immunization",
            "contained": [],
            "extension": [],
            "performer": [],
        }

    def transform(self, record: RecordDict) -> dict:
        imms = copy.deepcopy(self.raw_imms)
        decorate(imms, record)
        return imms

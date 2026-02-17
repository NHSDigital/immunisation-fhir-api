from enum import Enum

# Static constants for the MNS notification creation process
SPEC_VERSION = "1.0"
IMMUNISATION_TYPE = "imms-vaccinations-2"


# Fields from the incoming SQS message that forms part of the base schema and filtering attributes for MNS notifications
class SQSEventFields(Enum):
    IMMUNISATION_TYPE = IMMUNISATION_TYPE
    DATE_AND_TIME_KEY = "DATE_AND_TIME"
    NHS_NUMBER_KEY = "NHS_NUMBER"
    IMMUNISATION_ID_KEY = "ImmsID"
    SOURCE_ORGANISATION_KEY = "SITE_CODE"
    SOURCE_APPLICATION_KEY = "SupplierSystem"
    VACCINE_TYPE = "VACCINE_TYPE"
    ACTION = "Operation"

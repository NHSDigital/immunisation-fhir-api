import datetime
from dataclasses import dataclass


@dataclass
# > This class represents a simple immunization
class ImmunizationModel:
    NHS_NUMBER: str = None
    PERSON_FORENAME: str = None
    PERSON_SURNAME: str = None
    PERSON_DOB: datetime.date = None  # YYYY-MM-DD
    PERSON_GENDER_CODE: str = None
    PERSON_POSTCODE: str = None
    DATE_AND_TIME: datetime = None  # YYYY-MM-DDThh:mm:ss+zz (2020-12-14T10:08:15+00)
    SITE_CODE: str = None
    SITE_NAME: str = None
    UNIQUE_ID: str = None
    UNIQUE_ID_URI: str = None
    ACTION_FLAG: str = None
    PERFORMING_PROFESSIONAL_FORENAME: str = None
    PERFORMING_PROFESSIONAL_SURNAME: str = None
    PERFORMING_PROFESSIONAL_BODY_REG_CODE: str = None
    PERFORMING_PROFESSIONAL_BODY_REG_URI: str = None
    SDS_JOB_ROLE_NAME: str = None
    RECORDED_DATE: datetime.date = None  # YYYY-MM-DD
    PRIMARY_SOURCE: bool = None
    REPORT_ORIGIN: str = None
    VACCINATION_PROCEDURE_CODE: str = None
    VACCINATION_PROCEDURE_TERM: str = None
    VACCINATION_SITUATION_CODE: str = None
    VACCINATION_SITUATION_TERM: str = None
    NOT_GIVEN: str = None
    REASON_NOT_GIVEN_CODE: str = None
    REASON_NOT_GIVEN_TERM: str = None
    DOSE_SEQUENCE: int = None
    VACCINE_PRODUCT_CODE: str = None
    VACCINE_PRODUCT_TERM: str = None
    VACCINE_MANUFACTURER: str = None
    BATCH_NUMBER: str = None
    EXPIRY_DATE: datetime.date = None
    SITE_OF_VACCINATION_CODE: str = None
    SITE_OF_VACCINATION_TERM: str = None
    ROUTE_OF_VACCINATION_CODE: str = None
    ROUTE_OF_VACCINATION_TERM: str = None
    DOSE_AMOUNT: str = None
    DOSE_UNIT_CODE: str = None
    DOSE_UNIT_TERM: str = None
    INDICATION_CODE: str = None
    INDICATION_TERM: str = None
    NHS_NUMBER_STATUS_INDICATOR_CODE: str = None
    NHS_NUMBER_STATUS_INDICATOR_DESCRIPTION: str = None
    SITE_CODE_TYPE_URI: str = None
    LOCAL_PATIENT_ID: str = None
    LOCAL_PATIENT_URI: str = None
    CONSENT_FOR_TREATMENT_CODE: str = None
    CONSENT_FOR_TREATMENT_DESCRIPTION: str = None
    CARE_SETTING_TYPE_CODE: str = None
    CARE_SETTING_TYPE_DESCRIPTION: str = None
    IP_ADDRESS: str = None
    USER_ID: str = None
    USER_NAME: str = None
    USER_EMAIL: str = None
    SUBMITTED_TIMESTAMP: str = None  # YYYY-MM-DDThh:mm:ss+zz
    LOCATION_CODE: str = None
    LOCATION_CODE_TYPE_URI: str = None
    VACCINE_CUSTOM_LIST: str = None
    REDUCE_VALIDATION_CODE: str = None
    REDUCE_VALIDATION_REASON: str = None

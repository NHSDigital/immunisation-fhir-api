"""CSV Immunization Model"""

import dateutil.parser
from datetime import date
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, validator
from models.nhs_validators import (
    NHSImmunizationValidators,
    NHSPatientValidators,
    NHSPractitionerValidators,
)


class CsvImmunizationModel(BaseModel):
    """Pydantic CSV Immunization BaseModel"""

    NHS_NUMBER: str = None
    PERSON_FORENAME: str = None
    PERSON_SURNAME: str = None
    PERSON_DOB: Optional[date]
    PERSON_GENDER_CODE: str = None
    PERSON_POSTCODE: str = None
    DATE_AND_TIME: datetime  # YYYY-MM-DDThh:mm:ss+zz (2020-12-14T10:08:15+00)
    SITE_CODE: str = None
    SITE_NAME: str = None
    UNIQUE_ID: str = None
    UNIQUE_ID_URI: str = None
    ACTION_FLAG: str = None
    PERFORMING_PROFESSIONAL_SURNAME: str = None
    PERFORMING_PROFESSIONAL_FORENAME: str = None
    PERFORMING_PROFESSIONAL_BODY_REG_URI: str = None
    PERFORMING_PROFESSIONAL_BODY_REG_CODE: str = None
    SDS_JOB_ROLE_NAME: str = None
    RECORDED_DATE: Optional[date]
    PRIMARY_SOURCE: Any = None  # Use Any to allow any type, including bool or None
    REPORT_ORIGIN: str = None
    NOT_GIVEN: str = None
    VACCINATION_PROCEDURE_CODE: str = None
    VACCINATION_PROCEDURE_TERM: str = None
    VACCINATION_SITUATION_CODE: str = None
    VACCINATION_SITUATION_TERM: str = None
    REASON_NOT_GIVEN_CODE: str = None
    REASON_NOT_GIVEN_TERM: str = None
    DOSE_SEQUENCE: int = None
    VACCINE_PRODUCT_CODE: str = None
    VACCINE_PRODUCT_TERM: str = None
    VACCINE_MANUFACTURER: str = None
    BATCH_NUMBER: str = None
    EXPIRY_DATE: Optional[date]
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
    SUBMITTED_TIMESTAMP: Optional[datetime]  # YYYY-MM-DDThh:mm:ss+zz
    LOCATION_CODE: str = None
    LOCATION_CODE_TYPE_URI: str = None
    VACCINE_CUSTOM_LIST: str = None
    REDUCE_VALIDATION_REASON: str = None
    REDUCE_VALIDATION_CODE: Any = (
        None  # Use Any to allow any type, including bool or None
    )

    @validator("NHS_NUMBER")
    def validate_nhs_number(cls, value):
        """Validate NHS Number"""
        return NHSImmunizationValidators.validate_patient_identifier_value(value)

    @validator("PERSON_DOB", pre=True, always=True)
    def validate_person_dob(cls, value):
        """Validate Person DOB"""
        return NHSPatientValidators.validate_birth_date(value)

    @validator("PERSON_GENDER_CODE", pre=True, always=True)
    def validate_person_gender_code(cls, value):
        """Validate person gender code"""
        return NHSPatientValidators.validate_gender(value)

    @validator("PERSON_POSTCODE", pre=True, always=True)
    def validate_person_postcode(cls, value):
        """Validate person postcode"""
        return NHSPatientValidators.validate_address_postal_code(value)

    @validator("DATE_AND_TIME", pre=True, always=True)
    def validate_date_and_time(cls, value):
        """Validate date and time"""
        value = dateutil.parser.parse(value)
        return NHSImmunizationValidators.validate_occurrence_date_time(value)

    @validator("SITE_CODE", pre=True, always=True)
    def validate_site_code(cls, value):
        """Validate site code"""
        return NHSImmunizationValidators.validate_questionnaire_site_code_code(value)

    @validator("ACTION_FLAG", pre=True, always=True)
    def validate_action_flag(cls, value):
        """Validate action flag"""
        return NHSImmunizationValidators.validate_status(value)

    @validator("PERFORMING_PROFESSIONAL_FORENAME", pre=True, always=True)
    def validate_professional_forename(cls, v, values):
        """Validate performing professional forename"""
        return NHSPractitionerValidators.validate_performing_professional_forename(
            "FLU",  # TODO: This is hardcoded for now. We need to get this from the CSV
            values.get("PERFORMING_PROFESSIONAL_SURNAME"),
            values.get("PERFORMING_PROFESSIONAL_FORENAME"),
        )

    @validator("PERFORMING_PROFESSIONAL_BODY_REG_CODE", pre=True, always=True)
    def validate_professional_reg_code(cls, v, values):
        """Validate performing professional body reg code"""
        return NHSPractitionerValidators.validate_performing_professional_body_reg_code(
            v, values.get("PERFORMING_PROFESSIONAL_BODY_REG_URI", None)
        )

    @validator("RECORDED_DATE", pre=True, always=True)
    def validate_recorded_date(cls, value):
        """Validate recorded date"""
        return NHSImmunizationValidators.validate_recorded(value)

    @validator("REPORT_ORIGIN", pre=True, always=True)
    def validate_report_origin(cls, v, values):
        """Validate report origin"""
        primary_source = values["PRIMARY_SOURCE"]
        return NHSImmunizationValidators.validate_report_origin_text(v, primary_source)

    @validator("NOT_GIVEN", pre=True, always=True)
    def validate_not_given_flag(cls, value):
        """Validate not given flag"""
        return NHSImmunizationValidators.validate_not_given(value)

    @validator("VACCINATION_PROCEDURE_CODE", pre=True, always=True)
    def validate_vaccination_procedure_code(cls, v, values):
        """Validate vaccination procedure code"""
        return NHSImmunizationValidators.validate_vaccination_procedure_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("VACCINATION_SITUATION_CODE", pre=True, always=True)
    def validate_vaccination_situatuion_code(cls, v, values):
        """Validate vaccination situation code"""
        return NHSImmunizationValidators.validate_vaccination_situation_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("REASON_NOT_GIVEN_CODE", pre=True, always=True)
    def validate_reason_not_given_code(cls, v, values):
        """Validate reason not given code"""
        return NHSImmunizationValidators.validate_reason_not_given_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("DOSE_SEQUENCE", pre=True, always=True)
    def validate_dose_sequence(cls, v, values):
        """Validate dose sequence"""
        return NHSImmunizationValidators.validate_dose_sequence(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("VACCINE_PRODUCT_CODE", pre=True, always=True)
    def validate_vaccine_product_code(cls, v, values):
        """Validate vaccine product code"""
        return NHSImmunizationValidators.validate_vaccine_product_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("VACCINE_MANUFACTURER", pre=True, always=True)
    def validate_vaccine_manufacturer(cls, v, values):
        """Validate vaccine manufacturer"""
        return NHSImmunizationValidators.validate_vaccine_manufacturer(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("BATCH_NUMBER", pre=True, always=True)
    def validate_batch_number(cls, v, values):
        """Validate batch number"""
        return NHSImmunizationValidators.validate_batch_number(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("EXPIRY_DATE", pre=True, always=True)
    def validate_expiry_date(cls, v, values):
        """Validate expiry date"""
        return NHSImmunizationValidators.validate_expiry_date(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("ROUTE_OF_VACCINATION_CODE", pre=True, always=True)
    def validate_route_of_vaccination_code(cls, v, values):
        """Validate route of vaccination code"""
        return NHSImmunizationValidators.validate_route_of_vaccination_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("DOSE_AMOUNT", pre=True, always=True)
    def validate_dose_amount(cls, v, values):
        """Validate dose amount"""
        return NHSImmunizationValidators.validate_dose_amount(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("DOSE_UNIT_CODE", pre=True, always=True)
    def validate_dose_unit_code(cls, v, values):
        """Validate dose unit code"""
        return NHSImmunizationValidators.validate_dose_unit_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("INDICATION_CODE", pre=True, always=True)
    def validate_indication_code(cls, v, values):
        """Validate indication code"""
        return NHSImmunizationValidators.validate_indication_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("CONSENT_FOR_TREATMENT_CODE", pre=True, always=True)
    def validate_consent_for_treatment_code(cls, v, values):
        """Validate consent for treatment code"""
        return NHSImmunizationValidators.validate_consent_for_treatment_code(
            v, values.get("NOT_GIVEN", None)
        )

    @validator("SUBMITTED_TIMESTAMP", pre=True, always=True)
    def validate_submitted_timestamp(cls, value):
        """Validate submitted timestamp"""
        return NHSImmunizationValidators.validate_submitted_timestamp(value)

    @validator("LOCATION_CODE", pre=True, always=True)
    def validate_location_code(cls, value):
        """Validate location code"""
        return NHSImmunizationValidators.validate_location_code(value)

    @validator("REDUCE_VALIDATION_CODE", pre=True, always=True)
    def validate_reduce_validation_code(cls, v, values):
        """Validate reduce validation code"""
        return NHSImmunizationValidators.validate_reduce_validation_code(
            v, values.get("REDUCE_VALIDATION_REASON", None)
        )

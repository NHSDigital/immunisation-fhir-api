from datetime import date
from datetime import datetime
from pydantic import BaseModel, validator
from typing import Optional, Any
import re


class Constants:
    vaccination_not_given_flag: str = "not-done"
    vaccination_given_flag: str = "empty"

    def convert_iso8601_to_datetime(iso_datetime_str):
        try:
            time_str = "T00:00:00+00:00"
            # Check if time information is present
            if "T" in iso_datetime_str:
                # Check if timezone information is present
                if "+" in iso_datetime_str:
                    # Add the colon (:00) in the timezone offset
                    timestamp_str_with_colon = iso_datetime_str + ":00"
                    dt_obj = datetime.strptime(
                        timestamp_str_with_colon, "%Y-%m-%dT%H:%M:%S%z"
                    )
                else:
                    dt_obj = datetime.strptime(iso_datetime_str, "%Y-%m-%dT%H:%M:%S")
            else:
                # Add the the timezone offset
                timestamp_str_with_colon = iso_datetime_str + time_str
                dt_obj = datetime.strptime(
                    timestamp_str_with_colon, "%Y-%m-%dT%H:%M:%S%z"
                )

            return dt_obj
        except ValueError:
            raise ValueError("Invalid datetime format. Use YYYY-MM-DDThh:mm:ss+zz.")

    def convert_to_date(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    def is_urn_resource(s):
        # Check if the lowercase version of the string starts with "urn"
        return s.lower().startswith("urn")

    def if_vaccine_not_give(not_given_flag):
        if not not_given_flag or not_given_flag == Constants.vaccination_given_flag:
            return False
        else:
            if not_given_flag == Constants.vaccination_not_given_flag:
                return True

    def has_max_decimal_places(input_string, max_places=4):
        # Define a regular expression pattern for matching up to four decimal places
        pattern = r"^\d+(\.\d{1,4})?$"

        # Use re.match to check if the input matches the pattern
        return bool(re.match(pattern, input_string))


# > This class represents a simple immunization
class ImmunizationModel(BaseModel, Constants):
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
        if value:
            value = value.replace(" ", "")  # Removing any spaces
            if len(value) != 10:
                raise ValueError("NHS_NUMBER must consist of 10 digits.")
        return value

    @validator("PERSON_DOB", pre=True, always=True)
    def validate_person_dob(cls, value):
        # Assuming the date format is YYYY-MM-DD
        if value:
            parsed_date = Constants.convert_to_date(value)
            return parsed_date
        return None

    @validator("PERSON_GENDER_CODE", pre=True, always=True)
    def validate_person_gender_code(cls, value):
        if value:
            if value not in {"0", "1", "2", "9"}:
                raise ValueError(
                    "Invalid value for PERSON_GENDER_CODE. It must be 0, 1, 2, or 9."
                )
            return value

    @validator("PERSON_POSTCODE", pre=True, always=True)
    def validate_person_postcode(cls, value):
        if value:
            post_code = value.replace(" ", "")
            if len(post_code) > 8:
                raise ValueError("PERSON_POSTCODE must be less than 8 digits.")
        return value

    @validator("DATE_AND_TIME", pre=True, always=True)
    def validate_date_and_time(cls, value):
        if not value:
            raise ValueError("DATE_AND_TIME is a mandatory field.")
        parsed_datetime = Constants.convert_iso8601_to_datetime(value)
        return parsed_datetime

    @validator("SITE_CODE", pre=True, always=True)
    def validate_site_code(cls, value):
        if not value:
            raise ValueError("SITE_CODE is a mandatory field.")
        else:
            if Constants.is_urn_resource(value):
                raise ValueError("SITE_CODE must not be a urn code")
            else:
                return value

    @validator("ACTION_FLAG", pre=True, always=True)
    def validate_action_flag(cls, value):
        if not value:
            raise ValueError("ACTION_FLAG is a mandatory field.")
        else:
            if not (value in ["completed", "entered-in-error"]):
                raise ValueError(
                    "ACTION_FLAG shouled be 'completed' or 'entered-in-error' "
                )
            else:
                return value

    @validator("PERFORMING_PROFESSIONAL_FORENAME", pre=True, always=True)
    def validate_professional_forename(cls, v, values):
        surname = values["PERFORMING_PROFESSIONAL_SURNAME"]
        if v:
            if not surname:
                raise ValueError(
                    "If PERFORMING_PROFESSIONAL_FORENAME is given, PERFORMING_PROFESSIONAL_SURNAME must also be given"
                )
            else:
                return v
        else:
            if surname:
                raise ValueError(
                    "If PERFORMING_PROFESSIONAL_SURNAME is given, PERFORMING_PROFESSIONAL_FORENAME must also be given"
                )

    @validator("PERFORMING_PROFESSIONAL_BODY_REG_CODE", pre=True, always=True)
    def validate_professional_reg_code(cls, v, values):
        if v:
            reg_uri = values["PERFORMING_PROFESSIONAL_BODY_REG_URI"]
            # if is_empty(reg_uri):
            if not reg_uri:
                raise ValueError(
                    "If PERFORMING_PROFESSIONAL_BODY_REG_CODE is given, "
                    "PERFORMING_PROFESSIONAL_BODY_REG_URI must also be given"
                )
            else:
                return v

    @validator("RECORDED_DATE", pre=True, always=True)
    def validate_recorded_date(cls, value):
        # Assuming the date format is YYYY-MM-DD
        if value:
            parsed_date = Constants.convert_to_date(value)
            return parsed_date
        return None

    @validator("REPORT_ORIGIN", pre=True, always=True)
    def validate_report_origin(cls, v, values):
        primary_source = values["PRIMARY_SOURCE"]
        if (primary_source) and (not v):
            raise ValueError(
                "REPORT_ORIGIN is a mandatory field, when PRIMARY_SOURCE is given"
            )
        return v

    @validator("NOT_GIVEN", pre=True, always=True)
    def validate_not_given_flag(cls, value, values):
        if value:
            if not (
                value == Constants.vaccination_not_given_flag
                or value == Constants.vaccination_given_flag
            ):
                raise ValueError("NOT_GIVEN flag should be 'not-done' or 'empty' ")
            else:
                return value

    @validator("VACCINATION_PROCEDURE_CODE", pre=True, always=True)
    def validate_vaccination_procedure_code(cls, v, values):
        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "VACCINATION_PROCEDURE_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("VACCINATION_SITUATION_CODE", pre=True, always=True)
    def validate_vaccination_situatuion_code(cls, v, values):
        if "NOT_GIVEN" in values:
            if Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "VACCINATION_SITUATION_CODE is a mandatory field, when NOT_GIVEN=TRUE"
                    )
        return v

    @validator("REASON_NOT_GIVEN_CODE", pre=True, always=True)
    def validate_reason_not_given_code(cls, v, values):
        if "NOT_GIVEN" in values:
            if Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "REASON_NOT_GIVEN_CODE is a mandatory field, when NOT_GIVEN=TRUE"
                    )
        return v

    @validator("DOSE_SEQUENCE", pre=True, always=True)
    def validate_dose_sequence(cls, v, values):
        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "DOSE_SEQUENCE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
            else:
                return 1
        return v

    @validator("VACCINE_PRODUCT_CODE", pre=True, always=True)
    def validate_vaccine_product_code(cls, v, values):
        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "VACCINE_PRODUCT_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
            else:
                return 1
        return v

    @validator("VACCINE_MANUFACTURER", pre=True, always=True)
    def validate_vaccine_manufacturer(cls, v, values):
        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "VACCINE_MANUFACTURER is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("BATCH_NUMBER", pre=True, always=True)
    def validate_batch_number(cls, v, values):
        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "BATCH_NUMBER is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("EXPIRY_DATE", pre=True, always=True)
    def validate_expiry_date(cls, v, values):
        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "EXPIRY_DATE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
                else:
                    parsed_date = Constants.convert_to_date(v)
                    return parsed_date

    @validator("ROUTE_OF_VACCINATION_CODE", pre=True, always=True)
    def validate_route_of_vaccination_code(cls, v, values):

        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "ROUTE_OF_VACCINATION_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("DOSE_AMOUNT", pre=True, always=True)
    def validate_dose_amount(cls, v, values):

        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "DOSE_AMOUNT is a mandatory field, when NOT_GIVEN=FALSE"
                    )
                else:
                    if not (Constants.has_max_decimal_places(v)):
                        raise ValueError(
                            "DOSE_AMOUNT should have maximum 4 decimal places"
                        )
                    return v
        return None

    @validator("DOSE_UNIT_CODE", pre=True, always=True)
    def validate_dose_unit_code(cls, v, values):

        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "DOSE_UNIT_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("INDICATION_CODE", pre=True, always=True)
    def validate_indication_code(cls, v, values):

        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "INDICATION_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("CONSENT_FOR_TREATMENT_CODE", pre=True, always=True)
    def validate_consent_for_treatment_code(cls, v, values):

        if "NOT_GIVEN" in values:
            if not Constants.if_vaccine_not_give(values["NOT_GIVEN"]):
                if not v:
                    raise ValueError(
                        "CONSENT_FOR_TREATMENT_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                    )
        return v

    @validator("SUBMITTED_TIMESTAMP", pre=True, always=True)
    def validate_submitted_timestamp(cls, value):
        if value:
            parsed_datetime = Constants.convert_iso8601_to_datetime(value)
            return parsed_datetime

    @validator("LOCATION_CODE", pre=True, always=True)
    def validate_location_code(cls, value):
        if value:
            post_code = value.replace(" ", "")
            if len(post_code) > 8:
                raise ValueError("LOCATION_CODE must be less than 8 digits.")
            return value
        else:
            return "X99999"

    @validator("REDUCE_VALIDATION_CODE", pre=True, always=True)
    def validate_reduce_validation_code(cls, v, values):
        reduce_validation_reason = values["REDUCE_VALIDATION_REASON"]
        if v == "True":
            if not reduce_validation_reason:
                raise ValueError(
                    "REDUCE_VALIDATION_REASON is a mandatory field, when REDUCE_VALIDATION_CODE is True"
                )
            return True
        else:
            return False

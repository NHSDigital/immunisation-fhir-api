"""NHS Validator methods"""

from datetime import datetime, timezone

from mappings import VaccineTypes
from models.constants import Constants


class NHSImmunizationValidators:
    """NHS Immunization specific validator methods"""

    @staticmethod
    def validate_target_disease_type(disease_type: str):
        """Validate disease type"""
        if disease_type not in Constants.VALID_DISEASE_TYPES:
            raise ValueError("TARGET_DISEASE_CODE must be for valid disease type")
        return disease_type

    @staticmethod
    def validate_patient_identifier_value(patient_identifier_value):
        """Validate patient identifier value (NHS number)"""
        if patient_identifier_value:
            if " " in patient_identifier_value:
                raise ValueError("PATIENT_IDENTIFIER_VALUE MUST NOT CONTAIN SPACES")
            if len(patient_identifier_value) != 10:
                raise ValueError(
                    "PATIENT_IDENTIFIER_VALUE (NHS number) must consist of 10 digits."
                )

        return patient_identifier_value

    @staticmethod
    def validate_occurrence_date_time(occurrence_date_time: datetime):
        """Validate occurrence date and time"""
        if not occurrence_date_time:
            raise ValueError("OCCURRENCE_DATE_TIME is a mandatory field.")

        if not hasattr(occurrence_date_time, "time"):
            occurrence_date_time = datetime.combine(
                occurrence_date_time, datetime.min.time()
            )
        elif occurrence_date_time.time() is None:
            occurrence_date_time = occurrence_date_time.replace(
                hour=0, minute=0, second=0
            )

        if occurrence_date_time.tzinfo is None:
            occurrence_date_time = occurrence_date_time.replace(tzinfo=timezone.utc)

        if occurrence_date_time.date() > datetime.now().date():
            raise ValueError("OCCURRENCE_DATE_TIME must not be in the future.")

        return occurrence_date_time.isoformat()

    @staticmethod
    def validate_questionnaire_site_code_code(questionnaire_site_code_code):
        """
        Validate questionnaire site code (code of the Commissioned Healthcare Provider who has
        administered the vaccination)
        """
        if not questionnaire_site_code_code:
            raise ValueError("QUESTIONNAIRE_SITE_CODE_CODE is a mandatory field.")

        if (
            Constants.is_urn_resource(questionnaire_site_code_code)
            or questionnaire_site_code_code.isnumeric()
        ):
            raise ValueError("QUESTIONNAIRE_SITE_CODE_CODE must not be a urn code")

        return questionnaire_site_code_code

    @staticmethod
    def validate_identifier_value(identifier_value):
        """Validate immunization identifier value"""
        if not identifier_value:
            raise ValueError("IDENTIFIER_VALUE is a mandatory field")
        return identifier_value

    @staticmethod
    def validate_identifier_system(identifier_system):
        """Validate immunization identifier system"""
        if not identifier_system:
            raise ValueError("IDENTIFIER_SYSTEM is a mandatory field")
        return identifier_system

    @staticmethod
    def validate_status(status):
        """Validate status (action flag)"""
        if not status:
            raise ValueError("STATUS is a mandatory field.")

        if status not in Constants.STATUSES:
            raise ValueError(
                'STATUS should be "completed", "entered-in-error" or "not-done"'
            )

        return status

    @staticmethod
    def validate_recorded(recorded):
        """Validate recorded (recorded date)"""
        if not recorded:
            raise ValueError("RECORDED is a mandatory field")

        parsed_date = Constants.convert_to_date(recorded)
        return parsed_date

    @staticmethod
    def validate_primary_source(primary_source):
        """Validate primary source"""
        if not primary_source and primary_source is not False:
            raise ValueError("PRIMARY_SOURCE is a mandatory field.")
        if primary_source not in Constants.PRIMARY_SOURCE:
            raise ValueError(
                "PRIMARY_SOURCE should be boolean true or false (case-sensitive)"
            )

        return primary_source

    @staticmethod
    def validate_report_origin_text(report_origin_text, primary_source):
        """Validate report origin text"""
        if not primary_source and not report_origin_text:
            error = (
                "REPORT_ORIGIN_TEXT is a mandatory field, and must be a non-empty string,",
                "when PRIMARY_SOURCE is false",
            )
            raise ValueError(" ".join(error))
        if report_origin_text:
            if len(report_origin_text) > 100:
                raise ValueError(
                    "REPORT_ORIGIN_TEXT has maximum length of 100 characters"
                )
        return report_origin_text

    @staticmethod
    def validate_not_given(not_given):
        """Validate not given flag"""
        if not_given:
            if not (
                not_given == Constants.VACCINATION_NOT_GIVEN_FLAG
                or not_given == Constants.VACCINATION_GIVEN_FLAG
            ):
                raise ValueError("NOT_GIVEN flag should be 'empty' or 'not-done'")
        return not_given

    @staticmethod
    def validate_vaccination_procedure_code(vaccination_procedure_code, not_given):
        """Validate vaccination procedure code"""
        if not_given:
            if (
                not Constants.if_vaccine_not_give(not_given)
                and not vaccination_procedure_code
            ):
                raise ValueError(
                    "VACCINATION_PROCEDURE_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return vaccination_procedure_code

    @staticmethod
    def validate_vaccination_situation_code(vaccination_situation_code, not_given):
        """Validate vaccination situation code"""
        if not_given:
            if (
                Constants.if_vaccine_not_give(not_given)
                and not vaccination_situation_code
            ):
                raise ValueError(
                    "VACCINATION_SITUATION_CODE is a mandatory field, when NOT_GIVEN=TRUE"
                )
        return vaccination_situation_code

    @staticmethod
    def validate_reason_not_given_code(reason_not_given_code, not_given):
        """Validate reason not given code"""
        if not_given:
            if Constants.if_vaccine_not_give(not_given) and not reason_not_given_code:
                raise ValueError(
                    "REASON_NOT_GIVEN_CODE is a mandatory field, when NOT_GIVEN=TRUE"
                )
        return reason_not_given_code

    @staticmethod
    def validate_dose_sequence(dose_sequence, not_given):
        """Validate dose sequence"""
        if not_given:
            if not Constants.if_vaccine_not_give(not_given) and not dose_sequence:
                raise ValueError(
                    "DOSE_SEQUENCE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return dose_sequence

    @staticmethod
    def validate_vaccine_product_code(vaccine_product_code, not_given):
        """Validate vaccine product code"""
        if not_given:
            if (
                not Constants.if_vaccine_not_give(not_given)
                and not vaccine_product_code
            ):
                raise ValueError(
                    "VACCINE_PRODUCT_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return vaccine_product_code

    @staticmethod
    def validate_vaccine_manufacturer(vaccine_manufacturer, not_given):
        """Validate vaccine manufacturer"""
        if not_given:
            if (
                not Constants.if_vaccine_not_give(not_given)
                and not vaccine_manufacturer
            ):
                raise ValueError(
                    "VACCINE_MANUFACTURER is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return vaccine_manufacturer

    @staticmethod
    def validate_batch_number(batch_number, not_given):
        """Validate batch number"""
        if not_given:
            if not Constants.if_vaccine_not_give(not_given) and not batch_number:
                raise ValueError(
                    "VACCINE_BATCH_NUMBER is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return batch_number

    @staticmethod
    def validate_expiry_date(expiry_date, not_given):
        """Validate expiry date"""
        if not_given:
            if not Constants.if_vaccine_not_give(not_given) and not expiry_date:
                raise ValueError(
                    "EXPIRY_DATE is a mandatory field, when NOT_GIVEN=FALSE"
                )
            parsed_date = Constants.convert_to_date(expiry_date)
            return parsed_date

    @staticmethod
    def validate_route_of_vaccination_code(route_of_vaccination_code, not_given):
        """Validate route of vaccination code"""
        if not_given:
            if (
                not Constants.if_vaccine_not_give(not_given)
                and not route_of_vaccination_code
            ):
                raise ValueError(
                    "ROUTE_OF_VACCINATION_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return route_of_vaccination_code

    @staticmethod
    def validate_dose_amount(dose_amount, not_given):
        """Validate dose amount"""
        if not_given:
            if not Constants.if_vaccine_not_give(not_given) and not dose_amount:
                raise ValueError(
                    "DOSE_AMOUNT is a mandatory field, when NOT_GIVEN=FALSE"
                )
            if not Constants.has_max_decimal_places(dose_amount):
                raise ValueError("DOSE_AMOUNT must have a maximum of 4 decimal places")
            return dose_amount
        return None

    @staticmethod
    def validate_dose_unit_code(dose_unit_code, not_given):
        """Validate dose unit code"""
        if not_given:
            if not Constants.if_vaccine_not_give(not_given) and not dose_unit_code:
                raise ValueError(
                    "DOSE_UNIT_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return dose_unit_code

    @staticmethod
    def validate_indication_code(indication_code, not_given):
        """Validate indication code"""
        if not_given:
            if not Constants.if_vaccine_not_give(not_given) and not indication_code:
                raise ValueError(
                    "INDICATION_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return indication_code

    @staticmethod
    def validate_consent_for_treatment_code(consent_for_treatment_code, not_given):
        """Validate consent for treatment code"""
        if not_given:
            if (
                not Constants.if_vaccine_not_give(not_given)
                and not consent_for_treatment_code
            ):
                raise ValueError(
                    "CONSENT_FOR_TREATMENT_CODE is a mandatory field, when NOT_GIVEN=FALSE"
                )
        return consent_for_treatment_code

    @staticmethod
    def validate_submitted_timestamp(submitted_timestamp):
        """Validate submitted timestamp"""
        if submitted_timestamp:
            parsed_datetime = Constants.convert_iso8601_to_datetime(submitted_timestamp)
            return parsed_datetime

    @staticmethod
    def validate_location_code(location_code):
        """Validate location code"""
        if location_code:
            postcode = location_code.replace(" ", "")
            if len(postcode) > 8:
                raise ValueError("LOCATION_CODE must be less than 8 characters.")
            return location_code
        return "X99999"

    @staticmethod
    def validate_reduce_validation_code(
        reduce_validation_code, reduce_validation_reason
    ):
        """Validate reduce validation code"""
        if reduce_validation_code == "True":
            if not reduce_validation_reason:
                raise ValueError(
                    "REDUCE_VALIDATION_REASON is a mandatory field, \
                        when REDUCE_VALIDATION_CODE is True"
                )
            return True
        return False


class NHSPatientValidators:
    """NHS Patient specific validator methods"""

    @staticmethod
    def validate_name_given(name_given):
        """Validate given name (forename)"""
        if not name_given:
            raise ValueError("NAME_GIVEN (forename) is a manadatory field")

        return name_given

    @staticmethod
    def validate_name_family(name_family):
        """Validate family name (surname)"""
        if not name_family:
            raise ValueError("NAME_FAMILY (surname) is a manadatory field")

        return name_family

    @staticmethod
    def validate_birth_date(birth_date):
        """Validate birth date"""
        if not birth_date:
            raise ValueError("BIRTH_DATE is a mandatory field")

        parsed_date = Constants.convert_to_date(birth_date)
        return parsed_date

    @staticmethod
    def validate_gender(gender):
        """Validate Person Gender Code"""
        if not gender:
            raise ValueError("GENDER is a mandatory field")

        if gender not in Constants.GENDERS:
            raise ValueError(
                "Invalid value for GENDER. It must be male, female, other, or unknown."
            )
        return gender

    @staticmethod
    def validate_address_postal_code(address_postal_code):
        """Validate adress postal code"""
        if not address_postal_code:
            raise ValueError("ADDRESS_POSTAL_CODE is a mandatory field")
        if len(address_postal_code.split(" ")) != 2:
            raise ValueError(
                "ADDRESS_POSTAL_CODE must be divided into two parts by a single space"
            )
        postal_code = address_postal_code.replace(" ", "")
        if len(postal_code) > 8:
            raise ValueError("ADDRESS_POSTAL_CODE must be less that 8 characters.")
        return address_postal_code


class NHSPractitionerValidators:
    """NHS Practitioner specific validator methods"""

    @staticmethod
    def validate_performing_professional_forename(
        disease_type, performing_professional_forename, performing_professional_surname
    ):
        """Validate performing professional forename"""
        excluded_disease_types = (VaccineTypes.hpv, VaccineTypes.mmr)
        if disease_type in excluded_disease_types and performing_professional_forename:
            raise ValueError(
                " ".join(
                    (
                        "PERFORMING_PROFESSIONAL_FORENAME",
                        f"is not allowed for: {str(excluded_disease_types)}",
                    )
                )
            )
        if performing_professional_surname and not performing_professional_forename:
            raise ValueError(
                " ".join(
                    (
                        "If PERFORMING_PROFESSIONAL_SURNAME is given,",
                        "PERFORMING_PROFESSIONAL_FORENAME must also be given",
                    )
                )
            )
        return performing_professional_forename

    @staticmethod
    def validate_performing_professional_surname(
        disease_type, performing_professional_surname, performing_professional_forename
    ):
        """Validate performing professional surname"""
        excluded_disease_types = (VaccineTypes.hpv, VaccineTypes.mmr)
        if disease_type in excluded_disease_types and performing_professional_surname:
            raise ValueError(
                " ".join(
                    (
                        "PERFORMING_PROFESSIONAL_SURNAME",
                        f"is not allowed for: {str(excluded_disease_types)}",
                    )
                )
            )
        if performing_professional_forename and not performing_professional_surname:
            raise ValueError(
                " ".join(
                    (
                        "If PERFORMING_PROFESSIONAL_FORENAME is given,",
                        "PERFORMING_PROFESSIONAL_SURNAME must also be given",
                    )
                )
            )
        return performing_professional_surname

    @staticmethod
    def validate_performing_professional_body_reg_code(
        performing_professional_body_reg_code, performing_professional_body_reg_uri
    ):
        """Validate performing professional body reg code"""
        if performing_professional_body_reg_code:
            if not performing_professional_body_reg_uri:
                raise ValueError(
                    "If PERFORMING_PROFESSIONAL_BODY_REG_CODE is given, \
                        PERFORMING_PROFESSIONAL_BODY_REG_URI must also be given"
                )

            return performing_professional_body_reg_code

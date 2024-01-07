"""Immunization FHIR R4B validator"""
from fhir.resources.R4B.immunization import Immunization
from models.utils import (
    get_generic_questionnaire_response_value,
    get_generic_extension_value,
)
from models.immunization_pre_validators import (
    ImmunizationPreValidators,
)


class ImmunizationValidator:
    """
    Validate the FHIR Immunization model against the NHS specific validators and Immunization
    FHIR profile
    """

    def __init__(self) -> None:
        pass

    @classmethod
    def pre_validate_patient_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if  patient -> identifier -> value (NHS number) exists,
        then it is a string of 10 characters
        """
        try:
            patient_identifier_value = values["patient"]["identifier"]["value"]
            ImmunizationPreValidators.patient_identifier_value(patient_identifier_value)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_occurrence_date_time(cls, values: dict) -> dict:
        """
        Pre-validate that, if occurrenceDateTime exists (date_and_time), then it is a string in the
        format "YYYY-MM-DDThh:mm:ss+zz:zz" or "YYYY-MM-DDThh:mm:ss-zz:zz" (i.e. date and time,
        including timezone offset in hours and minutes), representing a valid datetime

        NOTE: occurrenceDateTime is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """
        try:
            occurrence_date_time = values["occurrenceDateTime"]
            ImmunizationPreValidators.occurrence_date_time(occurrence_date_time)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_contained(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained exists, then it is a list of length 1
        """
        try:
            contained = values["contained"]
            ImmunizationPreValidators.contained(contained)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_questionnaire_answers(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each contained[0] -> resourceType[QuestionnaireResponse]:
        item[*] -> linkId[*]: answer is a list of length 1
        """

        try:
            for item in values["contained"][0]["item"]:
                try:
                    answer = item["answer"]
                    ImmunizationPreValidators.questionnaire_answer(answer)
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_questionnaire_site_code_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[0] -> resourceType[QuestionnaireResponse]:
        item[*] -> linkId[SiteCode]: answer[0] -> valueCoding -> code (site_code) exists,
        then it is a non-empty string
        """
        try:
            questionnaire_site_code_code = get_generic_questionnaire_response_value(
                values, "SiteCode", "code"
            )
            ImmunizationPreValidators.questionnaire_site_code_code(
                questionnaire_site_code_code
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_site_name_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[0] -> resourceType[QuestionnaireResponse]:
        item[*] -> linkId[SiteName]: answer[0] -> valueCoding -> code (site_name) exists,
        then it is a non-empty string
        """
        try:
            questionnaire_site_name_code = get_generic_questionnaire_response_value(
                values, "SiteName", "code"
            )
            ImmunizationPreValidators.questionnaire_site_name_code(
                questionnaire_site_name_code
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier exists, then it is a list of length 1
        """
        try:
            identifier = values["identifier"]
            ImmunizationPreValidators.identifier(identifier)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0] -> value (unique_id) exists,
        then it is a non-empty string
        """
        try:
            identifier_value = values["identifier"][0]["value"]
            ImmunizationPreValidators.identifier_value(identifier_value)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0] -> system (unique_id_uri) exists,
        then it is a non-empty string
        """
        try:
            identifier_system = values["identifier"][0]["system"]
            ImmunizationPreValidators.identifier_system(identifier_system)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_status(cls, values: dict) -> dict:
        """
        Pre-validate that, if status (action_flag or not_given) exists, then it is a non-empty
        string which is one of the following: completed, entered-in-error, not-done.

        NOTE 1: action_flag and not_given are mutually exclusive i.e. if action_flag is present then
        not_given will be absent and vice versa. The action_flags are 'completed' and 'not-done'.
        The following 1-to-1 mapping applies:
        * not_given is True <---> Status will be set to 'not-done' (and therefore action_flag is
            absent)
        * not_given is False <---> Status will be set to 'completed' or 'entered-in-error' (and
            therefore action_flag is present)

        NOTE 2: Status is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """

        try:
            status = values["status"]
            ImmunizationPreValidators.status(status)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_recorded(cls, values: dict) -> dict:
        """
        Pre-validate that, if recorded (recorded_date) exists, then it is a string in the format
        YYYY-MM-DD, representing a valid date
        """

        try:
            recorded = values["recorded"]
            ImmunizationPreValidators.recorded(recorded)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_primary_source(cls, values: dict) -> dict:
        """Pre-validate that, if primarySource (primary_source) exists, then it is a boolean"""

        try:
            primary_source = values["primarySource"]
            ImmunizationPreValidators.primary_source(primary_source)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_report_origin_text(cls, values: dict) -> dict:
        """
        Pre-validate that, if reportOrigin -> text (report_origin_text)
        exists, then it is a non-empty string with maximum length 100 characters
        """

        try:
            report_origin_text = values["reportOrigin"]["text"]

            ImmunizationPreValidators.report_origin_text(report_origin_text)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_extension_value_codeable_concept_codings(
        cls, values: dict
    ) -> dict:
        """
        Pre-validate that, if they exist, each extension[*] -> valueCodeableConcept -> coding
        is a list of length 1
        """

        try:
            for item in values["extension"]:
                try:
                    coding = item["valueCodeableConcept"]["coding"]
                    ImmunizationPreValidators.extension_value_codeable_concept_coding(
                        coding
                    )
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccination_procedure_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[*] ->
        url[https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure]:
        valueCodeableConcept -> coding -> code (vaccination_procedure_code) exists,
        then it is a non-empty string
        """
        try:
            vaccination_procedure_code = get_generic_extension_value(
                values,
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "code",
            )
            ImmunizationPreValidators.vaccination_procedure_code(
                vaccination_procedure_code
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccination_procedure_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[*] ->
        url[https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure]:
        valueCodeableConcept -> coding -> display (vaccination_procedure_term) exists,
        then it is a non-empty string
        """
        try:
            vaccination_procedure_display = get_generic_extension_value(
                values,
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "display",
            )
            ImmunizationPreValidators.vaccination_procedure_display(
                vaccination_procedure_display
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccination_situation_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[*] ->
        url[https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation]:
        valueCodeableConcept -> coding -> code (vaccination_situation_code) exists,
        then it is a non-empty string
        """
        try:
            vaccination_situation_code = get_generic_extension_value(
                values,
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
                "code",
            )
            ImmunizationPreValidators.vaccination_situation_code(
                vaccination_situation_code
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccination_situation_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[*] ->
        url[https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation]:
        valueCodeableConcept -> coding -> display (vaccination_situation_term) exists,
        then it is a non-empty string
        """
        try:
            vaccination_situation_display = get_generic_extension_value(
                values,
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
                "display",
            )
            ImmunizationPreValidators.vaccination_situation_display(
                vaccination_situation_display
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_status_reason_coding(cls, values: dict) -> dict:
        """
        Pre-validate that, if statusReason -> coding (reason_not_given_code) exists, then it is a
        list of length 1
        """
        try:
            coding = values["statusReason"]["coding"]
            ImmunizationPreValidators.status_reason_coding(coding)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_status_reason_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if statusReason -> coding[0] -> code (reason_not_given_code) exists,
        then it is a non-empty string
        """
        try:
            status_reason_coding_code = values["statusReason"]["coding"][0]["code"]
            ImmunizationPreValidators.status_reason_coding_code(
                status_reason_coding_code
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_status_reason_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if statusReason -> coding[0] -> display (reason_not_given_term) exists,
        then it is a non-empty string
        """
        try:
            status_reason_coding_display = values["statusReason"]["coding"][0][
                "display"
            ]
            ImmunizationPreValidators.status_reason_coding_display(
                status_reason_coding_display
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_protocol_applied(cls, values: dict) -> dict:
        """Pre-validate that, if protocolApplied exists, then it is a list of length 1"""
        try:
            protocol_applied = values["protocolApplied"]
            ImmunizationPreValidators.protocol_applied(protocol_applied)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_protocol_applied_dose_number_positive_int(
        cls, values: dict
    ) -> dict:
        """
        Pre-validate that, if protocolApplied[0] -> doseNumberPositiveInt (dose_sequence) exists,
        then it is an integer from 1 to 9
        """
        try:
            protocol_applied_dose_number_positive_int = values["protocolApplied"][0][
                "doseNumberPositiveInt"
            ]
            ImmunizationPreValidators.protocol_applied_dose_number_positive_int(
                protocol_applied_dose_number_positive_int
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccine_code_coding(cls, values: dict) -> dict:
        """Pre-validate that, if vaccineCode -> coding exists, then it is a list of length 1"""
        try:
            vaccine_code_coding = values["vaccineCode"]["coding"]
            ImmunizationPreValidators.vaccine_code_coding(vaccine_code_coding)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccine_code_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if vaccineCode -> coding[0] -> code (vaccine_product_code) exists,
        then it is a non-empty string
        """
        try:
            vaccine_code_coding_code = values["vaccineCode"]["coding"][0]["code"]
            ImmunizationPreValidators.vaccine_code_coding_code(vaccine_code_coding_code)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccine_code_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if vaccineCode -> coding[0] -> display (vaccine_product_term) exists,
        then it is a non-empty string
        """
        try:
            vaccine_code_coding_display = values["vaccineCode"]["coding"][0]["display"]
            ImmunizationPreValidators.vaccine_code_coding_display(
                vaccine_code_coding_display
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_manufacturer_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if manufacturer -> display (vaccine_manufacturer) exists,
        then it is a non-empty string
        """
        try:
            manufacturer_display = values["manufacturer"]["display"]
            ImmunizationPreValidators.manufacturer_display(manufacturer_display)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_lot_number(cls, values: dict) -> dict:
        """
        Pre-validate that, if lotNumber (batch_number) exists,
        then it is a non-empty string
        """
        try:
            lot_number = values["lotNumber"]
            ImmunizationPreValidators.lot_number(lot_number)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_expiration_date(cls, values: dict) -> dict:
        """
        Pre-validate that, if expirationDate (expiry_date) exists, then it is a string in the format
        YYYY-MM-DD, representing a valid date
        """
        try:
            expiration_date = values["expirationDate"]
            ImmunizationPreValidators.expiration_date(expiration_date)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_site_coding(cls, values: dict) -> dict:
        """Pre-validate that, if site -> coding exists, then it is a list of length 1"""
        try:
            site_coding = values["site"]["coding"]
            ImmunizationPreValidators.site_coding(site_coding)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_site_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if site -> coding[0] -> code (site_of_vaccination_code) exists,
        then it is a non-empty string
        """
        try:
            site_coding_code = values["site"]["coding"][0]["code"]
            ImmunizationPreValidators.site_coding_code(site_coding_code)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_site_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if site -> coding[0] -> display (site_of_vaccination_term) exists,
        then it is a non-empty string
        """
        try:
            site_coding_display = values["site"]["coding"][0]["display"]
            ImmunizationPreValidators.site_coding_display(site_coding_display)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_route_coding(cls, values: dict) -> dict:
        """Pre-validate that, if route -> coding exists, then it is a list of length 1"""
        try:
            route_coding = values["route"]["coding"]
            ImmunizationPreValidators.route_coding(route_coding)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_route_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if route -> coding[0] -> code (route_of_vaccination_code) exists,
        then it is a non-empty string
        """
        try:
            route_coding_code = values["route"]["coding"][0]["code"]
            ImmunizationPreValidators.route_coding_code(route_coding_code)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_route_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if route -> coding[0] -> display (route_of_vaccination_term) exists,
        then it is a non-empty string
        """
        try:
            route_coding_display = values["route"]["coding"][0]["display"]
            ImmunizationPreValidators.route_coding_display(route_coding_display)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_dose_quantity_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity -> value (dose_amount) exists,
        then it is a number representing an integer or decimal with
        maximum four decimal places

        NOTE: This validator will only work if the raw json data is parsed with the
        parse_float argument set to equal Decimal type (Decimal must be imported from decimal).
        Floats (but not integers) will then be parsed as Decimals.
        e.g json.loads(raw_data, parse_float=Decimal)
        """
        try:
            dose_quantity_value = values["doseQuantity"]["value"]
            ImmunizationPreValidators.dose_quantity_value(dose_quantity_value)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_dose_quantity_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity -> code (dose_unit_code) exists,
        then it is a non-empty string
        """
        try:
            dose_quantity_code = values["doseQuantity"]["code"]
            ImmunizationPreValidators.dose_quantity_code(dose_quantity_code)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_dose_quantity_unit(cls, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity -> unit (dose_unit_term) exists,
        then it is a non-empty string
        """
        try:
            dose_quantity_unit = values["doseQuantity"]["unit"]
            ImmunizationPreValidators.dose_quantity_unit(dose_quantity_unit)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reason_code_codings(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[*] -> coding is a list of length 1
        """

        try:
            for item in values["reasonCode"]:
                try:
                    coding = item["coding"]
                    ImmunizationPreValidators.reason_code_coding(coding)
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reason_code_coding_codes(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[*] -> coding -> code (indication_code)
        is a non-empty string
        """

        try:
            for item in values["reasonCode"]:
                try:
                    coding = item["coding"][0]["code"]
                    ImmunizationPreValidators.reason_code_coding_code(coding)
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reason_code_coding_displays(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[*] -> coding -> display (indication_term)
        is a non-empty string
        """

        try:
            for item in values["reasonCode"]:
                try:
                    coding = item["coding"][0]["display"]
                    ImmunizationPreValidators.reason_code_coding_display(coding)
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    def add_custom_root_validators(self):
        """
        Add custom NHS validators to the model

        NOTE: THE ORDER IN WHICH THE VALIDATORS ARE ADDED IS IMPORTANT! DO NOT CHANGE THE ORDER
        WITHOUT UNDERSTANDING THE IMPACT ON OTHER VALIDATORS IN THE LIST.
        """
        # DO NOT CHANGE THE ORDER WITHOUT UNDERSTANDING THE IMPACT ON OTHER VALIDATORS IN THE LIST
        Immunization.add_root_validator(
            self.pre_validate_patient_identifier_value, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_occurrence_date_time, pre=True
        )
        Immunization.add_root_validator(self.pre_validate_contained, pre=True)
        Immunization.add_root_validator(
            self.pre_validate_questionnaire_answers, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_questionnaire_site_code_code, pre=True
        )
        Immunization.add_root_validator(self.pre_validate_site_name_code, pre=True)
        Immunization.add_root_validator(self.pre_validate_identifier, pre=True)
        Immunization.add_root_validator(self.pre_validate_identifier_value, pre=True)
        Immunization.add_root_validator(self.pre_validate_identifier_system, pre=True)
        Immunization.add_root_validator(self.pre_validate_status, pre=True)
        Immunization.add_root_validator(self.pre_validate_recorded, pre=True)
        Immunization.add_root_validator(self.pre_validate_primary_source, pre=True)
        Immunization.add_root_validator(self.pre_validate_report_origin_text, pre=True)
        Immunization.add_root_validator(
            self.pre_validate_extension_value_codeable_concept_codings, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_vaccination_procedure_code, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_vaccination_procedure_display, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_vaccination_situation_code, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_vaccination_situation_display, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_status_reason_coding, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_status_reason_coding_code, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_status_reason_coding_display, pre=True
        )
        Immunization.add_root_validator(self.pre_validate_protocol_applied, pre=True)
        Immunization.add_root_validator(
            self.pre_validate_protocol_applied_dose_number_positive_int, pre=True
        )
        Immunization.add_root_validator(self.pre_validate_vaccine_code_coding, pre=True)
        Immunization.add_root_validator(
            self.pre_validate_vaccine_code_coding_code, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_vaccine_code_coding_display, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_manufacturer_display, pre=True
        )
        Immunization.add_root_validator(self.pre_validate_lot_number, pre=True)
        Immunization.add_root_validator(self.pre_validate_expiration_date, pre=True)
        Immunization.add_root_validator(self.pre_validate_site_coding, pre=True)
        Immunization.add_root_validator(self.pre_validate_site_coding_code, pre=True)
        Immunization.add_root_validator(self.pre_validate_site_coding_display, pre=True)
        Immunization.add_root_validator(self.pre_validate_route_coding, pre=True)
        Immunization.add_root_validator(self.pre_validate_route_coding_code, pre=True)
        Immunization.add_root_validator(
            self.pre_validate_route_coding_display, pre=True
        )
        Immunization.add_root_validator(self.pre_validate_dose_quantity_value, pre=True)
        Immunization.add_root_validator(self.pre_validate_dose_quantity_code, pre=True)
        Immunization.add_root_validator(self.pre_validate_dose_quantity_unit, pre=True)
        Immunization.add_root_validator(self.pre_validate_reason_code_codings, pre=True)
        Immunization.add_root_validator(
            self.pre_validate_reason_code_coding_codes, pre=True
        )
        Immunization.add_root_validator(
            self.pre_validate_reason_code_coding_displays, pre=True
        )

    def validate(self, json_data) -> Immunization:
        """Generate the Immunization model"""
        immunization = Immunization.parse_obj(json_data)
        return immunization

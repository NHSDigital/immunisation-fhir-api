"""Functions for obtaining a field value from the FHIR immunization resource json data"""

from models.utils.generic_utils import (
    get_contained_patient,
    get_contained_practitioner,
    is_organization,
    get_generic_extension_value,
)
from constants import Urls


class ObtainFieldValue:
    """Functions for obtaining a field value from the FHIR immunization resource json data"""

    def __init__(self) -> None:
        pass

    @staticmethod
    def target_disease(imms: dict):
        return imms["protocolApplied"][0]["targetDisease"]

    @staticmethod
    def occurrence_date_time(imms: dict):
        """Obtains occurrence_date_time value"""
        return imms["occurrenceDateTime"]

    @staticmethod
    def patient_identifier_value(imms: dict):
        """Obtains patient_identifier_value value"""
        contained_patient = get_contained_patient(imms)
        contained_patient_identifier = [
            x for x in contained_patient.get("identifier") if x.get("system") == Urls.nhs_number
        ][0]
        return contained_patient_identifier["value"]

    @staticmethod
    def patient_name_given(imms: dict):
        """Obtains patient_name_given value"""
        return get_contained_patient(imms)["name"][0]["given"]

    @staticmethod
    def patient_name_family(imms: dict):
        """Obtains patient_name_family value"""
        return get_contained_patient(imms)["name"][0]["family"]

    @staticmethod
    def patient_birth_date(imms: dict):
        """Obtains patient_birth_date value"""
        return get_contained_patient(imms)["birthDate"]

    @staticmethod
    def patient_gender(imms: dict):
        """Obtains patient_gender value"""
        return get_contained_patient(imms)["gender"]

    @staticmethod
    def patient_address_postal_code(imms: dict):
        """Obtains patient_address_postal_code value"""
        return get_contained_patient(imms)["address"][0]["postalCode"]

    @staticmethod
    def organization_identifier_value(imms: dict):
        """Obtains organization_identifier_value value"""
        return [x for x in imms.get("performer") if is_organization(x)][0]["actor"]["identifier"]["value"]

    @staticmethod
    def organization_display(imms: dict):
        """Obtains organization_display value"""
        return [x for x in imms.get("performer") if is_organization(x)][0]["actor"]["display"]

    @staticmethod
    def identifier_value(imms: dict):
        """Obtains identifier_value value"""
        return imms["identifier"][0]["value"]

    @staticmethod
    def identifier_system(imms: dict):
        """Obtains identifier_system value"""
        return imms["identifier"][0]["system"]

    @staticmethod
    def practitioner_name_given(imms: dict):
        """Obtains practitioner_name_given value"""
        return get_contained_practitioner(imms)["name"][0]["given"]

    @staticmethod
    def practitioner_name_family(imms: dict):
        """Obtains practitioner_name_family value"""
        return get_contained_practitioner(imms)["name"][0]["family"]

    @staticmethod
    def practitioner_identifier_value(imms: dict):
        """Obtains practitioner_identifier_value value"""
        return get_contained_practitioner(imms)["identifier"][0]["value"]

    @staticmethod
    def practitioner_identifier_system(imms: dict):
        """Obtains practitioner_identifier_system value"""
        return get_contained_practitioner(imms)["identifier"][0]["system"]

    @staticmethod
    def recorded(imms: dict):
        """Obtains recorded value"""
        return imms["recorded"]

    @staticmethod
    def primary_source(imms: dict):
        """Obtains primary_source value"""
        return imms["primarySource"]

    @staticmethod
    def report_origin_text(imms: dict):
        """Obtains report_origin_text value"""
        return imms["reportOrigin"]["text"]

    @staticmethod
    def vaccination_procedure_code(imms: dict):
        """Obtains vaccination_procedure_code value"""
        return get_generic_extension_value(imms, Urls.vaccination_procedure, Urls.snomed, "code")

    @staticmethod
    def vaccination_procedure_display(imms: dict):
        """Obtains vaccination_procedure_display value"""
        return get_generic_extension_value(imms, Urls.vaccination_procedure, Urls.snomed, "display")

    @staticmethod
    def dose_number_positive_int(imms: dict):
        """Obtains dose_number_positive_int value"""
        return imms["protocolApplied"][0]["doseNumberPositiveInt"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def vaccine_code_coding_code(imms: dict):
    #     """Obtains vaccine_code_coding_code value"""
    #     return [x for x in imms["vaccineCode"]["coding"] if x.get("system") == Urls.snomed][0]["code"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def vaccine_code_coding_display(imms: dict):
    #     """Obtains vaccine_code_coding_display value"""
    #     return [x for x in imms["vaccineCode"]["coding"] if x.get("system") == Urls.snomed][0]["display"]

    @staticmethod
    def manufacturer_display(imms: dict):
        """Obtains manufacturer_display value"""
        return imms["manufacturer"]["display"]

    @staticmethod
    def lot_number(imms: dict):
        """Obtains lot_number value"""
        return imms["lotNumber"]

    @staticmethod
    def expiration_date(imms: dict):
        """Obtains expiration_date value"""
        return imms["expirationDate"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def site_coding_code(imms: dict):
    #     """Obtains site_coding_code value"""
    #     return [x for x in imms["site"]["coding"] if x.get("system") == Urls.snomed][0]["code"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def site_coding_display(imms: dict):
    #     """Obtains site_coding_display value"""
    #     return [x for x in imms["site"]["coding"] if x.get("system") == Urls.snomed][0]["display"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def route_coding_code(imms: dict):
    #     """Obtains route_coding_code value"""
    #     return [x for x in imms["route"]["coding"] if x.get("system") == Urls.snomed][0]["code"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def route_coding_display(imms: dict):
    #     """Obtains route_coding_display value"""
    #     return [x for x in imms["route"]["coding"] if x.get("system") == Urls.snomed][0]["display"]

    @staticmethod
    def dose_quantity_value(imms: dict):
        """Obtains dose_quantity_value value"""
        return imms["doseQuantity"]["value"]

    @staticmethod
    def dose_quantity_code(imms: dict):
        """Obtains dose_quantity_code value"""
        return imms["doseQuantity"]["code"]

    @staticmethod
    def dose_quantity_unit(imms: dict):
        """Obtains dose_quantity_unit value"""
        return imms["doseQuantity"]["unit"]

    @staticmethod
    def organization_identifier_system(imms: dict):
        """Obtains organization_identifier_system value"""
        return [x for x in imms.get("performer") if is_organization(x)][0]["actor"]["identifier"]["system"]

    @staticmethod
    def location_identifier_value(imms: dict):
        """Obtains location_identifier_value value"""
        return imms["location"]["identifier"]["value"]

    @staticmethod
    def location_identifier_system(imms: dict):
        """Obtains location_identifier_system value"""
        return imms["location"]["identifier"]["system"]

    # NOTE: THIS METHOD IS COMMENTED OUT AS IT IS for A REQUIRED ELEMENT (VALIDATION SHOULD ALWAYS PASS),
    # AND THE MEANS TO ACCESS THE VALUE HAS NOT BEEN CONFIRMED. DO NOT DELETE THE METHOD, IT MAY NEED REINSTATED LATER.
    # @staticmethod
    # def reason_code_coding_code(imms: dict, index: int):
    #     """Obtains reason_code_coding_code value"""
    #     return imms["reasonCode"][index]["coding"][0]["code"]

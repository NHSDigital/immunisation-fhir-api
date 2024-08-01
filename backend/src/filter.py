"""Functions for filtering a FHIR Immunization Resource"""

from models.utils.generic_utils import is_actor_referencing_contained_resource, get_contained_practitioner
from constants import Urls


def remove_reference_to_contained_practitioner(imms: dict) -> dict:
    """Remove the reference to a contained patient resource from the performer field (if such a reference exists)"""
    # Obtain contained_practitioner (if it exists)
    try:
        contained_practitioner = get_contained_practitioner(imms)
    except (KeyError, IndexError, AttributeError):
        return imms

    # Remove reference to the contained practitioner from imms[performer]
    imms["performer"] = [
        x for x in imms["performer"] if not is_actor_referencing_contained_resource(x, contained_practitioner["id"])
    ]

    return imms


def create_reference_to_patient_resource(patient_full_url: str, patient: dict) -> dict:
    """
    Returns a reference to the given patient which includes the patient nhs number identifier (system and value fields
    only) and a reference to patient full url. "Type" field is set to "Patient".
    """
    patient_nhs_number_identifier = [x for x in patient["identifier"] if x.get("system") == Urls.nhs_number][0]

    return {
        "reference": patient_full_url,
        "type": "Patient",
        "identifier": {
            "system": patient_nhs_number_identifier["system"],
            "value": patient_nhs_number_identifier["value"],
        },
    }


def replace_address_postal_codes(imms: dict) -> dict:
    """Replace any postal codes found in contained patient address with 'ZZ99 3CZ'"""
    for resource in imms.get("contained", [{}]):
        if resource.get("resourceType") == "Patient":
            for address in resource.get("address", [{}]):
                if address.get("postalCode") is not None:
                    address["postalCode"] = "ZZ99 3CZ"

    return imms


def replace_organization_values(imms: dict) -> dict:
    """
    Replace organization_identifier_values with N2N9I, organization_identifier_systems with
    https://fhir.nhs.uk/Id/ods-organization-code, and remove any organization_displays
    """
    for performer in imms.get("performer", [{}]):
        if performer.get("actor", {}).get("type") == "Organization":

            if performer["actor"].get("identifier", {}).get("value") is not None:
                performer["actor"]["identifier"]["value"] = "N2N9I"
                performer["actor"]["identifier"]["system"] = Urls.ods_organization_code

            elif performer["actor"].get("identifier", {}).get("system") is not None:
                performer["actor"]["identifier"]["system"] = Urls.ods_organization_code

            if performer["actor"].get("display") is not None:
                del performer["actor"]["display"]

    return imms


def add_use_to_identifier(imms: dict) -> dict:
    """
    Add use of "offical" to immunisation identifier if no use currently specified
    (if use is currently specified it is left as it is i.e. it doesn't get overwritten)
    """
    if "use" not in imms["identifier"][0]:
        imms["identifier"][0]["use"] = "official"
    return imms


class Filter:
    """Functions for filtering a FHIR Immunization Resource"""

    @staticmethod
    def read(imms: dict) -> dict:
        """Apply filtering for READ request"""
        imms.pop("identifier")
        return imms

    @staticmethod
    def search(imms: dict, patient_full_url: str, bundle_patient: dict = None) -> dict:
        """Apply filtering for an individual FHIR Immunization Resource as part of SEARCH request"""
        imms = remove_reference_to_contained_practitioner(imms)
        imms.pop("contained")
        imms["patient"] = create_reference_to_patient_resource(patient_full_url, bundle_patient)
        imms = add_use_to_identifier(imms)
        # Location identifier system and value are to be overwritten
        # (for backwards compatibility with Immunisation History API, as agreed with VDS team)
        imms["location"] = {"identifier": {"system": "urn:iso:std:iso:3166", "value": "GB"}}
        return imms

    @staticmethod
    def s_flag(imms: dict) -> dict:
        """Apply filtering for patients with 'RESTRICTED' flag"""
        imms = replace_address_postal_codes(imms)
        imms = replace_organization_values(imms)
        if imms.get("location"):
            imms["location"] = {"identifier": {"system": "urn:iso:std:iso:3166", "value": "GB"}}
        return imms

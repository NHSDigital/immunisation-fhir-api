"FHIR Immunization Pre Validators"

from models.constants import Constants
from models.utils.generic_utils import get_generic_extension_value, generate_field_location_for_extension
from models.utils.pre_validator_utils import PreValidation
from constants import Urls
import re


class PreValidators:
    """
    Validators which run prior to the FHIR validators and check that, where values exist, they
    meet the NHS custom requirements. Note that validation of the existence of a value (i.e. it
    exists if mandatory, or doesn't exist if is not applicable) is done by the post validators.
    """

    def __init__(self, immunization: dict):
        self.immunization = immunization
        self.errors = []

    def validate(self):
        """Run all pre-validation checks."""
        validation_methods = [
            self.pre_validate_contained_contents,
            self.pre_validate_patient_reference,
            self.pre_validate_patient_identifier,
            self.pre_validate_patient_identifier_value,
            self.pre_validate_patient_name,
            self.pre_validate_patient_name_given,
            self.pre_validate_patient_name_family,
            self.pre_validate_patient_birth_date,
            self.pre_validate_patient_gender,
            self.pre_validate_patient_address,
            self.pre_validate_patient_address_postal_code,
            self.pre_validate_occurrence_date_time,
            self.pre_validate_performer_actor_type,
            self.pre_validate_performer_actor_reference,
            self.pre_validate_organization_identifier_value,
            self.pre_validate_identifier,
            self.pre_validate_identifier_value,
            self.pre_validate_identifier_system,
            self.pre_validate_status,
            self.pre_validate_practitioner_name,
            self.pre_validate_practitioner_name_given,
            self.pre_validate_practitioner_name_family,
            self.pre_validate_recorded,
            self.pre_validate_primary_source,
            self.pre_validate_extension_urls,
            self.pre_validate_extension_value_codeable_concept_codings,
            self.pre_validate_vaccination_procedure_code,
            self.pre_validate_vaccination_procedure_display,
            self.pre_validate_vaccination_situation_code,
            self.pre_validate_vaccination_situation_display,
            self.pre_validate_protocol_applied,
            self.pre_validate_dose_number_positive_int,
            self.pre_validate_dose_number_string,
            self.pre_validate_target_disease,
            self.pre_validate_target_disease_codings,
            self.pre_validate_disease_type_coding_codes,
            self.pre_validate_vaccine_code_coding,
            self.pre_validate_vaccine_code_coding_code,
            self.pre_validate_vaccine_code_coding_display,
            self.pre_validate_manufacturer_display,
            self.pre_validate_lot_number,
            self.pre_validate_expiration_date,
            self.pre_validate_site_coding,
            self.pre_validate_site_coding_code,
            self.pre_validate_site_coding_display,
            self.pre_validate_route_coding,
            self.pre_validate_route_coding_code,
            self.pre_validate_route_coding_display,
            self.pre_validate_dose_quantity_value,
            self.pre_validate_dose_quantity_code,
            self.pre_validate_dose_quantity_unit,
            self.pre_validate_reason_code_codings,
            self.pre_validate_reason_code_coding_codes,
            self.pre_validate_organization_identifier_system,
            self.pre_validate_location_identifier_value,
            self.pre_validate_location_identifier_system,
            self.pre_validate_location_type,
        ]

        for method in validation_methods:
            try:
                method(self.immunization)
            except (ValueError, TypeError, IndexError, AttributeError) as e:
                self.errors.append(str(e))

        if self.errors:
            all_errors = "; ".join(self.errors)
            raise ValueError(f"Validation errors: {all_errors}")

    def pre_validate_contained_contents(self, values: dict) -> dict:
        """
        Pre-validate that there is exactly one patient resource in contained, a maximum of one practitioner resource,
        and no other resources
        """
        contained = values["contained"]

        # Contained must be a non-empty list of non-empty dictionaries
        PreValidation.for_list(contained, "contained", elements_are_dicts=True)

        # Every element of contained must have a resourceType key
        if [x for x in contained if x.get("resourceType") is None]:
            raise ValueError("contained resources must have 'resourceType' key")

        # Count number of each resource type in contained
        patient_count = sum(1 for x in contained if x["resourceType"] == "Patient")
        practitioner_count = sum(1 for x in contained if x["resourceType"] == "Practitioner")
        other_resource_count = sum(1 for x in contained if x["resourceType"] not in ("Patient", "Practitioner"))

        # Validate counts
        errors = []
        if other_resource_count != 0:
            errors.append("contained must contain only Patient and Practitioner resources")
        if patient_count != 1:
            errors.append("contained must contain exactly one Patient resource")
        if practitioner_count > 1:
            errors.append("contained must contain a maximum of one Practitioner resource")

        # Raise errors
        if errors:
            raise ValueError("; ".join(errors))

    def pre_validate_patient_reference(self, values: dict) -> dict:
        """
        Pre-validate that:
        - patient.reference exists and it is a reference
        - patient.reference matches the contained patient resource id
        - contained Patient resource has an id
        """

        # Obtain the patient.reference
        patient_reference = values.get("patient", {}).get("reference")

        # Make sure we have an internal reference (starts with #)
        if not (isinstance(patient_reference, str) and patient_reference.startswith("#")):
            raise ValueError("patient.reference must be a single reference to a contained Patient resource")

        # Obtain the contained patient resource
        contained_patient = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]

        try:
            # Try to obtain the contained patient resource id
            contained_patient_id = contained_patient["id"]

            # If the reference is not equal to the ID then raise an error
            if ("#" + contained_patient_id) != patient_reference:
                raise ValueError(
                    f"The reference '{patient_reference}' does not exist in the contained Patient resource"
                )
        except KeyError as error:
            # If the contained Patient resource has no id raise an error
            raise ValueError("The contained Patient resource must have an 'id' field") from error

    def pre_validate_patient_identifier(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].identifier exists, then it is a list of length 1
        """
        field_location = "contained[?(@.resourceType=='Patient')].identifier"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            PreValidation.for_list(field_value, field_location, defined_length=1)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_identifier_value(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].identifier[0].value (
        legacy CSV field name: NHS_NUMBER) exists, then it is a string of 10 characters
        which does not contain spaces
        """
        field_location = "contained[?(@.resourceType=='Patient')].identifier[0].value"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"][0][
                "value"
            ]
            PreValidation.for_string(field_value, field_location, defined_length=10, spaces_allowed=False)
            PreValidation.for_nhs_number(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_name(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].name exists, then it is an array of length 1
        """
        field_location = "contained[?(@.resourceType=='Patient')].name"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["name"]
            PreValidation.for_list(field_value, field_location, defined_length=1)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_name_given(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].name[0].given (legacy CSV field name:
        PERSON_FORENAME) exists, then it is a an array containing a single non-empty string
        """
        field_location = "contained[?(@.resourceType=='Patient')].name[0].given"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["name"][0]["given"]
            PreValidation.for_list(field_value, field_location, defined_length=1, elements_are_strings=True)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_name_family(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].name[0].family (legacy CSV field name:
        PERSON_SURNAME) exists, then it is a an array containing a single non-empty string
        """
        field_location = "contained[?(@.resourceType=='Patient')].name[0].family"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["name"][0]["family"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_birth_date(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].birthDate (legacy CSV field name: PERSON_DOB)
        exists, then it is a string in the format YYYY-MM-DD, representing a valid date
        """
        field_location = "contained[?(@.resourceType=='Patient')].birthDate"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["birthDate"]
            PreValidation.for_date(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_gender(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].gender (legacy CSV field name: PERSON_GENDER_CODE)
        exists, then it is a string, which is one of the following: male, female, other, unknown
        """
        field_location = "contained[?(@.resourceType=='Patient')].gender"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["gender"]
            PreValidation.for_string(field_value, field_location, predefined_values=Constants.GENDERS)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_address(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].address exists, then it is an array of length 1
        """
        field_location = "contained[?(@.resourceType=='Patient')].address"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["address"]
            PreValidation.for_list(field_value, field_location, defined_length=1)
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_address_postal_code(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].address[0].postalCode (legacy CSV field name:
        PERSON_POSTCODE) exists, then it is a non-empty string, separated into two parts by a single space
        """
        field_location = "contained[?(@.resourceType=='Patient')].address[0].postalCode"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["address"][0][
                "postalCode"
            ]
            PreValidation.for_string(field_value, field_location, is_postal_code=True)
        except (KeyError, IndexError):
            pass

    def pre_validate_occurrence_date_time(self, values: dict) -> dict:
        """
        Pre-validate that, if occurrenceDateTime exists (legacy CSV field name: DATE_AND_TIME),
        then it is a string in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or "YYYY-MM-DDThh:mm:ss-zz:zz"
        (i.e. date and time, including timezone offset in hours and minutes), representing a valid
        datetime. Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).

        NOTE: occurrenceDateTime is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """
        field_location = "occurrenceDateTime"
        try:
            field_value = values["occurrenceDateTime"]
            PreValidation.for_date_time(field_value, field_location)
        except KeyError:
            pass

    def pre_validate_performer_actor_type(self, values: dict) -> dict:
        """
        Pre-validate that, if performer.actor.organisation exists, then there is only one such
        key with the value of "Organization"
        """
        try:
            found = []
            for item in values["performer"]:
                if item.get("actor").get("type") == "Organization" and item.get("actor").get("type") in found:
                    raise ValueError("performer.actor[?@.type=='Organization'] must be unique")

                found.append(item.get("actor").get("type"))

        except (KeyError, AttributeError):
            pass

    def pre_validate_performer_actor_reference(self, values: dict) -> dict:
        """
        Pre-validate that:
        - if performer.actor.reference exists then it is a single reference
        - if there is no contained Practitioner resource, then there is no performer.actor.reference
        - if there is a contained Practitioner resource, then there is a performer.actor.reference
        - if there is a contained Practitioner resource, then it has an id
        - If there is a contained Practitioner resource, then the performer.actor.reference is equal
          to the ID
        """

        # Obtain the performer.actor.references that are internal references (#)
        performer_actor_internal_references = []
        for item in values.get("performer", []):
            reference = item.get("actor", {}).get("reference")
            if isinstance(reference, str) and reference.startswith("#"):
                performer_actor_internal_references.append(reference)

        # Check that we have a maximum of 1 internal reference
        if len(performer_actor_internal_references) > 1:
            raise ValueError(
                "performer.actor.reference must be a single reference to a contained Practitioner resource. "
                + f"References found: {performer_actor_internal_references}"
            )

        # Obtain the contained practitioner resource
        try:
            contained_practitioner = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]

            try:
                # Try to obtain the contained practitioner resource id
                contained_practitioner_id = contained_practitioner["id"]

                # If there is a contained practitioner resource, but no reference raise an error
                if len(performer_actor_internal_references) == 0:
                    raise ValueError("contained Practitioner ID must be referenced by performer.actor.reference")

                # If the reference is not equal to the ID then raise an error
                if ("#" + contained_practitioner_id) != performer_actor_internal_references[0]:
                    raise ValueError(
                        f"The reference '{performer_actor_internal_references[0]}' does "
                        + "not exist in the contained Practitioner resources"
                    )
            except KeyError as error:
                # If the contained practitioner resource has no id raise an error
                raise ValueError("The contained Practitioner resource must have an 'id' field") from error

        except (IndexError, KeyError) as error:
            # Entering this exception block implies that there is no contained practitioner resource
            # therefore if there is a reference then raise an error
            if len(performer_actor_internal_references) != 0:
                raise ValueError(
                    f"The reference(s) {performer_actor_internal_references} do "
                    + "not exist in the contained Practitioner resources"
                ) from error

    def pre_validate_organization_identifier_value(self, values: dict) -> dict:
        """
        Pre-validate that, if performer[?(@.actor.type=='Organization').identifier.value]
        (legacy CSV field name: SITE_CODE) exists, then it is a non-empty string.
        Also pre-validate it is in format alpha-numeric-alpha-numeric-alpha (e.g. "B0C4P").
        """
        field_location = "performer[?(@.actor.type=='Organization')].actor.identifier.value"
        ODS_code_format = re.compile(r"^[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9]{1}[A-Z]{1}$")
        try:
            field_value = [x for x in values["performer"] if x.get("actor").get("type") == "Organization"][0]["actor"][
                "identifier"
            ]["value"]
            PreValidation.for_string(field_value, field_location)

            # Validates that organization_identifier_value SITE CODE is in alpha-numeric-alpha-numeric-alpha
            # (e.g. "X0X0X")
            if not ODS_code_format.match(field_value):
                raise ValueError(
                    f"{field_location} must be in expected format" + " alpha-numeric-alpha-numeric-alpha (e.g X0X0X)"
                )
        except (KeyError, IndexError, AttributeError):
            pass

    def pre_validate_identifier(self, values: dict) -> dict:
        """Pre-validate that, if identifier exists, then it is a list of length 1"""
        try:
            field_value = values["identifier"]
            PreValidation.for_list(field_value, "identifier", defined_length=1)
        except KeyError:
            pass

    def pre_validate_identifier_value(self, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0].value (legacy CSV field name: UNIQUE_ID) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["identifier"][0]["value"]
            PreValidation.for_string(field_value, "identifier[0].value")
        except (KeyError, IndexError):
            pass

    def pre_validate_identifier_system(self, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0].system (legacy CSV field name: UNIQUE_ID_URI) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["identifier"][0]["system"]
            PreValidation.for_string(field_value, "identifier[0].system")
        except (KeyError, IndexError):
            pass

    def pre_validate_status(self, values: dict) -> dict:
        """
        Pre-validate that, if status exists, then its value is "completed"

        NOTE: Status is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """
        try:
            field_value = values["status"]
            PreValidation.for_string(field_value, "status", predefined_values=Constants.STATUSES)
        except KeyError:
            pass

    def pre_validate_practitioner_name(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].name exists,
        then it is an array of length 1
        """
        field_location = "contained[?(@.resourceType=='Practitioner')].name"
        try:
            field_values = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["name"]
            PreValidation.for_list(field_values, field_location, defined_length=1)
        except (KeyError, IndexError):
            pass

    def pre_validate_practitioner_name_given(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].name[0].given (legacy CSV field name:
        PERSON_FORENAME) exists, then it is a an array containing a single non-empty string
        """
        field_location = "contained[?(@.resourceType=='Practitioner')].name[0].given"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["name"][0][
                "given"
            ]
            PreValidation.for_list(field_value, field_location, defined_length=1, elements_are_strings=True)
        except (KeyError, IndexError):
            pass

    def pre_validate_practitioner_name_family(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].name[0].family (legacy CSV field name:
        PERSON_SURNAME) exists, then it is a an array containing a single non-empty string
        """
        field_location = "contained[?(@.resourceType=='Practitioner')].name[0].family"
        try:
            field_name = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["name"][0][
                "family"
            ]
            PreValidation.for_string(field_name, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_recorded(self, values: dict) -> dict:
        """
        Pre-validate that, if occurrenceDateTime exists (legacy CSV field name: RECORDED_DATE),
        then it is a string in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or "YYYY-MM-DDThh:mm:ss-zz:zz"
        (i.e. date and time, including timezone offset in hours and minutes), representing a valid
        datetime. Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).
        """
        try:
            recorded = values["recorded"]
            PreValidation.for_date_time(recorded, "recorded")
        except KeyError:
            pass

    def pre_validate_primary_source(self, values: dict) -> dict:
        """
        Pre-validate that, if primarySource (legacy CSV field name: PRIMARY_SOURCE) exists, then it is a boolean
        """
        try:
            primary_source = values["primarySource"]
            PreValidation.for_boolean(primary_source, "primarySource")
        except KeyError:
            pass

    def pre_validate_extension_urls(self, values: dict) -> dict:
        """Pre-validate that, if extension exists, then each url is unique"""
        try:
            PreValidation.for_unique_list(values["extension"], "url", "extension[?(@.url=='FIELD_TO_REPLACE')]")
        except (KeyError, IndexError):
            pass

    def pre_validate_extension_value_codeable_concept_codings(self, values: dict) -> dict:
        """Pre-validate that, if they exist, each extension[{index}].valueCodeableConcept.coding.system is unique"""
        try:
            for i in range(len(values["extension"])):
                try:
                    extension_value_codeable_concept_coding = values["extension"][i]["valueCodeableConcept"]["coding"]
                    PreValidation.for_unique_list(
                        extension_value_codeable_concept_coding,
                        "system",
                        f"extension[?(@.URL=='{values['extension'][i]['url']}']"
                        + ".valueCodeableConcept.coding[?(@.system=='FIELD_TO_REPLACE')]",
                    )
                except KeyError:
                    pass
        except KeyError:
            pass

    def pre_validate_vaccination_procedure_code(self, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-
        VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code
        (legacy CSV field name: VACCINATION_PROCEDURE_CODE) exists, then it is a non-empty string
        """
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "VaccinationProcedure"
        system = "http://snomed.info/sct"
        field_type = "code"
        field_location = generate_field_location_for_extension(url, system, field_type)
        try:
            field_value = get_generic_extension_value(values, url, system, field_type)
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_vaccination_procedure_display(self, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-
        VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display
        (legacy CSV field name: VACCINATION_PROCEDURE_TERM) exists, then it is a non-empty string
        """
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "VaccinationProcedure"
        system = "http://snomed.info/sct"
        field_type = "display"
        field_location = generate_field_location_for_extension(url, system, field_type)
        try:
            field_value = get_generic_extension_value(values, url, system, field_type)
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_vaccination_situation_code(self, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-
        VaccinationSituation')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code
        (legacy CSV field name: VACCINATION_SITUATION_CODE) exists, then it is a non-empty string
        """
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation"
        system = "http://snomed.info/sct"
        field_type = "code"
        field_location = generate_field_location_for_extension(url, system, field_type)
        try:
            field_value = get_generic_extension_value(values, url, system, field_type)
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_vaccination_situation_display(self, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-
        VaccinationSituation')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display
        (legacy CSV field name: VACCINATION_SITUATION_TERM) exists, then it is a non-empty string
        """
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation"
        system = "http://snomed.info/sct"
        field_type = "display"
        field_location = generate_field_location_for_extension(url, system, field_type)
        try:
            field_value = get_generic_extension_value(values, url, system, field_type)
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_protocol_applied(self, values: dict) -> dict:
        """Pre-validate that, if protocolApplied exists, then it is a list of length 1"""
        try:
            field_value = values["protocolApplied"]
            PreValidation.for_list(field_value, "protocolApplied", defined_length=1)
        except KeyError:
            pass

    def pre_validate_dose_number_positive_int(self, values: dict) -> dict:
        """
        Pre-validate that, if protocolApplied[0].doseNumberPositiveInt (legacy CSV field : dose_sequence)
        exists, then it is an integer from 1 to 9
        """
        field_location = "protocolApplied[0].doseNumberPositiveInt"
        try:
            field_value = values["protocolApplied"][0]["doseNumberPositiveInt"]
            PreValidation.for_positive_integer(field_value, field_location, max_value=9)
        except (KeyError, IndexError):
            pass

    def pre_validate_dose_number_string(self, values: dict) -> dict:
        """
        Pre-validate that, if protocolApplied[0].doseNumberString exists, then it
        is a non-empty string
        """
        field_location = "protocolApplied[0].doseNumberString"
        try:
            field_value = values["protocolApplied"][0]["doseNumberString"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_target_disease(self, values: dict) -> dict:
        """
        Pre-validate that protocolApplied[0].targetDisease exists, and each of its elements contains a coding field
        """
        try:
            field_value = values["protocolApplied"][0]["targetDisease"]
            for element in field_value:
                if "coding" not in element:
                    raise ValueError("Every element of protocolApplied[0].targetDisease must have 'coding' property")
        except (KeyError, IndexError) as error:
            raise ValueError("protocolApplied[0].targetDisease is a mandatory field") from error

    def pre_validate_target_disease_codings(self, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each protocolApplied[0].targetDisease[{index}].valueCodeableConcept.coding
        has exactly one element where the system is the snomed url
        """
        try:
            for i in range(len(values["protocolApplied"][0]["targetDisease"])):
                field_location = f"protocolApplied[0].targetDisease[{i}].coding"
                try:
                    coding = values["protocolApplied"][0]["targetDisease"][i]["coding"]
                    if sum(1 for x in coding if x.get("system") == Urls.snomed) != 1:
                        raise ValueError(
                            f"{field_location} must contain exactly one element with a system of {Urls.snomed}"
                        )
                except KeyError:
                    pass
        except KeyError:
            pass

    def pre_validate_disease_type_coding_codes(self, values: dict) -> dict:
        """
        Pre-validate that, if protocolApplied[0].targetDisease[{i}].coding[?(@.system=='http://snomed.info/sct')].code
        exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        try:
            for i in range(len(values["protocolApplied"][0]["targetDisease"])):
                field_location = f"protocolApplied[0].targetDisease[{i}].coding[?(@.system=='{url}')].code"
                try:
                    target_disease_coding = values["protocolApplied"][0]["targetDisease"][i]["coding"]
                    target_disease_coding_code = [x for x in target_disease_coding if x.get("system") == url][0]["code"]
                    PreValidation.for_string(target_disease_coding_code, field_location)
                except (KeyError, IndexError):
                    pass
        except KeyError:
            pass

    def pre_validate_vaccine_code_coding(self, values: dict) -> dict:
        """Pre-validate that, if vaccineCode.coding exists, then each code system is unique"""
        field_location = "vaccineCode.coding[?(@.system=='FIELD_TO_REPLACE')]"
        try:
            vaccine_code_coding = values["vaccineCode"]["coding"]
            PreValidation.for_unique_list(vaccine_code_coding, "system", field_location)
        except KeyError:
            pass

    def pre_validate_vaccine_code_coding_code(self, values: dict) -> dict:
        """
        Pre-validate that, if vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code (legacy CSV field location:
        REASON_NOT_GIVEN_CODE) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"vaccineCode.coding[?(@.system=='{url}')].code"
        try:
            field_value = [x for x in values["vaccineCode"]["coding"] if x.get("system") == url][0]["code"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_vaccine_code_coding_display(self, values: dict) -> dict:
        """
        Pre-validate that, if vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display (legacy CSV field name:
        REASON_NOT_GIVEN_TERM) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display"
        try:
            field_value = [x for x in values["vaccineCode"]["coding"] if x.get("system") == url][0]["display"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_manufacturer_display(self, values: dict) -> dict:
        """
        Pre-validate that, if manufacturer.display (legacy CSV field name: VACCINE_MANUFACTURER)
        exists, then it is a non-empty string
        """
        try:
            field_value = values["manufacturer"]["display"]
            PreValidation.for_string(field_value, "manufacturer.display")
        except KeyError:
            pass

    def pre_validate_lot_number(self, values: dict) -> dict:
        """
        Pre-validate that, if lotNumber (legacy CSV field name: BATCH_NUMBER) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["lotNumber"]
            PreValidation.for_string(field_value, "lotNumber", max_length=100)
        except KeyError:
            pass

    def pre_validate_expiration_date(self, values: dict) -> dict:
        """
        Pre-validate that, if expirationDate (legacy CSV field name: EXPIRY_DATE) exists,
        then it is a string in the format YYYY-MM-DD, representing a valid date
        """
        try:
            field_value = values["expirationDate"]
            PreValidation.for_date(field_value, "expirationDate")
        except KeyError:
            pass

    def pre_validate_site_coding(self, values: dict) -> dict:
        """Pre-validate that, if site.coding exists, then each code system is unique"""
        try:
            field_value = values["site"]["coding"]
            PreValidation.for_unique_list(field_value, "system", "site.coding[?(@.system=='FIELD_TO_REPLACE')]")
        except KeyError:
            pass

    def pre_validate_site_coding_code(self, values: dict) -> dict:
        """
        Pre-validate that, if site.coding[?(@.system=='http://snomed.info/sct')].code
        (legacy CSV field name: SITE_OF_VACCINATION_CODE) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"site.coding[?(@.system=='{url}')].code"
        try:
            site_coding_code = [x for x in values["site"]["coding"] if x.get("system") == url][0]["code"]
            PreValidation.for_string(site_coding_code, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_site_coding_display(self, values: dict) -> dict:
        """
        Pre-validate that, if site.coding[?(@.system=='http://snomed.info/sct')].display
        (legacy CSV field name: SITE_OF_VACCINATION_TERM) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"site.coding[?(@.system=='{url}')].display"
        try:
            field_value = [x for x in values["site"]["coding"] if x.get("system") == url][0]["display"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_route_coding(self, values: dict) -> dict:
        """Pre-validate that, if route.coding exists, then each code system is unique"""
        try:
            field_value = values["route"]["coding"]
            PreValidation.for_unique_list(field_value, "system", "route.coding[?(@.system=='FIELD_TO_REPLACE')]")
        except KeyError:
            pass

    def pre_validate_route_coding_code(self, values: dict) -> dict:
        """
        Pre-validate that, if route.coding[?(@.system=='http://snomed.info/sct')].code
        (legacy CSV field name: ROUTE_OF_VACCINATION_CODE) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"route.coding[?(@.system=='{url}')].code"
        try:
            field_value = [x for x in values["route"]["coding"] if x.get("system") == url][0]["code"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_route_coding_display(self, values: dict) -> dict:
        """
        Pre-validate that, if route.coding[?(@.system=='http://snomed.info/sct')].display
        (legacy CSV field name: ROUTE_OF_VACCINATION_TERM) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"route.coding[?(@.system=='{url}')].display"
        try:
            field_value = [x for x in values["route"]["coding"] if x.get("system") == url][0]["display"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    # TODO: need to validate that doseQuantity.system is "http://unitsofmeasure.org"?
    # Check with Martin

    def pre_validate_dose_quantity_value(self, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity.value (legacy CSV field name: DOSE_AMOUNT) exists,
        then it is a number representing an integer or decimal with
        maximum four decimal places

        NOTE: This validator will only work if the raw json data is parsed with the
        parse_float argument set to equal Decimal type (Decimal must be imported from decimal).
        Floats (but not integers) will then be parsed as Decimals.
        e.g json.loads(raw_data, parse_float=Decimal)
        """
        try:
            field_value = values["doseQuantity"]["value"]
            PreValidation.for_integer_or_decimal(field_value, "doseQuantity.value", max_decimal_places=4)
        except KeyError:
            pass

    def pre_validate_dose_quantity_code(self, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity.code (legacy CSV field name: DOSE_UNIT_CODE) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["doseQuantity"]["code"]
            PreValidation.for_string(field_value, "doseQuantity.code")
        except KeyError:
            pass

    def pre_validate_dose_quantity_unit(self, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity.unit (legacy CSV field name: DOSE_UNIT_TERM) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["doseQuantity"]["unit"]
            PreValidation.for_string(field_value, "doseQuantity.unit")
        except KeyError:
            pass

    def pre_validate_reason_code_codings(self, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[{index}].coding is a list of length 1
        """
        try:
            for index, value in enumerate(values["reasonCode"]):
                try:
                    field_value = value["coding"]
                    PreValidation.for_list(field_value, f"reasonCode[{index}].coding", defined_length=1)
                except KeyError:
                    pass
        except KeyError:
            pass

    def pre_validate_reason_code_coding_codes(self, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[{index}].coding[0].code
        (legacy CSV field name: INDICATION_CODE) is a non-empty string
        """
        try:
            for index, value in enumerate(values["reasonCode"]):
                try:
                    field_value = value["coding"][0]["code"]
                    PreValidation.for_string(field_value, f"reasonCode[{index}].coding[0].code")
                except KeyError:
                    pass
        except KeyError:
            pass

    def pre_validate_organization_identifier_system(self, values: dict) -> dict:
        """
        Pre-validate that, if performer[?(@.actor.type=='Organization').identifier.system]
        (legacy CSV field name: SITE_CODE_TYPE_URI) exists, then it is a non-empty string
        """
        field_location = "performer[?(@.actor.type=='Organization')].actor.identifier.system"
        try:
            field_value = [x for x in values["performer"] if x.get("actor").get("type") == "Organization"][0]["actor"][
                "identifier"
            ]["system"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError, AttributeError):
            pass

    def pre_validate_location_identifier_value(self, values: dict) -> dict:
        """
        Pre-validate that, if location.identifier.value (legacy CSV field name: LOCATION_CODE) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["location"]["identifier"]["value"]
            PreValidation.for_string(field_value, "location.identifier.value")
        except KeyError:
            pass

    def pre_validate_location_identifier_system(self, values: dict) -> dict:
        """
        Pre-validate that, if location.identifier.system (legacy CSV field name: LOCATION_CODE_TYPE_URI) exists,
        then it is a non-empty string
        """
        try:
            field_value = values["location"]["identifier"]["system"]
            PreValidation.for_string(field_value, "location.identifier.system")
        except KeyError:
            pass

    def pre_validate_location_type(self, values: dict) -> dict:
        """Pre-validate that, if location.type exists, then its value is 'Location'"""
        try:
            field_value = values["location"]["type"]
            PreValidation.for_string(field_value, "location.type", predefined_values=["Location"])
        except KeyError:
            pass

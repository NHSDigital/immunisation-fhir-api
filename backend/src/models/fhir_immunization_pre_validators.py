"FHIR Immunization Pre Validators"

from src.models.constants import Constants
from src.models.utils.generic_utils import (
    get_generic_questionnaire_response_value,
    get_generic_extension_value,
    generate_field_location_for_questionnaire_response,
    generate_field_location_for_extension,
)
from src.models.utils.pre_validator_utils import PreValidation


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
            self.pre_validate_contained,
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
            self.pre_validate_questionnaire_response_item,
            self.pre_validate_questionnaire_answers,
            self.pre_validate_performer_actor_type,
            self.pre_validate_performer_actor_reference,
            self.pre_validate_organization_identifier_value,
            self.pre_validate_organization_display,
            self.pre_validate_identifier,
            self.pre_validate_identifier_value,
            self.pre_validate_identifier_system,
            self.pre_validate_status,
            self.pre_validate_practitioner_name,
            self.pre_validate_practitioner_name_given,
            self.pre_validate_practitioner_name_family,
            self.pre_validate_practitioner_identifier,
            self.pre_validate_practitioner_identifier_value,
            self.pre_validate_practitioner_identifier_system,
            self.pre_validate_performer_sds_job_role,
            self.pre_validate_recorded,
            self.pre_validate_primary_source,
            self.pre_validate_report_origin_text,
            self.pre_validate_extension_urls,
            self.pre_validate_extension_value_codeable_concept_codings,
            self.pre_validate_vaccination_procedure_code,
            self.pre_validate_vaccination_procedure_display,
            self.pre_validate_vaccination_situation_code,
            self.pre_validate_vaccination_situation_display,
            self.pre_validate_status_reason_coding,
            self.pre_validate_status_reason_coding_code,
            self.pre_validate_status_reason_coding_display,
            self.pre_validate_protocol_applied,
            self.pre_validate_protocol_applied_dose_number_positive_int,
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
            self.pre_validate_reason_code_coding_displays,
            self.pre_validate_patient_identifier_extension,
            self.pre_validate_nhs_number_verification_status_coding,
            self.pre_validate_nhs_number_verification_status_code,
            self.pre_validate_nhs_number_verification_status_display,
            self.pre_validate_organization_identifier_system,
            self.pre_validate_local_patient_value,
            self.pre_validate_local_patient_system,
            self.pre_validate_consent_code,
            self.pre_validate_consent_display,
            self.pre_validate_care_setting_code,
            self.pre_validate_care_setting_display,
            self.pre_validate_ip_address,
            self.pre_validate_user_id,
            self.pre_validate_user_name,
            self.pre_validate_user_email,
            self.pre_validate_submitted_time_stamp,
            self.pre_validate_location_identifier_value,
            self.pre_validate_location_identifier_system,
            self.pre_validate_reduce_validation,
            self.pre_validate_reduce_validation_reason,
        ]

        for method in validation_methods:
            try:
                method(self.immunization)
            except (ValueError, TypeError, IndexError, AttributeError) as e:
                self.errors.append(str(e))

        if self.errors:
            all_errors = "; ".join(self.errors)
            raise ValueError(f"Validation errors: {all_errors}")

    def pre_validate_contained(self, values: dict) -> dict:
        """Pre-validate that, if contained exists, then  each resourceType is unique"""
        try:
            contained = values["contained"]
            PreValidation.for_unique_list(contained, "resourceType", "contained[?(@.resourceType=='FIELD_TO_REPLACE')]")
        except KeyError:
            pass

    def pre_validate_patient_reference(self, values: dict) -> dict:
        """
        Pre-validate that:
        - patient.reference exists and it is a reference
        - patient.reference matches the contained patient resource id
        - contained Patient resource has an id
        - there is a contained Patient resource
        """

        # Obtain the patient.reference that are internal references (#)
        patient_reference = values.get("patient", {}).get("reference")

        # Make sure we have a reference
        if not (isinstance(patient_reference, str) and patient_reference.startswith("#")):
            raise ValueError("patient.reference must be a single reference to a contained Patient resource")

        # Obtain the contained patient resource
        try:
            contained_patient = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]

            try:
                # Try to obtain the contained patient resource id
                contained_patient_id = contained_patient["id"]

                # If the reference is not equal to the ID then raise an error
                if ("#" + contained_patient_id) != patient_reference:
                    raise ValueError(
                        f"The reference '{patient_reference}' does " + "not exist in the contained Patient resource"
                    )
            except KeyError as error:
                # If the contained Patient resource has no id raise an error
                raise ValueError("The contained Patient resource must have an 'id' field") from error

        except (IndexError, KeyError) as error:
            # Entering this exception block implies that there is no contained patient resource
            # therefore raise an error
            raise ValueError("contained[?(@.resourceType=='Patient')] is mandatory") from error

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
        datetime. Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00)."

        NOTE: occurrenceDateTime is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """
        field_location = "occurrenceDateTime"
        try:
            field_value = values["occurrenceDateTime"]
            PreValidation.for_date_time(field_value, field_location)
        except KeyError:
            pass

    def pre_validate_questionnaire_response_item(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item exists,
        then each linkId is unique
        """
        field_location = "contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='FIELD_TO_REPLACE')]"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "QuestionnaireResponse"][0][
                "item"
            ]
            PreValidation.for_unique_list(field_value, "linkId", field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_questionnaire_answers(self, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each contained[?(@.resourceType=='QuestionnaireResponse')].item[index].answer
        is a list of length 1
        """
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "QuestionnaireResponse"][0][
                "item"
            ]
            for index, value in enumerate(field_value):
                field_location = f"contained[?(@.resourceType=='QuestionnaireResponse')].item[{index}].answer"
                try:
                    questionnaire_answer = value["answer"]
                    PreValidation.for_list(questionnaire_answer, field_location, defined_length=1)
                except KeyError:
                    pass
        except (KeyError, IndexError):
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
        (legacy CSV field name: SITE_CODE) exists, then it is a non-empty string
        """
        field_location = "performer[?(@.actor.type=='Organization')].actor.identifier.value"
        try:
            field_value = [x for x in values["performer"] if x.get("actor").get("type") == "Organization"][0]["actor"][
                "identifier"
            ]["value"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError, AttributeError):
            pass

    def pre_validate_organization_display(self, values: dict) -> dict:
        """
        Pre-validate that, if performer[?@.actor.type == 'Organization'].actor.display
        (legacy CSV field name: SITE_NAME) exists, then it is a non-empty string
        """
        field_location = "performer[?@.actor.type == 'Organization'].actor.display"
        try:
            field_value = [x for x in values["performer"] if x.get("actor").get("type") == "Organization"][0]["actor"][
                "display"
            ]
            PreValidation.for_string(field_value, field_location)
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
        Pre-validate that, if status (legacy CSV field names ACTION_FLAG or NOT_GIVEN) exists,
        then it is a non-empty string which is one of the following: completed, entered-in-error,
        not-done.

        NOTE 1: The following mapping applies:
        # TODO: Check this mapping with Imms team
        * NOT_GIVEN is True & ACTION_FLAG is "new" or "update" or "delete" <---> Status is 'not-done'
        * NOT_GIVEN is False & ACTION_FLAG is "new" or "update" <---> Status is 'completed'
        * NOT_GIVEN is False and ACTION_FLAG is "delete" <---> Status is entered-in-error'

        NOTE 2: Status is a mandatory FHIR field. A value of None will be rejected by the
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

    def pre_validate_practitioner_identifier(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].identifier exists,
        then it is a list of length 1
        """
        field_location = "contained[?(@.resourceType=='Practitioner')].identifier"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["identifier"]
            PreValidation.for_list(field_value, field_location, defined_length=1)
        except (KeyError, IndexError):
            pass

    def pre_validate_practitioner_identifier_value(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].identifier[0].value (legacy CSV field name:
        PERFORMING_PROFESSIONAL_BODY_REG_CODE) exists, then it is a non-empty string
        """
        field_location = "contained[?(@.resourceType=='Practitioner')].identifier[0].value"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["identifier"][
                0
            ]["value"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_practitioner_identifier_system(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].identifier[0].system (legacy CSV field name:
        PERFORMING_PROFESSIONAL_BODY_REG_URI) exists, then it is a non-empty string
        """
        field_location = "contained[?(@.resourceType=='Practitioner')].identifier[0].system"
        try:
            field_value = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["identifier"][
                0
            ]["system"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_performer_sds_job_role(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='PerformerSDSJob
        Role')].answer[0].valueString (legacy CSV field name: SDS_JOB_ROLE_NAME) exists, then it is a non-empty string
        """
        answer_type = "valueString"
        field_location = generate_field_location_for_questionnaire_response("PerformerSDSJobRole", answer_type)
        try:
            field_value = get_generic_questionnaire_response_value(values, "PerformerSDSJobRole", answer_type)
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_recorded(self, values: dict) -> dict:
        """
        Pre-validate that, if recorded (legacy CSV field name: RECORDED_DATE) exists, then it is a
        string in the format YYYY-MM-DD, representing a valid date
        """
        try:
            recorded = values["recorded"]
            PreValidation.for_date(recorded, "recorded")
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

    def pre_validate_report_origin_text(self, values: dict) -> dict:
        """
        Pre-validate that, if reportOrigin.text (legacy CSV field name: REPORT_ORIGIN_TEXT)
        exists, then it is a non-empty string with maximum length 100 characters
        """
        try:
            report_origin_text = values["reportOrigin"]["text"]
            PreValidation.for_string(report_origin_text, "reportOrigin.text", max_length=100)
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

    def pre_validate_status_reason_coding(self, values: dict) -> dict:
        """
        Pre-validate that, if statusReason.coding (legacy CSV field name: REASON_GIVEN_CODE)
        exists, then each coding system value is unique
        """
        field_location = "statusReason.coding[?(@.system=='FIELD_TO_REPLACE')]"
        try:
            field_value = values["statusReason"]["coding"]
            PreValidation.for_unique_list(field_value, "system", field_location)
        except KeyError:
            pass

    def pre_validate_status_reason_coding_code(self, values: dict) -> dict:
        """
        Pre-validate that, if statusReason.coding[?(@.system=='http://snomed.info/sct')].code (legacy CSV field
        location: REASON_NOT_GIVEN_CODE) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"statusReason.coding[?(@.system=='{url}')].code"
        try:
            field_value = [x for x in values["statusReason"]["coding"] if x.get("system") == url][0]["code"]
            PreValidation.for_string(field_value, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_status_reason_coding_display(self, values: dict) -> dict:
        """
        Pre-validate that, if statusReason.coding[?(@.system=='http://snomed.info/sct')].display (legacy CSV field name:
        REASON_NOT_GIVEN_TERM) exists, then it is a non-empty string
        """
        url = "http://snomed.info/sct"
        field_location = f"statusReason.coding[?(@.system=='{url}')].display"
        try:
            field_value = [x for x in values["statusReason"]["coding"] if x.get("system") == url][0]["display"]
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

    def pre_validate_protocol_applied_dose_number_positive_int(self, values: dict) -> dict:
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

    def pre_validate_target_disease(self, values: dict) -> dict:
        """
        Pre-validate that, if protocolApplied[0].targetDisease exists, then each of its elements contains a coding field
        """
        try:
            field_value = values["protocolApplied"][0]["targetDisease"]
            for element in field_value:
                if "coding" not in element:
                    raise ValueError("Every element of protocolApplied[0].targetDisease must have 'coding' property")
        except (KeyError, IndexError):
            pass

    def pre_validate_target_disease_codings(self, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each
        protocolApplied[0].targetDisease[{index}].valueCodeableConcept.coding.system is unique
        """
        try:
            for i in range(len(values["protocolApplied"][0]["targetDisease"])):
                field_location = f"protocolApplied[0].targetDisease[{i}].coding[?(@.system=='FIELD_TO_REPLACE')]"
                try:
                    field_value = values["protocolApplied"][0]["targetDisease"][i]["coding"]
                    PreValidation.for_unique_list(field_value, "system", field_location)
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
                except KeyError:
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

    def pre_validate_reason_code_coding_displays(self, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[{index}].coding[0].display
        (legacy CSV field name: INDICATION_TERM) is a non-empty string
        """
        try:
            for index, value in enumerate(values["reasonCode"]):
                try:
                    field_value = value["coding"][0]["display"]
                    PreValidation.for_string(field_value, f"reasonCode[{index}].coding[0].display")
                except KeyError:
                    pass
        except (KeyError, IndexError):
            pass

    def pre_validate_patient_identifier_extension(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].identifier
        [?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].extension exists, then each url is unique
        """
        url = "https://fhir.nhs.uk/Id/nhs-number"
        field_location = (
            f"contained[?(@.resourceType=='Patient')].identifier[?(@.system=='{url}')]"
            + ".extension[?(@.url=='FIELD_TO_REPLACE')]"
        )
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            field_value = [x for x in patient_identifier if x.get("system") == url][0]["extension"]
            PreValidation.for_unique_list(field_value, "url", field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_nhs_number_verification_status_coding(self, values: dict) -> dict:
        """
        Pre-validate that, if "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id
        /nhs-number')].extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-
        NHSNumberVerificationStatus')].valueCodeableConcept.coding exists, then each url is unique
        """
        url_1 = "https://fhir.nhs.uk/Id/nhs-number"
        url_2 = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
        field_location = (
            f"contained[?(@.resourceType=='Patient')].identifier[?(@.system=='{url_1}')].extension[?(@.url=="
            + f"'{url_2}')].valueCodeableConcept.coding[?(@.system=='FIELD_TO_REPLACE')]"
        )
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            patient_extension = [x for x in patient_identifier if x.get("system") == url_1][0]["extension"]
            field_value = [x for x in patient_extension if x.get("url") == url_2][0]["valueCodeableConcept"]["coding"]
            PreValidation.for_unique_list(field_value, "system", field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_nhs_number_verification_status_code(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].extension[?(@.url=='https://fhir.hl7.org.uk/
        StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus')].valueCodeableConcept.coding[0].code
        (legacy CSV field name: NHS_NUMBER_STATUS_INDICATOR_CODE) exists, then it is a non-empty string
        """
        url_1 = "https://fhir.nhs.uk/Id/nhs-number"
        url_2 = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
        system = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
        field_type = "code"
        field_location = (
            f"contained[?(@.resourceType=='Patient')].identifier[?(@.system=='{url_1}')]."
            + generate_field_location_for_extension(url_2, system, field_type)
        )
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            patient_identifier_extension_item = [x for x in patient_identifier if x.get("system") == url_1][0]
            nhs_number_verification_status_code = get_generic_extension_value(
                patient_identifier_extension_item, url_2, system, field_type
            )
            PreValidation.for_string(nhs_number_verification_status_code, field_location)
        except (KeyError, IndexError):
            pass

    def pre_validate_nhs_number_verification_status_display(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].extension[?(@.url=='https://fhir.hl7.org.uk/
        StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus')].valueCodeableConcept.coding[0].display
        (legacy CSV field name: NHS_NUMBER_STATUS_INDICATOR_DESCRIPTION) exists, then it is a non-empty string
        """
        url_1 = "https://fhir.nhs.uk/Id/nhs-number"
        url_2 = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
        system = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
        field_type = "display"
        field_location = (
            f"contained[?(@.resourceType=='Patient')].identifier[?(@.system=='{url_1}')]."
            + generate_field_location_for_extension(url_2, system, field_type)
        )
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            patient_identifier_extension_item = [x for x in patient_identifier if x.get("system") == url_1][0]
            nhs_number_verification_status_code = get_generic_extension_value(
                patient_identifier_extension_item, url_2, system, field_type
            )
            PreValidation.for_string(nhs_number_verification_status_code, field_location)
        except (KeyError, IndexError):
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

    def pre_validate_local_patient_value(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='LocalPatient')].
        valueReference.identifier.value (legacy CSV field name: LOCAL_PATIENT_ID) exists, then it is a non-empty string
        """
        answer_type = "valueReference"
        field_type = "value"
        field_location = generate_field_location_for_questionnaire_response("LocalPatient", answer_type, field_type)
        try:
            field_value = get_generic_questionnaire_response_value(values, "LocalPatient", answer_type, field_type)
            PreValidation.for_string(field_value, field_location, max_length=20)
        except (KeyError, IndexError):
            pass

    def pre_validate_local_patient_system(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='LocalPatient')].
        valueReference.identifier.system (legacy CSV field name: LOCAL_PATIENT_URI) exists,
        then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(
            values, link_id="LocalPatient", answer_type="valueReference", field_type="system"
        )

    def pre_validate_consent_code(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='Consent')].
        answer[0].valueCoding.code (legacy CSV field name: CONSENT_FOR_TREATMENT_CODE) exists,
        then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(
            values, link_id="Consent", answer_type="valueCoding", field_type="code"
        )

    def pre_validate_consent_display(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='Consent')].
        answer[0].valueCoding.display (legacy CSV field name: CONSENT_FOR_TREATMENT_DESCRIPTION) exists,
        then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(
            values, link_id="Consent", answer_type="valueCoding", field_type="display"
        )

    def pre_validate_care_setting_code(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='CareSetting')].
        answer[0].valueCoding.code (legacy CSV field name: CARE_SETTING_TYPE_CODE) exists,
        then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(
            values, link_id="CareSetting", answer_type="valueCoding", field_type="code"
        )

    def pre_validate_care_setting_display(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='CareSetting')].
        answer[0].valueCoding.display (legacy CSV field name: CARE_SETTING_TYPE_DESCRIPTION) exists,
        then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(
            values, link_id="CareSetting", answer_type="valueCoding", field_type="display"
        )

    def pre_validate_ip_address(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='IpAddress')].
        answer[0].valueString (legacy CSV field name: IP_ADDRESS) exists, then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(values, link_id="IpAddress", answer_type="valueString")

    def pre_validate_user_id(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='UserId')].
        answer[0].valueString (legacy CSV field name: USER_ID) exists, then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(values, link_id="UserId", answer_type="valueString")

    def pre_validate_user_name(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='UserName')].
        answer[0].valueString (legacy CSV field name: USER_NAME) exists, then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(values, link_id="UserName", answer_type="valueString")

    def pre_validate_user_email(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='UserEmail')].
        answer[0].valueString (legacy CSV field name: USER_EMAIL) exists, then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(values, link_id="UserEmail", answer_type="valueString")

    def pre_validate_submitted_time_stamp(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId==
        'SubmittedTimeStamp')].answer[0].valueDateTime (legacy CSV field name: SUBMITTED_TIMESTAMP), then it is a string
        in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or "YYYY-MM-DDThh:mm:ss-zz:zz" (i.e. date and time, including
        timezone offset in hours and minutes), representing a valid datetime. Milliseconds are optional after the
        seconds (e.g. 2021-01-01T00:00:00.000+00:00).
        """
        PreValidation.for_questionnaire_response(values, link_id="SubmittedTimeStamp", answer_type="valueDateTime")

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

    def pre_validate_reduce_validation(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId=='ReduceValidation')
        ].answer[0].valueBoolean (legacy CSV field name: REDUCE_VALIDATION_CODE) exists, then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(values, link_id="ReduceValidation", answer_type="valueBoolean")

    def pre_validate_reduce_validation_reason(self, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item[?(@.linkId==
        'ReduceValidationReason')].answer[0].valueString" (legacy CSV field name: REDUCE_VALIDATION_REASON) exists,
        then it is a non-empty string
        """
        PreValidation.for_questionnaire_response(values, link_id="ReduceValidationReason", answer_type="valueString")
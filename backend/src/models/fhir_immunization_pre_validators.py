"FHIR Immunization Pre Validators"

from models.constants import Constants
from models.utils.generic_utils import (
    get_generic_questionnaire_response_value,
    get_generic_extension_value,
    generate_field_location_for_questionnnaire_response,
    generate_field_location_for_extension,
)
from models.utils.pre_validator_utils import PreValidation


class FHIRImmunizationPreValidators:
    """
    Validators which run prior to the FHIR validators and check that, where values exist, they
    meet the NHS custom requirements. Note that validation of the existence of a value (i.e. it
    exists if mandatory, or doesn't exist if is not applicable) is done by the post validators.
    """

    @classmethod
    def pre_validate_contained(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained exists, then  each resourceType is unique
        """
        try:
            contained = values["contained"]
            PreValidation.for_unique_list(
                contained,
                "resourceType",
                "contained[?(@.resourceType=='FIELD_TO_REPLACE')]",
            )

        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_patient_reference(cls, values: dict) -> dict:
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

        return values

    @classmethod
    def pre_validate_patient_identifier(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].identifier exists, then it
        is a list of length 1
        """
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            PreValidation.for_list(
                patient_identifier,
                "contained[?(@.resourceType=='Patient')].identifier",
                defined_length=1,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].identifier[0].value (
        legacy CSV field name: NHS_NUMBER) exists, then it is a string of 10 characters
        which does not contain spaces
        """
        try:
            patient_identifier_value = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0][
                "identifier"
            ][0]["value"]

            PreValidation.for_string(
                patient_identifier_value,
                "contained[?(@.resourceType=='Patient')].identifier[0].value",
                defined_length=10,
                spaces_allowed=False,
            )

            PreValidation.for_nhs_number(
                patient_identifier_value, "contained[?(@.resourceType=='Patient')].identifier[0].value"
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_name(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].name exists,
        then it is an array of length 1
        """
        try:
            patient_name = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["name"]
            PreValidation.for_list(
                patient_name,
                "contained[?(@.resourceType=='Patient')].name",
                defined_length=1,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_name_given(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].name[0].given
        (legacy CSV field name: PERSON_FORENAME) exists, then it is a
        an array containing a single non-empty string
        """
        try:
            patient_name_given = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["name"][0][
                "given"
            ]
            PreValidation.for_list(
                patient_name_given,
                "contained[?(@.resourceType=='Patient')].name[0].given",
                defined_length=1,
                elements_are_strings=True,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_name_family(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].name[0].family
        (legacy CSV field name: PERSON_SURNAME) exists, then it is a
        an array containing a single non-empty string
        """
        try:
            patient_name_family = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["name"][0][
                "family"
            ]
            PreValidation.for_string(
                patient_name_family,
                "contained[?(@.resourceType=='Patient')].name[0].family",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_birth_date(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].birthDate
        (legacy CSV field name: PERSON_DOB) exists, then it is a
        string in the format YYYY-MM-DD, representing a valid date
        """
        try:
            patient_birth_date = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["birthDate"]
            PreValidation.for_date(patient_birth_date, "contained[?(@.resourceType=='Patient')].birthDate")
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_gender(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].gender
        (legacy CSV field name: PERSON_GENDER_CODE) exists,
        then it is a string, which is one of the following: male, female, other, unknown
        """
        try:
            patient_gender = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["gender"]
            PreValidation.for_string(
                patient_gender,
                "contained[?(@.resourceType=='Patient')].gender",
                predefined_values=Constants.GENDERS,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_address(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].address exists, then it is
        an array of length 1
        """
        try:
            patient_address = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["address"]
            PreValidation.for_list(
                patient_address,
                "contained[?(@.resourceType=='Patient')].address",
                defined_length=1,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_address_postal_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].address[0].postalCode
        (legacy CSV field name: PERSON_POSTCODE) exists, then it is a non-empty string,
        separated into two parts by a single space
        """

        try:
            patient_address_postal_code = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0][
                "address"
            ][0]["postalCode"]
            PreValidation.for_string(
                patient_address_postal_code,
                "contained[?(@.resourceType=='Patient')].address[0].postalCode",
                is_postal_code=True,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_occurrence_date_time(cls, values: dict) -> dict:
        """
        Pre-validate that, if occurrenceDateTime exists (legacy CSV field name: DATE_AND_TIME),
        then it is a string in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or "YYYY-MM-DDThh:mm:ss-zz:zz"
        (i.e. date and time, including timezone offset in hours and minutes), representing a valid
        datetime. Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00)."

        NOTE: occurrenceDateTime is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """
        try:
            occurrence_date_time = values["occurrenceDateTime"]
            PreValidation.for_date_time(occurrence_date_time, "occurrenceDateTime")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_questionnaire_response_item(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')].item exists,
        then each linkId is unique
        """
        try:
            questionnaire_response_item = [
                x for x in values["contained"] if x.get("resourceType") == "QuestionnaireResponse"
            ][0]["item"]

            PreValidation.for_unique_list(
                questionnaire_response_item,
                "linkId",
                "contained[?(@.resourceType=='QuestionnaireResponse')]" + ".item[?(@.linkId=='FIELD_TO_REPLACE')]",
            )

        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_questionnaire_answers(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each
        contained[?(@.resourceType=='QuestionnaireResponse')].item[index].answer
        is a list of length 1
        """
        try:
            questionnaire_items = [x for x in values["contained"] if x.get("resourceType") == "QuestionnaireResponse"][
                0
            ]["item"]
            for index, value in enumerate(questionnaire_items):
                try:
                    questionnaire_answer = value["answer"]
                    PreValidation.for_list(
                        questionnaire_answer,
                        "contained[?(@.resourceType=='QuestionnaireResponse')]" + f".item[{index}].answer",
                        defined_length=1,
                    )
                except KeyError:
                    pass
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_performer_actor_type(cls, values: dict) -> dict:
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

        return values

    @classmethod
    def pre_validate_performer_actor_reference(cls, values: dict) -> dict:
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
                "performer.actor.reference must be a single reference to a "
                + "contained Practitioner resource. References found: "
                + f"{performer_actor_internal_references}"
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

        return values

    @classmethod
    def pre_validate_organization_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if performer[?(@.actor.type=='Organization').identifier.value]
        (legacy CSV field name: SITE_CODE) exists, then it is a non-empty string
        """
        try:
            organization_identifier_value = [
                x for x in values["performer"] if x.get("actor").get("type") == "Organization"
            ][0]["actor"]["identifier"]["value"]
            PreValidation.for_string(
                organization_identifier_value,
                "performer[?(@.actor.type=='Organization')].actor.identifier.value",
            )
        except (KeyError, IndexError, AttributeError):
            pass

        return values

    @classmethod
    def pre_validate_organization_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if performer[?@.actor.type == 'Organization'].actor.display
        (legacy CSV field name: SITE_NAME) exists, then it is a non-empty string
        """
        try:
            organization_display = [x for x in values["performer"] if x.get("actor").get("type") == "Organization"][0][
                "actor"
            ]["display"]
            PreValidation.for_string(
                organization_display,
                "performer[?@.actor.type == 'Organization'].actor.display",
            )
        except (KeyError, IndexError, AttributeError):
            pass

        return values

    @classmethod
    def pre_validate_identifier(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier exists, then it is a list of length 1
        """
        try:
            identifier = values["identifier"]
            PreValidation.for_list(identifier, "identifier", defined_length=1)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0].value (legacy CSV field name: UNIQUE_ID) exists,
        then it is a non-empty string
        """
        try:
            identifier_value = values["identifier"][0]["value"]
            PreValidation.for_string(identifier_value, "identifier[0].value")
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_identifier_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if identifier[0].system (legacy CSV field name: UNIQUE_ID_URI) exists,
        then it is a non-empty string
        """
        try:
            identifier_system = values["identifier"][0]["system"]
            PreValidation.for_string(identifier_system, "identifier[0].system")
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_status(cls, values: dict) -> dict:
        """
        Pre-validate that, if status (legacy CSV field names ACTION_FLAG or NOT_GIVEN) exists,
        then it is a non-empty string which is one of the following: completed, entered-in-error,
        not-done.

        NOTE 1: ACTION_FLAG and NOT_GIVEN are mutually exclusive i.e. if ACTION_FLAG is present then
        NOT_GIVEN will be absent and vice versa. The ACTION_FLAGs are 'completed' and 'not-done'.
        The following 1-to-1 mapping applies:
        * NOT_GIVEN is True <---> Status will be set to 'not-done' (and therefore ACTION_FLAG is
            absent)
        * NOT_GIVEN is False <---> Status will be set to 'completed' or 'entered-in-error' (and
            therefore ACTION_FLAG is present)

        NOTE 2: Status is a mandatory FHIR field. A value of None will be rejected by the
        FHIR model before pre-validators are run.
        """
        try:
            status = values["status"]
            PreValidation.for_string(status, "status", predefined_values=Constants.STATUSES)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_practitioner_name(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].name exists,
        then it is an array of length 1
        """
        try:
            practitioner_name = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0]["name"]
            PreValidation.for_list(
                practitioner_name,
                "contained[?(@.resourceType=='Practitioner')].name",
                defined_length=1,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_practitioner_name_given(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].name[0].given
        (legacy CSV field name: PERSON_FORENAME) exists, then it is a
        an array containing a single non-empty string
        """
        try:
            practitioner_name_given = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0][
                "name"
            ][0]["given"]
            PreValidation.for_list(
                practitioner_name_given,
                "contained[?(@.resourceType=='Practitioner')].name[0].given",
                defined_length=1,
                elements_are_strings=True,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_practitioner_name_family(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].name[0].family
        (legacy CSV field name: PERSON_SURNAME) exists, then it is a
        an array containing a single non-empty string
        """
        try:
            practitioner_name_family = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0][
                "name"
            ][0]["family"]
            PreValidation.for_string(
                practitioner_name_family,
                "contained[?(@.resourceType=='Practitioner')].name[0].family",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_practitioner_identifier(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].identifier exists,
        then it is a list of length 1
        """
        try:
            practitioner_identifier = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][0][
                "identifier"
            ]
            PreValidation.for_list(
                practitioner_identifier,
                "contained[?(@.resourceType=='Practitioner')].identifier",
                defined_length=1,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_practitioner_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].identifier[0].value
        (legacy CSV field name: PERFORMING_PROFESSIONAL_BODY_REG_CODE) exists, then it is a
        non-empty string
        """
        try:
            practitioner_identifier_value = [x for x in values["contained"] if x.get("resourceType") == "Practitioner"][
                0
            ]["identifier"][0]["value"]
            PreValidation.for_string(
                practitioner_identifier_value,
                "contained[?(@.resourceType=='Practitioner')].identifier[0].value",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_practitioner_identifier_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Practitioner')].identifier[0].system
        (legacy CSV field name: PERFORMING_PROFESSIONAL_BODY_REG_URI) exists, then it is a
        non-empty string
        """
        try:
            practitioner_identifier_system = [
                x for x in values["contained"] if x.get("resourceType") == "Practitioner"
            ][0]["identifier"][0]["system"]
            PreValidation.for_string(
                practitioner_identifier_system,
                "contained[?(@.resourceType=='Practitioner')].identifier[0].system",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_performer_sds_job_role(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='PerformerSDSJobRole')].answer[0].valueString (legacy CSV field name:
        SDS_JOB_ROLE_NAME) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueString"
            ip_address_code = get_generic_questionnaire_response_value(
                values, "PerformerSDSJobRole", answer_type=answer_type
            )
            PreValidation.for_string(
                ip_address_code,
                generate_field_location_for_questionnnaire_response(
                    link_id="PerformerSDSJobRole", answer_type=answer_type
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_recorded(cls, values: dict) -> dict:
        """
        Pre-validate that, if recorded (legacy CSV field name: RECORDED_DATE) exists, then it is a
        string in the format YYYY-MM-DD, representing a valid date
        """
        try:
            recorded = values["recorded"]
            PreValidation.for_date(recorded, "recorded")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_primary_source(cls, values: dict) -> dict:
        """
        Pre-validate that, if primarySource (legacy CSV field name: PRIMARY_SOURCE) exists,
        then it is a boolean
        """
        try:
            primary_source = values["primarySource"]
            PreValidation.for_boolean(primary_source, "primarySource")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_report_origin_text(cls, values: dict) -> dict:
        """
        Pre-validate that, if reportOrigin.text (legacy CSV field name: REPORT_ORIGIN_TEXT)
        exists, then it is a non-empty string with maximum length 100 characters
        """
        try:
            report_origin_text = values["reportOrigin"]["text"]

            PreValidation.for_string(report_origin_text, "reportOrigin.text", max_length=100)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_extension_urls(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension exists, then each url is unique
        """
        try:
            PreValidation.for_unique_list(
                values["extension"],
                "url",
                "extension[?(@.url=='FIELD_TO_REPLACE')]",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_extension_value_codeable_concept_codings(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each extension[{index}].valueCodeableConcept.coding.system
        is unique
        """
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

        return values

    @classmethod
    def pre_validate_vaccination_procedure_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/
        Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system==
        'http://snomed.info/sct')].code
        (legacy CSV field name: VACCINATION_PROCEDURE_CODE) exists, then it is a non-empty string
        """
        try:
            url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "VaccinationProcedure"
            system = "http://snomed.info/sct"
            field_type = "code"
            vaccination_procedure_code = get_generic_extension_value(
                values,
                url,
                system,
                field_type,
            )
            PreValidation.for_string(
                vaccination_procedure_code,
                generate_field_location_for_extension(url, system, field_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_vaccination_procedure_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/
        Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system==
        'http://snomed.info/sct')].display
        (legacy CSV field name: VACCINATION_PROCEDURE_TERM) exists, then it is a non-empty string
        """
        try:
            url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "VaccinationProcedure"
            system = "http://snomed.info/sct"
            field_type = "display"
            vaccination_procedure_display = get_generic_extension_value(
                values,
                url,
                system,
                field_type,
            )
            PreValidation.for_string(
                vaccination_procedure_display,
                generate_field_location_for_extension(url, system, field_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_vaccination_situation_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/
        Extension-UKCore-VaccinationSituation')].valueCodeableConcept.coding[?(@.system==
        'http://snomed.info/sct')].code
        (legacy CSV field name: VACCINATION_SITUATION_CODE) exists, then it is a non-empty string
        """
        try:
            url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "VaccinationSituation"
            system = "http://snomed.info/sct"
            field_type = "code"
            vaccination_situation_code = get_generic_extension_value(values, url, system, field_type)
            PreValidation.for_string(
                vaccination_situation_code,
                generate_field_location_for_extension(url, system, field_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_vaccination_situation_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/
        Extension-UKCore-VaccinationSituation')].valueCodeableConcept.coding[?(@.system==
        'http://snomed.info/sct')].display
        (legacy CSV field name: VACCINATION_SITUATION_TERM) exists, then it is a non-empty string
        """
        try:
            url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "VaccinationSituation"
            system = "http://snomed.info/sct"
            field_type = "display"
            vaccination_situation_display = get_generic_extension_value(values, url, system, field_type)
            PreValidation.for_string(
                vaccination_situation_display,
                generate_field_location_for_extension(url, system, field_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_status_reason_coding(cls, values: dict) -> dict:
        """
        Pre-validate that, if statusReason.coding (legacy CSV field name: REASON_GIVEN_CODE)
        exists, then each coding system value is unique
        """
        try:
            coding = values["statusReason"]["coding"]

            PreValidation.for_unique_list(
                coding,
                "system",
                "statusReason.coding[?(@.system=='FIELD_TO_REPLACE')]",
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_status_reason_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if statusReason.coding[?(@.system==
        'http://snomed.info/sct')].code (legacy CSV field location:
        REASON_NOT_GIVEN_CODE) exists, then it is a non-empty string
        """
        try:
            status_reason_coding_code = [
                x for x in values["statusReason"]["coding"] if x.get("system") == "http://snomed.info/sct"
            ][0]["code"]
            PreValidation.for_string(
                status_reason_coding_code,
                "statusReason.coding[?(@.system=='http://snomed.info/sct')].code",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_status_reason_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if statusReason.coding[?(@.system==
        'http://snomed.info/sct')].display (legacy CSV field name:
        REASON_NOT_GIVEN_TERM) exists, then it is a non-empty string
        """
        try:
            status_reason_coding_display = [
                x for x in values["statusReason"]["coding"] if x.get("system") == "http://snomed.info/sct"
            ][0]["display"]
            PreValidation.for_string(
                status_reason_coding_display,
                "statusReason.coding[?(@.system=='http://snomed.info/sct')].display",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_protocol_applied(cls, values: dict) -> dict:
        """Pre-validate that, if protocolApplied exists, then it is a list of length 1"""
        try:
            protocol_applied = values["protocolApplied"]
            PreValidation.for_list(
                protocol_applied,
                "protocolApplied",
                defined_length=1,
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_protocol_applied_dose_number_positive_int(cls, values: dict) -> dict:
        """
        Pre-validate that, if protocolApplied[0].doseNumberPositiveInt (legacy CSV fidose_sequence)
        exists, then it is an integer from 1 to 9
        """
        try:
            protocol_applied_dose_number_positive_int = values["protocolApplied"][0]["doseNumberPositiveInt"]
            PreValidation.for_positive_integer(
                protocol_applied_dose_number_positive_int,
                "protocolApplied[0].doseNumberPositiveInt",
                max_value=9,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_vaccine_code_coding(cls, values: dict) -> dict:
        """Pre-validate that, if vaccineCode.coding exists, then each code system is unique"""
        try:
            vaccine_code_coding = values["vaccineCode"]["coding"]

            PreValidation.for_unique_list(
                vaccine_code_coding,
                "system",
                "vaccineCode.coding[?(@.system=='FIELD_TO_REPLACE')]",
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_vaccine_code_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if vaccineCode.coding[?(@.system==
        'http://snomed.info/sct')].code (legacy CSV field location:
        REASON_NOT_GIVEN_CODE) exists, then it is a non-empty string
        """
        try:
            status_reason_coding_code = [
                x for x in values["vaccineCode"]["coding"] if x.get("system") == "http://snomed.info/sct"
            ][0]["code"]
            PreValidation.for_string(
                status_reason_coding_code,
                "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_vaccine_code_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if vaccineCode.coding[?(@.system==
        'http://snomed.info/sct')].display (legacy CSV field name:
        REASON_NOT_GIVEN_TERM) exists, then it is a non-empty string
        """
        try:
            vaccine_code_coding_display = [
                x for x in values["vaccineCode"]["coding"] if x.get("system") == "http://snomed.info/sct"
            ][0]["display"]
            PreValidation.for_string(
                vaccine_code_coding_display,
                "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_manufacturer_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if manufacturer.display (legacy CSV field name: VACCINE_MANUFACTURER)
        exists, then it is a non-empty string
        """
        try:
            manufacturer_display = values["manufacturer"]["display"]
            PreValidation.for_string(manufacturer_display, "manufacturer.display")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_lot_number(cls, values: dict) -> dict:
        """
        Pre-validate that, if lotNumber (legacy CSV field name: BATCH_NUMBER) exists,
        then it is a non-empty string
        """
        try:
            lot_number = values["lotNumber"]
            PreValidation.for_string(lot_number, "lotNumber", max_length=100)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_expiration_date(cls, values: dict) -> dict:
        """
        Pre-validate that, if expirationDate (legacy CSV field name: EXPIRY_DATE) exists,
        then it is a string in the format YYYY-MM-DD, representing a valid date
        """
        try:
            expiration_date = values["expirationDate"]
            PreValidation.for_date(expiration_date, "expirationDate")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_site_coding(cls, values: dict) -> dict:
        """Pre-validate that, if site.coding exists, then each code system is unique"""
        try:
            coding = values["site"]["coding"]

            PreValidation.for_unique_list(
                coding,
                "system",
                "site.coding[?(@.system=='FIELD_TO_REPLACE')]",
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_site_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if site.coding[?(@.system=='http://snomed.info/sct')].code
        (legacy CSV field name: SITE_OF_VACCINATION_CODE) exists, then it is a non-empty string
        """
        try:
            site_coding_code = [x for x in values["site"]["coding"] if x.get("system") == "http://snomed.info/sct"][0][
                "code"
            ]
            PreValidation.for_string(
                site_coding_code,
                "site.coding[?(@.system=='http://snomed.info/sct')].code",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_site_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if site.coding[?(@.system=='http://snomed.info/sct')].display
        (legacy CSV field name: SITE_OF_VACCINATION_TERM) exists, then it is a non-empty string
        """
        try:
            site_coding_display = [x for x in values["site"]["coding"] if x.get("system") == "http://snomed.info/sct"][
                0
            ]["display"]

            PreValidation.for_string(
                site_coding_display,
                "site.coding[?(@.system=='http://snomed.info/sct')].display",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_route_coding(cls, values: dict) -> dict:
        """Pre-validate that, if route.coding exists, then each code system is unique"""
        try:
            coding = values["route"]["coding"]

            PreValidation.for_unique_list(
                coding,
                "system",
                "route.coding[?(@.system=='FIELD_TO_REPLACE')]",
            )
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_route_coding_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if route.coding[?(@.system=='http://snomed.info/sct')].code
        (legacy CSV field name: ROUTE_OF_VACCINATION_CODE) exists, then it is a non-empty string
        """
        try:
            route_coding_code = [x for x in values["route"]["coding"] if x.get("system") == "http://snomed.info/sct"][
                0
            ]["code"]
            PreValidation.for_string(
                route_coding_code,
                "route.coding[?(@.system=='http://snomed.info/sct')].code",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_route_coding_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if route.coding[?(@.system=='http://snomed.info/sct')].display
        (legacy CSV field name: ROUTE_OF_VACCINATION_TERM) exists, then it is a non-empty string
        """
        try:
            route_coding_display = [
                x for x in values["route"]["coding"] if x.get("system") == "http://snomed.info/sct"
            ][0]["display"]

            PreValidation.for_string(
                route_coding_display,
                "route.coding[?(@.system=='http://snomed.info/sct')].display",
            )
        except (KeyError, IndexError):
            pass

        return values

    # TODO: need to validate that doseQuantity.system is "http://unitsofmeasure.org"?
    # Check with Martin

    @classmethod
    def pre_validate_dose_quantity_value(cls, values: dict) -> dict:
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
            dose_quantity_value = values["doseQuantity"]["value"]
            PreValidation.for_integer_or_decimal(dose_quantity_value, "doseQuantity.value", max_decimal_places=4)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_dose_quantity_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity.code (legacy CSV field name: DOSE_UNIT_CODE) exists,
        then it is a non-empty string
        """
        try:
            dose_quantity_code = values["doseQuantity"]["code"]
            PreValidation.for_string(dose_quantity_code, "doseQuantity.code")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_dose_quantity_unit(cls, values: dict) -> dict:
        """
        Pre-validate that, if doseQuantity.unit (legacy CSV field name: DOSE_UNIT_TERM) exists,
        then it is a non-empty string
        """
        try:
            dose_quantity_unit = values["doseQuantity"]["unit"]
            PreValidation.for_string(dose_quantity_unit, "doseQuantity.unit")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reason_code_codings(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[{index}].coding is a list of length 1
        """
        try:
            for index, value in enumerate(values["reasonCode"]):
                try:
                    reason_code_coding = value["coding"]
                    PreValidation.for_list(
                        reason_code_coding,
                        f"reasonCode[{index}].coding",
                        defined_length=1,
                    )
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reason_code_coding_codes(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[{index}].coding[0].code
        (legacy CSV field name: INDICATION_CODE) is a non-empty string
        """
        try:
            for index, value in enumerate(values["reasonCode"]):
                try:
                    reason_code_coding_code = value["coding"][0]["code"]
                    PreValidation.for_string(reason_code_coding_code, f"reasonCode[{index}].coding[0].code")
                except KeyError:
                    pass
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reason_code_coding_displays(cls, values: dict) -> dict:
        """
        Pre-validate that, if they exist, each reasonCode[{index}].coding[0].display
        (legacy CSV field name: INDICATION_TERM) is a non-empty string
        """
        try:
            for index, value in enumerate(values["reasonCode"]):
                try:
                    reason_code_coding_display = value["coding"][0]["display"]
                    PreValidation.for_string(
                        reason_code_coding_display,
                        f"reasonCode[{index}].coding[0].display",
                    )
                except KeyError:
                    pass
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_patient_identifier_extension(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].identifier
        [?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].extension exists, then each url is unique
        """
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]
            patient_extension = [
                x for x in patient_identifier if x.get("system") == "https://fhir.nhs.uk/Id/nhs-number"
            ][0]["extension"]

            PreValidation.for_unique_list(
                patient_extension,
                "url",
                "contained[?(@.resourceType=='Patient')].identifier"
                + "[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].extension[?(@.url=="
                + "'FIELD_TO_REPLACE')]",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_nhs_number_verification_status_coding(cls, values: dict) -> dict:
        """
        Pre-validate that, if "contained[?(@.resourceType=='Patient')].identifier
        [?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].extension[?(@.url==
        'https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-
        NHSNumberVerificationStatus')].valueCodeableConcept.coding exists, then each url is unique
        """
        try:
            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]

            patient_extension = [
                x for x in patient_identifier if x.get("system") == "https://fhir.nhs.uk/Id/nhs-number"
            ][0]["extension"]

            nhs_number_verification_status_coding = [
                x
                for x in patient_extension
                if x.get("url")
                == "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-" + "NHSNumberVerificationStatus"
            ][0]["valueCodeableConcept"]["coding"]

            PreValidation.for_unique_list(
                nhs_number_verification_status_coding,
                "system",
                "contained[?(@.resourceType=='Patient')].identifier"
                + "[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].extension[?(@.url=="
                + "'https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-"
                + "NHSNumberVerificationStatus')].valueCodeableConcept.coding"
                + "[?(@.system=='FIELD_TO_REPLACE')]",
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_nhs_number_verification_status_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].extension[?(@.url==
        'https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus')]
        .valueCodeableConcept.coding[0].code (legacy CSV field name:
        NHS_NUMBER_STATUS_INDICATOR_CODE) exists, then it is a non-empty string
        """
        try:
            url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-" + "UKCore-NHSNumberVerificationStatus"
            system = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
            field_type = "code"

            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]

            patient_identifier_extension_item = [
                x for x in patient_identifier if x.get("system") == "https://fhir.nhs.uk/Id/nhs-number"
            ][0]

            nhs_number_verification_status_code = get_generic_extension_value(
                patient_identifier_extension_item, url, system, field_type
            )

            field_location = (
                "contained[?(@.resourceType=='Patient')].identifier"
                + "[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
                + generate_field_location_for_extension(url, system, field_type)
            )

            PreValidation.for_string(
                nhs_number_verification_status_code,
                field_location,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_nhs_number_verification_status_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='Patient')].extension[?(@.url==
        'https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus')]
        .valueCodeableConcept.coding[0].display (legacy CSV field name:
        NHS_NUMBER_STATUS_INDICATOR_DESCRIPTION) exists, then it is a non-empty string
        """
        try:
            url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-" + "UKCore-NHSNumberVerificationStatus"
            system = "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland"
            field_type = "display"

            patient_identifier = [x for x in values["contained"] if x.get("resourceType") == "Patient"][0]["identifier"]

            patient_identifier_extension_item = [
                x for x in patient_identifier if x.get("system") == "https://fhir.nhs.uk/Id/nhs-number"
            ][0]

            nhs_number_verification_status_display = get_generic_extension_value(
                patient_identifier_extension_item, url, system, field_type
            )

            field_location = (
                "contained[?(@.resourceType=='Patient')].identifier"
                + "[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
                + generate_field_location_for_extension(url, system, field_type)
            )

            PreValidation.for_string(
                nhs_number_verification_status_display,
                field_location,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_organization_identifier_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if performer[?(@.actor.type=='Organization').identifier.system]
        (legacy CSV field name: SITE_CODE_TYPE_URI) exists, then it is a non-empty string
        """
        try:
            organization_identifier_system = [
                x for x in values["performer"] if x.get("actor").get("type") == "Organization"
            ][0]["actor"]["identifier"]["system"]
            PreValidation.for_string(
                organization_identifier_system,
                "performer[?(@.actor.type=='Organization')].actor.identifier.system",
            )
        except (KeyError, IndexError, AttributeError):
            pass

        return values

    @classmethod
    def pre_validate_local_patient_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='LocalPatient')].valueReference.identifier.value (legacy CSV field name:
        LOCAL_PATIENT_ID) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueReference"
            local_patient_value = get_generic_questionnaire_response_value(
                values,
                "LocalPatient",
                answer_type=answer_type,
                field_type="value",
            )
            PreValidation.for_string(
                local_patient_value,
                generate_field_location_for_questionnnaire_response(
                    link_id="LocalPatient", answer_type=answer_type, field_type="value"
                ),
                max_length=20,
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_local_patient_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='LocalPatient')].valueReference.identifier.system (legacy CSV field name:
        LOCAL_PATIENT_URI) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueReference"
            local_patient_system = get_generic_questionnaire_response_value(
                values,
                "LocalPatient",
                answer_type=answer_type,
                field_type="system",
            )
            PreValidation.for_string(
                local_patient_system,
                generate_field_location_for_questionnnaire_response(
                    link_id="LocalPatient", answer_type=answer_type, field_type="system"
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_consent_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='Consent')].answer[0].valueCoding.code (legacy CSV field name:
        CONSENT_FOR_TREATMENT_CODE) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueCoding"
            consent_code = get_generic_questionnaire_response_value(
                values,
                "Consent",
                answer_type=answer_type,
                field_type="code",
            )
            PreValidation.for_string(
                consent_code,
                generate_field_location_for_questionnnaire_response(
                    link_id="Consent", answer_type=answer_type, field_type="code"
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_consent_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='Consent')].answer[0].valueCoding.display (legacy CSV field name:
        CONSENT_FOR_TREATMENT_DESCRIPTION) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueCoding"
            consent_display = get_generic_questionnaire_response_value(
                values,
                "Consent",
                answer_type=answer_type,
                field_type="display",
            )
            PreValidation.for_string(
                consent_display,
                generate_field_location_for_questionnnaire_response(
                    link_id="Consent", answer_type=answer_type, field_type="display"
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_care_setting_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='CareSetting')].answer[0].valueCoding.code (legacy CSV field name:
        CARE_SETTING_TYPE_CODE) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueCoding"
            care_setting_code = get_generic_questionnaire_response_value(
                values,
                "CareSetting",
                answer_type=answer_type,
                field_type="code",
            )
            PreValidation.for_string(
                care_setting_code,
                generate_field_location_for_questionnnaire_response(
                    link_id="CareSetting", answer_type=answer_type, field_type="code"
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_care_setting_display(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='CareSetting')].answer[0].valueCoding.display (legacy CSV field name:
        CARE_SETTING_TYPE_DESCRIPTION) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueCoding"
            care_setting_display = get_generic_questionnaire_response_value(
                values,
                "CareSetting",
                answer_type=answer_type,
                field_type="display",
            )
            PreValidation.for_string(
                care_setting_display,
                generate_field_location_for_questionnnaire_response(
                    link_id="CareSetting", answer_type=answer_type, field_type="display"
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_ip_address(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='IpAddress')].answer[0].valueString (legacy CSV field name:
        IP_ADDRESS) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueString"
            ip_address_code = get_generic_questionnaire_response_value(values, "IpAddress", answer_type=answer_type)
            PreValidation.for_string(
                ip_address_code,
                generate_field_location_for_questionnnaire_response(link_id="IpAddress", answer_type=answer_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_user_id(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='UserId')].answer[0].valueString (legacy CSV field name:
        USER_ID) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueString"
            user_id_code = get_generic_questionnaire_response_value(values, "UserId", answer_type=answer_type)
            PreValidation.for_string(
                user_id_code,
                generate_field_location_for_questionnnaire_response(link_id="UserId", answer_type=answer_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_user_name(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='UserName')].answer[0].valueString (legacy CSV field name:
        USER_NAME) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueString"
            user_name_code = get_generic_questionnaire_response_value(values, "UserName", answer_type=answer_type)
            PreValidation.for_string(
                user_name_code,
                generate_field_location_for_questionnnaire_response(link_id="UserName", answer_type=answer_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_user_email(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='UserEmail')].answer[0].valueString (legacy CSV field name:
        USER_EMAIL) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueString"
            user_email_code = get_generic_questionnaire_response_value(values, "UserEmail", answer_type=answer_type)
            PreValidation.for_string(
                user_email_code,
                generate_field_location_for_questionnnaire_response(link_id="UserEmail", answer_type=answer_type),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_submitted_time_stamp(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='SubmittedTimeStamp')].answer[0].valueDateTime (legacy CSV field name:
        SUBMITTED_TIMESTAMP), then it is a string in the format "YYYY-MM-DDThh:mm:ss+zz:zz" or
        "YYYY-MM-DDThh:mm:ss-zz:zz" (i.e. date and time, including timezone offset in hours and
        minutes), representing a valid datetime. Milliseconds are optional after the seconds
        (e.g. 2021-01-01T00:00:00.000+00:00).
        """
        try:
            answer_type = "valueDateTime"
            submitted_time_stamp_code = get_generic_questionnaire_response_value(
                values, "SubmittedTimeStamp", answer_type=answer_type
            )
            PreValidation.for_date_time(
                submitted_time_stamp_code,
                generate_field_location_for_questionnnaire_response(
                    link_id="SubmittedTimeStamp", answer_type=answer_type
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_location_identifier_value(cls, values: dict) -> dict:
        """
        Pre-validate that, if location.identifier.value (legacy CSV field name: LOCATION_CODE)
        exists, then it is a non-empty string
        """
        try:
            location_identifier_value = values["location"]["identifier"]["value"]
            PreValidation.for_string(location_identifier_value, "location.identifier.value")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_location_identifier_system(cls, values: dict) -> dict:
        """
        Pre-validate that, if location.identifier.system (legacy CSV field name:
        LOCATION_CODE_TYPE_URI) exists, then it is a non-empty string
        """
        try:
            location_identifier_system = values["location"]["identifier"]["system"]
            PreValidation.for_string(location_identifier_system, "location.identifier.system")
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_reduce_validation(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='ReduceValidation')].answer[0].valueBoolean (legacy CSV field name:
        REDUCE_VALIDATION_CODE) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueBoolean"
            reduce_validation_code = get_generic_questionnaire_response_value(
                values, "ReduceValidation", answer_type=answer_type
            )
            PreValidation.for_boolean(
                reduce_validation_code,
                generate_field_location_for_questionnnaire_response(
                    link_id="ReduceValidation", answer_type=answer_type
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

    @classmethod
    def pre_validate_reduce_validation_reason(cls, values: dict) -> dict:
        """
        Pre-validate that, if contained[?(@.resourceType=='QuestionnaireResponse')]
        .item[?(@.linkId=='ReduceValidationReason')].answer[0].valueString" (legacy CSV field name:
        REDUCE_VALIDATION_REASON) exists, then it is a non-empty string
        """
        try:
            answer_type = "valueString"
            reduce_validation_display = get_generic_questionnaire_response_value(
                values, "ReduceValidationReason", answer_type=answer_type
            )
            PreValidation.for_string(
                reduce_validation_display,
                generate_field_location_for_questionnnaire_response(
                    link_id="ReduceValidationReason",
                    answer_type=answer_type,
                ),
            )
        except (KeyError, IndexError):
            pass

        return values

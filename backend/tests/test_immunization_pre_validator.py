# """Test immunization pre validation rules on the model"""

# import unittest
# from copy import deepcopy
# from decimal import Decimal
# from jsonpath_ng.ext import parse

# from src.models.fhir_immunization import ImmunizationValidator
# from src.mappings import DiseaseCodes
# from .utils.generic_utils import (
#     # these have an underscore to avoid pytest collecting them as tests
#     test_valid_values_accepted as _test_valid_values_accepted,
#     test_invalid_values_rejected as _test_invalid_values_rejected,
#     load_json_data,
# )
# from .utils.pre_validation_test_utils import ValidatorModelTests
# from .utils.values_for_tests import ValidValues, InvalidValues


# class TestImmunizationModelPreValidationRules(unittest.TestCase):
#     """Test immunization pre validation rules on the FHIR model using the covid sample data"""

#     def setUp(self):
#         """Set up for each test. This runs before every test"""
#         self.json_data = load_json_data(filename="completed_covid19_immunization_event.json")
#         self.validator = ImmunizationValidator(add_post_validators=False)

#     def test_collected_errors(self):
#         """Test that when passed multiple validation errors, it returns a list of all expected errors."""

#         covid_data = deepcopy(self.json_data)

#         # remove identifier[0].value from 'contained' resource
#         covid_data["contained"][0]["identifier"][0]["value"] = None

#         # remove identifier[0].coding[0].code from 'Patient' resource
#         for resource in covid_data["contained"]:
#             if resource["resourceType"] == "Patient":
#                 resource["identifier"][0]["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = None

#         # remove coding.code from 'reasonCode'
#         covid_data["reasonCode"][0]["coding"][0]["code"] = None

#         expected_errors = [
#             "Validation errors: contained[?(@.resourceType=='Practitioner')].identifier[0].value must be a string",
#             "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
#             + "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerification"
#             + "Status')].valueCodeableConcept.coding[?(@.system=="
#             + "'https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland')].code must be a string",
#             "reasonCode[0].coding[0].code must be a string",
#         ]

#         # assert ValueError raised
#         with self.assertRaises(ValueError) as cm:
#             self.validator.validate(covid_data)

#         # extract the error messages from the exception
#         actual_errors = str(cm.exception).split("; ")

#         # assert length of errors
#         assert len(actual_errors) == len(expected_errors)

#         # assert the error is in the expected error messages
#         for error in actual_errors:
#             assert error in expected_errors

#     def test_pre_validate_contained(self):
#         """Test pre_validate_contained accepts valid values and rejects invalid values"""
#         # Test that the contained field is rejected when invalid
#         valid_list_to_test = [
#             ValidValues.empty_practitioner_resource_id_Pract1,
#             ValidValues.empty_patient_resource_id_Pat1,
#             ValidValues.empty_questionnnaire_resource_id_QR1,
#         ]

#         invalid_list_to_test = [
#             ValidValues.empty_practitioner_resource_id_Pract1,
#             ValidValues.empty_patient_resource_id_Pat1,
#             ValidValues.empty_questionnnaire_resource_id_QR1,
#             ValidValues.empty_patient_resource_id_Pat2,
#         ]

#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="contained",
#             valid_lists_to_test=[valid_list_to_test],
#             invalid_list_with_duplicates_to_test=invalid_list_to_test,
#             expected_error_message="contained[?(@.resourceType=='Patient')] must be unique",
#         )

#     def test_pre_validate_patient_reference(self):
#         """Test pre_validate_patient_reference accepts valid values and rejects invalid values"""
#         valid_contained_with_patient = [
#             ValidValues.empty_patient_resource_id_Pat1,
#             ValidValues.empty_practitioner_resource_id_Pract1,
#         ]

#         invalid_contained_with_no_id_in_patient = [
#             {"resourceType": "Patient"},
#             ValidValues.empty_practitioner_resource_id_Pract1,
#         ]

#         invalid_contained_with_no_patient = [ValidValues.empty_practitioner_resource_id_Pract1]

#         valid_patient_pat1 = {"reference": "#Pat1"}
#         valid_patient_pat2 = {"reference": "#Pat2"}
#         invalid_patient_pat1 = {"reference": "Pat1"}

#         # Test case: Pat1 in contained, patient reference is #Pat1 - accept
#         ValidatorModelTests.test_valid_combinations_of_contained_and_patient_accepted(
#             self, valid_contained_with_patient, valid_patient_pat1
#         )

#         # Test case: Pat1 in contained, patient reference is Pat1 - reject
#         ValidatorModelTests.test_invalid_patient_reference_rejected(
#             self,
#             valid_contained_with_patient,
#             invalid_patient_pat1,
#             expected_error_message="patient.reference must be a single reference to a contained Patient resource",
#         )

#         # Test case: Pat1 in contained, patient reference is #Pat2 - reject
#         ValidatorModelTests.test_invalid_patient_reference_rejected(
#             self,
#             valid_contained_with_patient,
#             valid_patient_pat2,
#             expected_error_message="The reference '#Pat2' does not exist in the contained Patient resource",
#         )
#         # Test case: contained Patient has no id, patient reference is #Pat1 - reject
#         ValidatorModelTests.test_invalid_patient_reference_rejected(
#             self,
#             invalid_contained_with_no_id_in_patient,
#             valid_patient_pat1,
#             expected_error_message="The contained Patient resource must have an 'id' field",
#         )

#         # Test case: no contained patient, patient reference is #Pat1 - reject
#         ValidatorModelTests.test_invalid_patient_reference_rejected(
#             self,
#             invalid_contained_with_no_patient,
#             valid_patient_pat1,
#             expected_error_message="contained[?(@.resourceType=='Patient')] is mandatory",
#         )

#     def test_pre_validate_patient_identifier(self):
#         """Test pre_validate_patient_identifier accepts valid values and rejects invalid values"""
#         valid_list_element = {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9000000009"}
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].identifier",
#             valid_lists_to_test=[[valid_list_element]],
#             predefined_list_length=1,
#             valid_list_element=valid_list_element,
#         )

#     def test_pre_validate_patient_identifier_value(self):
#         """Test pre_validate_patient_identifier_value accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].identifier[0].value",
#             valid_strings_to_test=["9990548609"],
#             defined_length=10,
#             invalid_length_strings_to_test=["999054860", "99905486091", ""],
#             spaces_allowed=False,
#             invalid_strings_with_spaces_to_test=["99905 8609", " 990548609", "999054860 ", "9990  8609"],
#         )

#     def test_pre_validate_patient_name(self):
#         """Test pre_validate_patient_name accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].name",
#             valid_lists_to_test=[[{"family": "Test"}]],
#             predefined_list_length=1,
#             valid_list_element={"family": "Test"},
#         )

#     def test_pre_validate_patient_name_given(self):
#         """Test pre_validate_patient_name_given accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].name[0].given",
#             valid_lists_to_test=[["Test"], ["Test test"]],
#             predefined_list_length=1,
#             valid_list_element="Test",
#             is_list_of_strings=True,
#         )

#     def test_pre_validate_patient_name_family(self):
#         """Test pre_validate_patient_name_family accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].name[0].family",
#             valid_strings_to_test=["test"],
#         )

#     def test_pre_validate_patient_birth_date(self):
#         """Test pre_validate_patient_birth_date accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_date_value(self, field_location="contained[?(@.resourceType=='Patient')].birthDate")

#     def test_pre_validate_patient_gender(self):
#         """Test pre_validate_patient_gender accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].gender",
#             valid_strings_to_test=["male", "female", "other", "unknown"],
#             predefined_values=("male", "female", "other", "unknown"),
#             invalid_strings_to_test=InvalidValues.for_genders,
#         )

#     def test_pre_validate_patient_address(self):
#         """Test pre_validate_patient_address accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].address",
#             valid_lists_to_test=[[{"postalCode": "AA1 1AA"}]],
#             predefined_list_length=1,
#             valid_list_element={"family": "Test"},
#         )

#     def test_pre_validate_patient_address_postal_code(self):
#         """Test pre_validate_patient_address_postal_code accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='Patient')].address[0].postalCode",
#             valid_strings_to_test=["AA00 00AA", "A0 0AA"],
#             is_postal_code=True,
#         )

#     def test_pre_validate_occurrence_date_time(self):
#         """Test pre_validate_occurrence_date_time accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_date_time_value(
#             self, field_location="occurrenceDateTime", is_occurrence_date_time=True
#         )

#     def test_pre_validate_valid_questionnaire_answers(self):
#         """Test pre_validate_quesionnaire_answers accepts valid values and rejects invalid values"""
#         # Check that any of the answer fields in the sample data are rejected when invalid
#         for i in range(len(self.json_data["contained"][2]["item"])):
#             # Determine what valid list element looks like
#             answer_keys = self.json_data["contained"][2]["item"][i]["answer"][0].keys()
#             if "valueCoding" in answer_keys:
#                 valid_list_element = {"valueCoding": {"code": "True"}}
#             elif "valueBoolean" in answer_keys:
#                 valid_list_element = {"valueBoolean": True}
#             elif "valueString" in answer_keys:
#                 valid_list_element = {"valueString": "test_string"}
#             elif "valueDateTime" in answer_keys:
#                 valid_list_element = {"valueDateTime": "2021-02-07T13:44:07+00:00"}
#             elif "valueReference" in answer_keys:
#                 valid_list_element = {"valueReference": {"reference": "#"}}

#             ValidatorModelTests.test_list_value(
#                 self,
#                 field_location="contained[?(@.resourceType=='QuestionnaireResponse')]" + f".item[{i}].answer",
#                 valid_lists_to_test=[[valid_list_element]],
#                 predefined_list_length=1,
#                 valid_list_element=valid_list_element,
#             )

#     def test_pre_validate_questionnaire_response_item(self):
#         """Test pre_validate_questionnaire_response_item accepts valid values and rejects invalid values"""
#         # Test that the contained field is rejected when invalid
#         valid_list_to_test = [
#             ValidValues.questionnaire_immunisation,
#             ValidValues.questionnaire_reduce_validation_false,
#             ValidValues.questionnaire_ip_address,
#         ]

#         invalid_list_to_test = [
#             ValidValues.questionnaire_immunisation,
#             ValidValues.questionnaire_reduce_validation_false,
#             ValidValues.questionnaire_reduce_validation_true,
#             ValidValues.questionnaire_ip_address,
#         ]

#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')].item",
#             valid_lists_to_test=[valid_list_to_test],
#             invalid_list_with_duplicates_to_test=invalid_list_to_test,
#             expected_error_message="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='ReduceValidation')] must be unique",
#         )

#     def test_pre_validate_performer_actor_type(self):
#         """Test pre_validate_performer_actor_type accepts valid values and rejects invalid values"""
#         # Test that valid data is accepted
#         _test_valid_values_accepted(self, deepcopy(self.json_data), "performer", [ValidValues.performer])

#         # Test lists with duplicate values
#         _test_invalid_values_rejected(
#             self,
#             valid_json_data=deepcopy(self.json_data),
#             field_location="performer",
#             invalid_value=InvalidValues.performer_with_two_organizations,
#             expected_error_message="performer.actor[?@.type=='Organization'] must be unique",
#         )

#     def test_pre_validate_performer_actor_reference(self):
#         """Test pre_validate_performer_actor_reference accepts valid values and rejects invalid values"""

#         valid_contained_with_no_practitioner = [ValidValues.empty_patient_resource_id_Pat1]

#         valid_contained_with_practitioner = [
#             ValidValues.empty_practitioner_resource_id_Pract1,
#             ValidValues.empty_patient_resource_id_Pat1,
#         ]

#         invalid_contained_with_no_id_in_practitioner = [
#             InvalidValues.practitioner_resource_with_no_id,
#             ValidValues.empty_patient_resource_id_Pat1,
#         ]

#         valid_performer_with_one_pract1 = [
#             ValidValues.performer_actor_reference_internal_Pract1,
#             ValidValues.performer_actor_organization,
#         ]

#         valid_performer_with_no_actor_reference = [ValidValues.performer_actor_organization]

#         valid_performer_with_two_pract1 = [
#             ValidValues.performer_actor_reference_internal_Pract1,
#             ValidValues.performer_actor_reference_internal_Pract1,
#             ValidValues.performer_actor_organization,
#         ]

#         valid_performer_with_one_pract2 = [
#             ValidValues.performer_actor_reference_internal_Pract2,
#             ValidValues.performer_actor_organization,
#         ]

#         # Test case: Pract1 in contained, 1 actor of #Pract1 in performer - accept
#         ValidatorModelTests.test_valid_combinations_of_contained_and_performer_accepted(
#             self, valid_contained_with_practitioner, valid_performer_with_one_pract1
#         )

#         # Test case: No contained practitioner, no actor reference in performer - accept
#         ValidatorModelTests.test_valid_combinations_of_contained_and_performer_accepted(
#             self, valid_contained_with_no_practitioner, valid_performer_with_no_actor_reference
#         )

#         # Test case: Pract1 in contained, 2 actor of #Pract1 in performer - reject
#         ValidatorModelTests.test_invalid_performer_actor_reference_rejected(
#             self,
#             valid_contained_with_practitioner,
#             valid_performer_with_two_pract1,
#             expected_error_message="performer.actor.reference must be a single reference to a "
#             + "contained Practitioner resource. References found: ['#Pract1', '#Pract1']",
#         )

#         # Test case: No contained practitioner, 1 actor of #Pract1 in performer - reject
#         ValidatorModelTests.test_invalid_performer_actor_reference_rejected(
#             self,
#             valid_contained_with_no_practitioner,
#             valid_performer_with_one_pract1,
#             expected_error_message="The reference(s) ['#Pract1'] do not exist in the contained Practitioner resources",
#         )

#         # Test case: Contained practitioner with no ID, no actor reference in perfomer - reject
#         ValidatorModelTests.test_invalid_performer_actor_reference_rejected(
#             self,
#             invalid_contained_with_no_id_in_practitioner,
#             valid_performer_with_no_actor_reference,
#             expected_error_message="The contained Practitioner resource must have an 'id' field",
#         )

#         # Test case: Pract1 in contained, no actor reference in performer - reject
#         ValidatorModelTests.test_invalid_performer_actor_reference_rejected(
#             self,
#             valid_contained_with_practitioner,
#             valid_performer_with_no_actor_reference,
#             expected_error_message="contained Practitioner ID must be referenced by performer.actor.reference",
#         )

#         # Test case: Pract1 in contained, 1 actor of #Pract2 in performer - reject
#         ValidatorModelTests.test_invalid_performer_actor_reference_rejected(
#             self,
#             valid_contained_with_practitioner,
#             valid_performer_with_one_pract2,
#             expected_error_message="The reference '#Pract2' does not exist in the contained Practitioner resources",
#         )

#     def test_pre_validate_organization_identifier_value(self):
#         """Test pre_validate_organization_identifier_value accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="performer[?(@.actor.type=='Organization')].actor.identifier.value",
#             valid_strings_to_test=["B0C4P", "D3P5L"],
#             invalid_strings_to_test=["ABCDE", "R99TL"]
#         )
        
        

#     def test_pre_validate_organization_display(self):
#         """Test pre_validate_organization_display accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="performer[?@.actor.type == 'Organization'].actor.display",
#             valid_strings_to_test=["dummy"],
#         )

#     def test_pre_validate_identifier(self):
#         """Test pre_validate_identifier accepts valid values and rejects invalid values"""
#         valid_list_element = {"system": "https://supplierABC/identifiers/vacc", "value": "ACME-vacc123456"}
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="identifier",
#             valid_lists_to_test=[[valid_list_element]],
#             predefined_list_length=1,
#             valid_list_element=valid_list_element,
#         )

#     def test_pre_validate_identifier_value(self):
#         """Test pre_validate_identifier_value accepts valid values and rejects invalid values"""
#         valid_strings_to_test = ["e045626e-4dc5-4df3-bc35-da25263f901e", "ACME-vacc123456", "ACME-CUSTOMER1-vacc123456"]
#         ValidatorModelTests.test_string_value(
#             self, field_location="identifier[0].value", valid_strings_to_test=valid_strings_to_test
#         )

#     def test_pre_validate_identifier_system(self):
#         """Test pre_validate_identifier_system accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="identifier[0].system",
#             valid_strings_to_test=[
#                 "https://supplierABC/identifiers/vacc",
#                 "https://supplierABC/ODSCode_NKO41/identifiers/vacc",
#             ],
#         )

#     def test_pre_validate_status(self):
#         """Test pre_validate_status accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="status",
#             valid_strings_to_test=["completed", "entered-in-error", "not-done"],
#             predefined_values=("completed", "entered-in-error", "not-done"),
#             invalid_strings_to_test=["1", "complete", "enteredinerror"],
#             is_mandatory_fhir=True,
#         )

#     def test_pre_validate_practitioner_name(self):
#         """Test pre_validate_practitioner_name accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Practitioner')].name",
#             valid_lists_to_test=[[{"family": "Test"}]],
#             predefined_list_length=1,
#             valid_list_element={"family": "Test"},
#         )

#     def test_pre_validate_practitioner_name_given(self):
#         """Test pre_validate_practitioner_name_given accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Practitioner')].name[0].given",
#             valid_lists_to_test=[["Test"], ["Test test"]],
#             predefined_list_length=1,
#             valid_list_element="Test",
#             is_list_of_strings=True,
#         )

#     def test_pre_validate_practitioner_name_family(self):
#         """Test pre_validate_practitioner_name_family accepts valid values and rejects invalid values"""
#         field_location = "contained[?(@.resourceType=='Practitioner')].name[0].family"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["test"])

#     def test_pre_validate_practitioner_identifier(self):
#         """Test pre_validate_practitioner_identifier accepts valid values and rejects invalid values"""
#         valid_list_element = {"system": "https://supplierABC/identifiers/vacc", "value": "ACME-vacc123456"}
#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="contained[?(@.resourceType=='Practitioner')].identifier",
#             valid_lists_to_test=[[valid_list_element]],
#             predefined_list_length=1,
#             valid_list_element=valid_list_element,
#         )

#     def test_pre_validate_practitioner_identifier_value(self):
#         """Test pre_validate_practitioner_identifier_value accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='Practitioner')].identifier[0].value",
#             valid_strings_to_test=[
#                 "e045626e-4dc5-4df3-bc35-da25263f901e",
#                 "ACME-vacc123456",
#                 "ACME-CUSTOMER1-vacc123456",
#             ],
#         )

#     def test_pre_validate_practitioner_identifier_system(self):
#         """Test pre_validate_practitioner_identifier_system accepts valid values and rejects invalid values"""
#         valid_strings_to_test = [
#             "https://supplierABC/identifiers/vacc",
#             "https://supplierABC/ODSCode_NKO41/identifiers/vacc",
#         ]
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='Practitioner')].identifier[0].system",
#             valid_strings_to_test=valid_strings_to_test,
#         )

#     def test_pre_validate_performer_sds_job_role(self):
#         """Test pre_validate_performer_sds_job_role accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='PerformerSDSJobRole')].answer[0].valueString",
#             valid_strings_to_test=["Doctor"],
#         )

#     def test_pre_validate_recorded(self):
#         """Test pre_validate_recorded accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_date_value(self, field_location="recorded")

#     def test_pre_validate_primary_source(self):
#         """Test pre_validate_primary_source accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_boolean_value(self, field_location="primarySource")

#     def test_pre_validate_report_origin_text(self):
#         """Test pre_validate_report_origin_text accepts valid values and rejects invalid values"""
#         valid_strings_to_test = ["sample", "Free text description of organisation recording the event"]
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="reportOrigin.text",
#             valid_strings_to_test=valid_strings_to_test,
#             max_length=100,
#             invalid_length_strings_to_test=InvalidValues.for_strings_with_max_100_chars,
#         )

#     def test_pre_validate_extension_urls(self):
#         """Test pre_validate_extension_urls accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="extension",
#             valid_lists_to_test=[[ValidValues.vaccination_procedure_with_one_snomed_code]],
#             invalid_list_with_duplicates_to_test=[
#                 ValidValues.vaccination_procedure_with_one_snomed_code,
#                 ValidValues.vaccination_procedure_with_one_snomed_code,
#             ],
#             expected_error_message="extension[?(@.url=='https://fhir.hl7.org.uk"
#             + "/StructureDefinition/Extension-UKCore-VaccinationProcedure')] must be unique",
#         )

#     def test_pre_validate_extension_value_codeable_concept_codings(self):
#         """
#         Test pre_validate_extension_value_codeable_concept_codings accepts valid values and rejects
#         invalid values
#         """
#         valid_extension_value = [
#             ValidValues.vaccination_procedure_with_snomed_and_dmd_codes,
#             ValidValues.vaccination_situation_with_one_snomed_code,
#         ]

#         invalid_extension_value = [
#             ValidValues.vaccination_procedure_with_one_snomed_code,
#             InvalidValues.vaccination_situation_with_two_snomed_codes,
#         ]

#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="extension",
#             valid_lists_to_test=[valid_extension_value],
#             invalid_list_with_duplicates_to_test=invalid_extension_value,
#             expected_error_message="extension[?(@.URL=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-V"
#             + "accinationSituation'].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')] must be unique",
#         )

#     def test_pre_validate_vaccination_procedure_code(self):
#         """Test pre_validate_vaccination_procedure_code accepts valid values and rejects invalid values"""
#         field_location = (
#             "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')]"
#             + ".valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code"
#         )

#         ValidatorModelTests.test_string_value(self, field_location=field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_vaccination_procedure_display(self):
#         """Test pre_validate_vaccination_procedure_display accepts valid values and rejects invalid values"""
#         field_location = (
#             "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')]"
#             + ".valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display"
#         )
#         ValidatorModelTests.test_string_value(self, field_location=field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_protocol_applied(self):
#         """Test pre_validate_protocol_applied accepts valid values and rejects invalid values"""
#         valid_list_element = {
#             "targetDisease": [
#                 {"coding": [{"system": "http://snomed.info/sct", "code": "6142004", "display": "Influenza"}]}
#             ],
#             "doseNumberPositiveInt": 1,
#         }

#         ValidatorModelTests.test_list_value(
#             self,
#             field_location="protocolApplied",
#             valid_lists_to_test=[[valid_list_element]],
#             predefined_list_length=1,
#             valid_list_element=valid_list_element,
#         )

#     def test_pre_validate_protocol_applied_dose_number_positive_int(self):
#         """
#         Test pre_validate_protocol_applied_dose_number_positive_int accepts valid values and
#         rejects invalid values
#         """
#         ValidatorModelTests.test_positive_integer_value(
#             self,
#             field_location="protocolApplied[0].doseNumberPositiveInt",
#             valid_positive_integers_to_test=[1, 2, 3, 4, 5, 6, 7, 8, 9],
#             max_value=9,
#         )

#     def test_pre_validate_protocol_applied_dose_number_string(self):
#         """
#         Test pre_validate_protocol_applied_dose_number_string accepts valid values and
#         rejects invalid values
#         """
#         valid_json_data = deepcopy(self.json_data)
#         valid_json_data["protocolApplied"][0]["doseNumberString"] = "Dose sequence not recorded"
#         valid_json_data = parse("protocolApplied[0].doseNumberPositiveInt").filter(lambda d: True, valid_json_data)

#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="protocolApplied[0].doseNumberString",
#             valid_strings_to_test=["Dose sequence not recorded"],
#             valid_json_data=valid_json_data,
#             defined_length="",
#             invalid_strings_to_test=["Invalid"],
#         )

#     def test_pre_validate_target_disease(self):
#         """Test pre_validate_target_disease accepts valid values and rejects invalid values"""

#         valid_json_data = load_json_data(filename="completed_mmr_immunization_event.json")

#         self.assertTrue(self.validator.validate(valid_json_data))

#         invalid_target_disease = [
#             {"coding": [{"system": "http://snomed.info/sct", "code": "14189004", "display": "Measles"}]},
#             {"text": "a_disease"},
#             {"coding": [{"system": "http://snomed.info/sct", "code": "36653000", "display": "Rubella"}]},
#         ]

#         _test_invalid_values_rejected(
#             self,
#             valid_json_data,
#             field_location="protocolApplied[0].targetDisease",
#             invalid_value=invalid_target_disease,
#             expected_error_message="Every element of protocolApplied[0].targetDisease must have 'coding' property",
#         )

#     def test_pre_validate_target_disease_codings(self):
#         """Test pre_validate_target_disease_codings accepts valid values and rejects invalid values"""
#         valid_target_disease_values = [
#             [
#                 {
#                     "coding": [
#                         {"system": "http://snomed.info/sct", "code": "14189004", "display": "Measles"},
#                         {"system": "some_other_system", "code": "a_code", "display": "Measles"},
#                     ]
#                 },
#                 {"coding": [{"system": "http://snomed.info/sct", "code": "36989005", "display": "Mumps"}]},
#                 {"coding": [{"system": "http://snomed.info/sct", "code": "36653000", "display": "Rubella"}]},
#             ]
#         ]

#         invalid_target_disease_values = [
#             {
#                 "coding": [
#                     {"system": "http://snomed.info/sct", "code": "14189004", "display": "Measles"},
#                     {"system": "some_other_system", "code": "a_code", "display": "Measles"},
#                 ]
#             },
#             {
#                 "coding": [
#                     {"system": "http://snomed.info/sct", "code": "36989005", "display": "Mumps"},
#                     {"system": "http://snomed.info/sct", "code": "another_mumps_code", "display": "Mumps"},
#                 ]
#             },
#             {"coding": [{"system": "http://snomed.info/sct", "code": "36653000", "display": "Rubella"}]},
#         ]

#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="protocolApplied[0].targetDisease",
#             valid_lists_to_test=valid_target_disease_values,
#             invalid_list_with_duplicates_to_test=invalid_target_disease_values,
#             expected_error_message="protocolApplied[0].targetDisease[1].coding"
#             + "[?(@.system=='http://snomed.info/sct')] must be unique",
#         )

#     def test_pre_validate_disease_type_coding_codes(self):
#         """Test pre_validate_disease_type_coding_codes accepts valid values and rejects invalid values"""
#         # Test data with single disease_type_coding_code
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="protocolApplied[0].targetDisease[0]."
#             + "coding[?(@.system=='http://snomed.info/sct')].code",
#             valid_strings_to_test=[DiseaseCodes.covid_19, DiseaseCodes.flu, DiseaseCodes.hpv],
#             valid_json_data=load_json_data(filename="completed_covid19_immunization_event.json"),
#         )

#         # Test data with multiple disease_type_coding_codes
#         for i, disease_code in [(0, DiseaseCodes.measles), (1, DiseaseCodes.mumps), (2, DiseaseCodes.rubella)]:
#             ValidatorModelTests.test_string_value(
#                 self,
#                 field_location=f"protocolApplied[0].targetDisease[{i}]."
#                 + "coding[?(@.system=='http://snomed.info/sct')].code",
#                 valid_strings_to_test=[disease_code],
#                 valid_json_data=load_json_data(filename="completed_mmr_immunization_event.json"),
#             )

#     def test_pre_validate_vaccine_code_coding(self):
#         """Test pre_validate_vaccine_code_coding accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="vaccineCode.coding",
#             valid_lists_to_test=[[ValidValues.snomed_coding_element]],
#             invalid_list_with_duplicates_to_test=[
#                 ValidValues.snomed_coding_element,
#                 ValidValues.snomed_coding_element,
#             ],
#             expected_error_message="vaccineCode.coding[?(@.system=='http://snomed.info/sct')]" + " must be unique",
#         )

#     def test_pre_validate_vaccine_code_coding_code(self):
#         """Test pre_validate_vaccine_code_coding_code accepts valid values and rejects invalid values"""
#         field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_vaccine_code_coding_display(self):
#         """Test pre_validate_vaccine_code_coding_display accepts valid values and rejects invalid values"""
#         field_location = "vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_manufacturer_display(self):
#         """Test pre_validate_manufacturer_display accepts valid values and rejects invalid values"""
#         field_location = "manufacturer.display"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_lot_number(self):
#         """Test pre_validate_lot_number accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="lotNumber",
#             valid_strings_to_test=["sample", "0123456789101112"],
#             max_length=100,
#             invalid_length_strings_to_test=InvalidValues.for_strings_with_max_100_chars,
#         )

#     def test_pre_validate_expiration_date(self):
#         """Test pre_validate_expiration_date accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_date_value(self, field_location="expirationDate")

#     def test_pre_validate_site_coding(self):
#         """Test pre_validate_site_coding accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="site.coding",
#             valid_lists_to_test=[[ValidValues.snomed_coding_element]],
#             invalid_list_with_duplicates_to_test=[
#                 ValidValues.snomed_coding_element,
#                 ValidValues.snomed_coding_element,
#             ],
#             expected_error_message="site.coding[?(@.system=='http://snomed.info/sct')]" + " must be unique",
#         )

#     def test_pre_validate_site_coding_code(self):
#         """Test pre_validate_site_coding_code accepts valid values and rejects invalid values"""
#         field_location = "site.coding[?(@.system=='http://snomed.info/sct')].code"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_site_coding_display(self):
#         """Test pre_validate_site_coding_display accepts valid values and rejects invalid values"""
#         field_location = "site.coding[?(@.system=='http://snomed.info/sct')].display"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_route_coding(self):
#         """Test pre_validate_route_coding accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="route.coding",
#             valid_lists_to_test=[[ValidValues.snomed_coding_element]],
#             invalid_list_with_duplicates_to_test=[
#                 ValidValues.snomed_coding_element,
#                 ValidValues.snomed_coding_element,
#             ],
#             expected_error_message="route.coding[?(@.system=='http://snomed.info/sct')]" + " must be unique",
#         )

#     def test_pre_validate_route_coding_code(self):
#         """Test pre_validate_route_coding_code accepts valid values and rejects invalid values"""
#         field_location = "route.coding[?(@.system=='http://snomed.info/sct')].code"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_route_coding_display(self):
#         """Test pre_validate_route_coding_display accepts valid values and rejects invalid values"""
#         field_location = "route.coding[?(@.system=='http://snomed.info/sct')].display"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_dose_quantity_value(self):
#         """Test pre_validate_dose_quantity_value accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_decimal_or_integer_value(
#             self,
#             field_location="doseQuantity.value",
#             valid_decimals_and_integers_to_test=[
#                 1,  # small integer
#                 100,  # larger integer
#                 Decimal("1.0"),  # Only 0s after decimal point
#                 Decimal("0.1"),  # 1 decimal place
#                 Decimal("100.52"),  # 2 decimal places
#                 Decimal("32.430"),  # 3 decimal places
#                 Decimal("1.1234"),  # 4 decimal places,
#             ],
#             max_decimal_places=4,
#         )

#     def test_pre_validate_dose_quantity_code(self):
#         """Test pre_validate_dose_quantity_code accepts valid values and rejects invalid values"""
#         field_location = "doseQuantity.code"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["ABC123"])

#     def test_pre_validate_dose_quantity_unit(self):
#         """Test pre_validate_dose_quantity_unit accepts valid values and rejects invalid values"""
#         field_location = "doseQuantity.unit"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["Millilitre"])

#     # TODO: ?add extra reason code to sample data for validation testing
#     def test_pre_validate_reason_code_codings(self):
#         """Test pre_validate_reason_code_codings accepts valid values and rejects invalid values"""
#         # Check that both of the 2 reasonCode[{index}].coding fields in the sample data are rejected
#         # when invalid
#         for i in range(1):
#             ValidatorModelTests.test_list_value(
#                 self,
#                 field_location=f"reasonCode[{i}].coding",
#                 valid_lists_to_test=[[{"code": "ABC123", "display": "test"}]],
#                 predefined_list_length=1,
#                 valid_list_element={"code": "ABC123", "display": "test"},
#             )

#     # TODO: ?add extra reason code to sample data for validation testing
#     def test_pre_validate_reason_code_coding_codes(self):
#         """Test pre_validate_reason_code_coding_codes accepts valid values and rejects invalid values"""
#         # Check that both of the reasonCode[{index}].coding[0].code fields in the sample data are
#         # rejected when invalid
#         for i in range(1):
#             ValidatorModelTests.test_string_value(
#                 self, field_location=f"reasonCode[{i}].coding[0].code", valid_strings_to_test=["ABC123"]
#             )

#     # TODO: ?add extra reason code to sample data for validation testing
#     def test_pre_validate_reason_code_coding_displays(self):
#         """Test pre_validate_reason_code_coding_displays accepts valid values and rejects invalid values"""
#         # Check that both of the reasonCode[{index}].coding[0].display fields in the sample data are
#         # rejected when invalid
#         for i in range(1):
#             ValidatorModelTests.test_string_value(
#                 self, field_location=f"reasonCode[{i}].coding[0].display", valid_strings_to_test=["test"]
#             )

#     def test_pre_validate_patient_identifier_extension(self):
#         """Test pre_validate_patient_identifier_extension accepts valid values and rejects invalid values"""
#         field_location = (
#             "contained[?(@.resourceType=='Patient')].identifier"
#             + "[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')].extension"
#         )

#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location=field_location,
#             valid_lists_to_test=[[ValidValues.nhs_number_verification_status]],
#             invalid_list_with_duplicates_to_test=[
#                 ValidValues.nhs_number_verification_status,
#                 ValidValues.nhs_number_verification_status,
#             ],
#             expected_error_message=f"{field_location}[?(@.url=='https://fhir.hl7.org.uk"
#             + "/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus')] must be unique",
#         )

#     def test_pre_validate_nhs_number_verification_status_coding(self):
#         """Test pre_validate_nhs_number_verification_status_coding accepts valid values and rejects invalid values"""
#         field_location = (
#             "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
#             + "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-"
#             + "NHSNumberVerificationStatus')].valueCodeableConcept.coding"
#         )

#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location=field_location,
#             valid_lists_to_test=[[ValidValues.nhs_number_coding_item]],
#             invalid_list_with_duplicates_to_test=[
#                 ValidValues.nhs_number_coding_item,
#                 ValidValues.nhs_number_coding_item,
#             ],
#             expected_error_message=f"{field_location}[?(@.system=='https://fhir.hl7.org.uk"
#             + "/CodeSystem/UKCore-NHSNumberVerificationStatusEngland')] must be unique",
#         )

#     def test_pre_validate_nhs_number_verification_status_code(self):
#         """Test pre_validate_nhs_number_verification_status_code accepts valid values and rejects invalid values"""
#         field_location = (
#             "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
#             + "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/"
#             + "Extension-UKCore-NHSNumberVerificationStatus')].valueCodeableConcept.coding[?(@.system=="
#             + "'https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland')].code"
#         )

#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["01"])

#     def test_pre_validate_nhs_number_verification_status_display(self):
#         """Test pre_validate_nhs_number_verification_status_display accepts valid values and rejects invalid values"""
#         field_location = (
#             "contained[?(@.resourceType=='Patient')].identifier[?(@.system=='https://fhir.nhs.uk/Id/nhs-number')]."
#             + "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/"
#             + "Extension-UKCore-NHSNumberVerificationStatus')].valueCodeableConcept.coding[?(@.system=="
#             + "'https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland')].display"
#         )

#         ValidatorModelTests.test_string_value(
#             self, field_location, valid_strings_to_test=["Number present and verified"]
#         )

#     def test_pre_validate_organisation_identifier_system(self):
#         """Test pre_validate_organization_identifier_system accepts valid systems and rejects invalid systems"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="performer[?(@.actor.type=='Organization')].actor.identifier.system",
#             valid_strings_to_test=["DUMMY"],
#         )

#     def test_pre_validate_local_patient_value(self):
#         """Test pre_validate_local_patient_value accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='LocalPatient')].answer[0].valueReference.identifier.value",
#             valid_strings_to_test=["ACME-patient123456", "ACME-CUST1-pat123456", "ACME-CUST2-pat123456"],
#             invalid_length_strings_to_test=["ACME-CUST1-pat1234567"],
#             max_length=20,
#         )

#     def test_pre_validate_local_patient_system(self):
#         """Test pre_validate_local_patient_system accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='LocalPatient')].answer[0].valueReference.identifier.system",
#             valid_strings_to_test=["https://supplierABC/identifiers"],
#         )

#     def test_pre_validate_consent_code(self):
#         """Test pre_validate_consent_code accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='Consent')].answer[0].valueCoding.code",
#             valid_strings_to_test=["snomed"],
#         )

#     def test_pre_validate_consent_display(self):
#         """Test pre_validate_consent_display accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='Consent')].answer[0].valueCoding.display",
#             valid_strings_to_test=[
#                 "Patient consented to be given the vaccination",
#                 "Parent/carer/guardian consented for child to be given the vaccination",
#             ],
#         )

#     def test_pre_validate_care_setting_code(self):
#         """Test pre_validate_care_setting_code accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='CareSetting')].answer[0].valueCoding.code",
#             valid_strings_to_test=["snomed"],
#         )

#     def test_pre_validate_care_setting_display(self):
#         """Test pre_validate_care_setting_display accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='CareSetting')].answer[0].valueCoding.display",
#             valid_strings_to_test=["SNOMED-CT Term description Community health services (qualifier value)"],
#         )

#     def test_pre_validate_ip_address(self):
#         """Test pre_validate_ip_address accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='IpAddress')].answer[0].valueString",
#             valid_strings_to_test=["192.168.0.1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
#         )

#     def test_pre_validate_user_id(self):
#         """Test pre_validate_user_id accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='UserId')].answer[0].valueString",
#             valid_strings_to_test=["LESTER_TESTER-1234"],
#         )

#     def test_pre_validate_user_name(self):
#         """Test pre_validate_user_name accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='UserName')].answer[0].valueString",
#             valid_strings_to_test=["LESTER TESTER"],
#         )

#     def test_pre_validate_user_email(self):
#         """Test pre_validate_user_email accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='UserEmail')].answer[0].valueString",
#             valid_strings_to_test=["lester.tester@test.com"],
#         )

#     def test_pre_validate_submitted_time_stamp(self):
#         """Test pre_validate_submitted_time_stamp accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_date_time_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='SubmittedTimeStamp')].answer[0].valueDateTime",
#         )

#     def test_pre_validate_location_identifier_value(self):
#         """Test pre_validate_location_identifier_value accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self, field_location="location.identifier.value", valid_strings_to_test=["B0C4P", "140565"]
#         )

#     def test_pre_validate_location_identifier_system(self):
#         """Test pre_validate_location_identifier_system accepts valid values and rejects invalid values"""
#         field_location = "location.identifier.system"
#         ValidatorModelTests.test_string_value(
#             self, field_location, valid_strings_to_test=["https://fhir.hl7.org.uk/Id/140565"]
#         )

#     def test_pre_validate_reduce_validation(self):
#         """Test pre_validate_reduce_validation accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_boolean_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='ReduceValidation')].answer[0].valueBoolean",
#         )


# class TestImmunizationModelPreValidationRulesForNotDone(unittest.TestCase):
#     """Test immunization pre validation rules on the FHIR model using the status="not-done" data"""

#     def setUp(self):
#         """Set up for each test. This runs before every test"""
#         self.json_data = load_json_data("not_done_hpv_immunization_event.json")
#         self.validator = ImmunizationValidator(add_post_validators=False)

#     def test_pre_validate_vaccination_situation_code(self):
#         """Test pre_validate_vaccination_situation_code accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-"
#             + "VaccinationSituation')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code",
#             valid_strings_to_test=["dummy"],
#         )

#     def test_pre_validate_vaccination_situation_display(self):
#         """Test pre_validate_vaccination_situation_display accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-"
#             + "VaccinationSituation')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display",
#             valid_strings_to_test=["dummy"],
#         )

#     def test_pre_validate_status_reason_coding(self):
#         """Test pre_validate_status_reason_coding accepts valid values and rejects invalid values"""
#         invalid_list_with_duplicates_to_test = [ValidValues.snomed_coding_element, ValidValues.snomed_coding_element]
#         ValidatorModelTests.test_unique_list(
#             self,
#             field_location="statusReason.coding",
#             valid_lists_to_test=[[ValidValues.snomed_coding_element]],
#             invalid_list_with_duplicates_to_test=invalid_list_with_duplicates_to_test,
#             expected_error_message="statusReason.coding[?(@.system=='http://snomed.info/sct')] must be unique",
#         )

#     def test_pre_validate_status_reason_coding_code(self):
#         """Test pre_validate_status_reason_coding_code accepts valid values and rejects invalid values"""
#         field_location = "statusReason.coding[?(@.system=='http://snomed.info/sct')].code"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

#     def test_pre_validate_status_reason_coding_display(self):
#         """Test pre_validate_status_reason_coding_display accepts valid values and rejects invalid values"""
#         field_location = "statusReason.coding[?(@.system=='http://snomed.info/sct')].display"
#         ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])


# class TestImmunizationModelPreValidationRulesForReduceValidation(unittest.TestCase):
#     """Test immunization pre validation rules on the FHIR model using the status="reduce validation" data"""

#     def setUp(self):
#         """Set up for each test. This runs before every test"""
#         self.json_data = load_json_data("reduce_validation_hpv_immunization_event.json")
#         self.validator = ImmunizationValidator(add_post_validators=False)

#     def test_pre_validate_reduce_validation_reason_answer(self):
#         """Test pre_validate_reduce_validation_display accepts valid values and rejects invalid values"""
#         ValidatorModelTests.test_string_value(
#             self,
#             field_location="contained[?(@.resourceType=='QuestionnaireResponse')]"
#             + ".item[?(@.linkId=='ReduceValidationReason')].answer[0].valueString",
#             valid_strings_to_test=["From DPS CSV"],
#         )

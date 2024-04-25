from collections import OrderedDict

import copy
import unittest
from unittest.mock import ANY, MagicMock, patch

from batch.decorators import (
    _decorate_patient,
    _decorate_vaccination,
    _decorate_vaccine,
    _decorate_practitioner,
    _decorate_questionare, decorate, _decorate_immunization)
from batch.errors import DecoratorError, TransformerFieldError, TransformerRowError, TransformerUnhandledError

"""Test each decorator in the transformer module
Each decorator has its own test class. Each method is used to test a specific scenario. For example there may be
different ways to create a patient object. We may need to handle legacy data, or Point of Care data that's different
from other PoCs. This means the decorator should be flexible enough to handle different scenarios. Hence a test class.
NOTE: testing protected methods is not ideal. But in this case, we are testing the decorators in isolation.
NOTE: the public function `decorate` is tested in `TestDecorate` class.
"""

raw_imms: dict = {
    "resourceType": "Immunization",
    "contained": [],
    "extension": [],
    "performer": [],
}


class TestDecorate(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

        self.decorator0 = MagicMock(name="decorator0")
        self.decorator1 = MagicMock(name="decorator1")
        self.patcher = patch("batch.decorators.all_decorators", [self.decorator0, self.decorator1])
        self.patcher.start()

    def test_decorate_apply_decorators(self):
        """it should decorate the raw imms by applying the decorators"""

        # we create two mock decorators. Then we make sure they both contribute to the imms
        def decorator_0(_imms, _record):
            _imms["decorator_0"] = "decorator_0"
            return None

        def decorator_1(_imms, _record):
            _imms["decorator_1"] = "decorator_1"
            return None

        self.decorator0.side_effect = decorator_0
        self.decorator1.side_effect = decorator_1

        # When
        imms = {}
        decorate(imms, OrderedDict([]))

        # Then
        decorators_contribution = {
            "decorator_0": "decorator_0",
            "decorator_1": "decorator_1",
        }
        # initial imms is empty so, the contribution should be equal to the decorated imms
        self.assertEqual(imms, decorators_contribution)

    def test_accumulate_errors(self):
        """it should keep calling decorators and accumulate errors"""

        def decorator_0(_imms, _record):
            return DecoratorError(errors=[TransformerFieldError(message="field a and b failed", field="a")],
                                  decorator_name="decorator_0")

        def decorator_1(_imms, _record):
            return DecoratorError(errors=[TransformerFieldError(message="field x failed", field="b")],
                                  decorator_name="decorator_1")

        self.decorator0.side_effect = decorator_0
        self.decorator1.side_effect = decorator_1

        # When
        with self.assertRaises(TransformerRowError) as e:
            imms = {}
            decorate(imms, OrderedDict([]))

        # Then
        self.assertEqual(len(e.exception.errors), 2)

    def test_unhandled_error(self):
        """it should raise an error if a decorator throws an error"""

        def decorator_0(_imms, _record):
            raise ValueError("decorator_0")

        def decorator_1(_imms, _record):
            return None

        self.decorator0.side_effect = decorator_0
        self.decorator1.side_effect = decorator_1

        # When
        with self.assertRaises(TransformerUnhandledError) as e:
            imms = {}
            decorate(imms, OrderedDict([]))

        # Then
        self.assertEqual(e.exception.decorator_name, str(self.decorator0))
        self.decorator1.assert_not_called()


class TestImmunizationDecorator(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

    def test_identifier(self):
        """it should add unique id as identifier"""
        headers = OrderedDict([
            ("unique_id", "a_unique_id"),
            ("unique_id_uri", "a_unique_id_uri")])

        _decorate_immunization(self.imms, headers)

        expected = [{"value": "a_unique_id", "system": "a_unique_id_uri"}]

        self.assertDictEqual(expected[0], self.imms["identifier"][0])

    def test_not_given_true(self):
        """it should set status to 'not-done' if not given is true"""
        headers = OrderedDict([("not_given", "TRUE")])

        _decorate_immunization(self.imms, headers)

        self.assertEqual("not-done", self.imms["status"])

    def test_not_given_false_action_delete(self):
        """it should set the status to 'entered-in-error' if not given is false and ACTION_FLAG is update or delete"""
        values = [("FALSE", "update"), ("FALSE", "delete"), ("FALSE", "some-other-value")]
        for not_given, action_flag in values:
            with self.subTest(not_given=not_given, action_flag=action_flag):
                headers = OrderedDict([("not_given", not_given), ("action_flag", action_flag)])

                _decorate_immunization(self.imms, headers)

                self.assertEqual("entered-in-error", self.imms["status"])

    def test_not_given_reason(self):
        """it should add the reason why the vaccine was not given"""
        headers = OrderedDict([("reason_not_given_code", "a_not_given_reason_code"),
                               ("reason_not_given_term", "a_not_given_reason_term")])

        _decorate_immunization(self.imms, headers)

        expected = {
            "coding": [{
                "code": "a_not_given_reason_code",
                "display": "a_not_given_reason_term"
            }]
        }
        self.assertDictEqual(expected, self.imms["statusReason"])

    def test_use_indication_if_not_given_empty(self):
        """it should use the indication if reason-not-given is empty. they are mutually exclusive"""
        headers = OrderedDict([
            ("reason_not_given_code", ""),
            ("reason_not_given_term", ""),
            ("indication_code", "a_indication_code"),
            ("indication_term", "a_indication_term")
        ])

        _decorate_immunization(self.imms, headers)

        expected = {
            "coding": [{
                "code": "a_indication_code",
                "display": "a_indication_term"
            }]
        }
        self.assertDictEqual(expected, self.imms["statusReason"])

    def test_recorded_date(self):
        """it should convert and add the recorded date to the immunization object"""
        headers = OrderedDict([("recorded_date", "20240221")])

        _decorate_immunization(self.imms, headers)

        self.assertEqual("2024-02-21", self.imms["recorded"])


class TestPatientDecorator(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

    def test_add_patient(self):
        """it should add the patient object to the contained list"""
        # Given
        headers = OrderedDict([])

        _decorate_patient(self.imms, headers)

        expected_imms = copy.deepcopy(raw_imms)
        expected_imms["patient"] = {"reference": "#patient1"}
        expected_imms["contained"].append({
            "resourceType": "Patient",
            "id": "patient1",
            "identifier": [],
            "name": []
        })

        self.assertDictEqual(expected_imms, self.imms)

    def test_add_nhs_number(self):
        """it should add the nhs number to the patient object"""
        # Given
        headers = OrderedDict([("nhs_number", "a_nhs_number")])

        # When
        _decorate_patient(self.imms, headers)

        # Then
        expected = {
            "resourceType": "Patient",
            "id": ANY,
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "a_nhs_number"
                }
            ],
            "name": []
        }
        self.assertDictEqual(expected, self.imms["contained"][0])

    def test_add_nhs_number_extension(self):
        """it should add the nhs number to the patient object"""
        # Given
        headers = OrderedDict([
            ("nhs_number", "a_nhs_number"),
            ("nhs_number_status_indicator_code", "a_nhs_number_status_indicator_code"),
            ("nhs_number_status_indicator_description", "a_nhs_number_status_indicator_description"),
        ])

        # When
        _decorate_patient(self.imms, headers)

        # Then
        expected = {
            "resourceType": "Patient",
            "id": ANY,
            "identifier": [{
                "system": ANY,
                "value": ANY,
                "extension": [{
                    "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
                    "valueCodeableConcept": {
                        "coding": [{
                            "system": "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland",
                            "code": "a_nhs_number_status_indicator_code",
                            "display": "a_nhs_number_status_indicator_description"
                        }]
                    }
                }]
            }],
            "name": []
        }
        self.assertDictEqual(expected, self.imms["contained"][0])

    def test_add_name(self):
        """it should add the name to the patient object"""
        # Given
        headers = OrderedDict([
            ("person_surname", "a_person_surname"),
            ("person_forename", "a_person_forename"),
        ])

        # When
        _decorate_patient(self.imms, headers)

        # Then
        expected = {
            "resourceType": "Patient",
            "id": "patient1",
            "identifier": [],
            "name": [
                {
                    "family": "a_person_surname",
                    "given": ["a_person_forename"]
                }
            ]
        }
        self.assertDictEqual(expected, self.imms["contained"][0])

    def test_add_dob(self):
        """it should convert and add the dob to the patient object"""
        headers = OrderedDict([("person_dob", "19930821")])

        _decorate_patient(self.imms, headers)

        expected = {
            "resourceType": "Patient",
            "id": ANY,
            "identifier": [],
            "name": [],
            "birthDate": "1993-08-21"
        }
        self.assertDictEqual(expected, self.imms["contained"][0])

    def test_gender_converter(self):
        """it should convert gender code to fhir code and leave it as is if we can't convert it"""
        values = [("0", "unknown"),
                  ("1", "male"),
                  ("2", "female"),
                  ("9", "other"),
                  ("unknown_code_123", "unknown_code_123")]
        for gen_num, gen_value in values:
            with self.subTest(value=gen_num):
                headers = OrderedDict([("person_gender_code", gen_num)])
                imms = copy.deepcopy(raw_imms)

                _decorate_patient(imms, headers)

                expected = {
                    "resourceType": "Patient",
                    "id": ANY,
                    "identifier": [],
                    "name": [],
                    "gender": gen_value
                }

                self.assertDictEqual(expected, imms["contained"][0])

    def test_add_address(self):
        """it should add postcode and address to the patient object"""
        headers = OrderedDict([("person_postcode", "a_person_postcode")])

        _decorate_patient(self.imms, headers)

        expected = {
            "resourceType": "Patient",
            "id": ANY,
            "identifier": [],
            "name": [],
            "address": [
                {
                    "postalCode": "a_person_postcode",
                }
            ]
        }
        self.assertDictEqual(expected, self.imms["contained"][0])


class TestVaccineDecorator(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

    def test_vaccine_product(self):
        headers = OrderedDict([
            ("vaccine_product_code", "a_vaccine_product_code"),
            ("vaccine_product_term", "a_vaccine_product_term"),
        ])

        _decorate_vaccine(self.imms, headers)

        expected = {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "a_vaccine_product_code",
                "display": "a_vaccine_product_term"
            }]
        }
        self.assertDictEqual(expected, self.imms["vaccineCode"])

    def test_manufacturer(self):
        headers = OrderedDict([("vaccine_manufacturer", "a_vaccine_manufacturer")])

        _decorate_vaccine(self.imms, headers)

        expected = {"display": "a_vaccine_manufacturer"}
        self.assertDictEqual(expected, self.imms["manufacturer"])

    def test_expiration(self):
        """it should convert and add expiration date"""
        headers = OrderedDict([("expiry_date", "20240303")])

        _decorate_vaccine(self.imms, headers)

        expected = "2024-03-03"
        self.assertEqual(expected, self.imms["expirationDate"])

    def test_lot_number(self):
        headers = OrderedDict([("batch_number", "a_batch_number")])

        _decorate_vaccine(self.imms, headers)

        expected = "a_batch_number"
        self.assertEqual(expected, self.imms["lotNumber"])


class TestVaccinationDecorator(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

    def test_vaccination_procedure(self):
        """it should get the vaccination procedure code and term and add it to the extension list"""
        a_vaccination_procedure_code = "1324681000000101"
        headers = OrderedDict([
            ("vaccination_procedure_code", a_vaccination_procedure_code),
            ("vaccination_procedure_term", "a_vaccination_procedure_term"),
        ])

        _decorate_vaccination(self.imms, headers)

        # Then
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
        expected = {
            "url": url,
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": a_vaccination_procedure_code,
                        "display": "a_vaccination_procedure_term"
                    }
                ]
            }
        }
        self.assertDictEqual(expected, self.imms["extension"][0])

    def test_vaccination_situation(self):
        """it should get the vaccination situation code and term and add it to the extension list"""
        a_vaccination_situation_code = "1324681000000101"
        headers = OrderedDict([
            ("vaccination_situation_code", a_vaccination_situation_code),
            ("vaccination_situation_term", "a_vaccination_situation_term"),
        ])

        _decorate_vaccination(self.imms, headers)

        # Then
        url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation"
        expected = {
            "url": url,
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": a_vaccination_situation_code,
                        "display": "a_vaccination_situation_term"
                    }
                ]
            }
        }
        self.assertDictEqual(expected, self.imms["extension"][0])

    def test_occurrence_date_time(self):
        """it should convert and add the occurrence date time to the vaccination object"""
        headers = OrderedDict([("date_and_time", "20240221T171930")])

        _decorate_vaccination(self.imms, headers)

        expected = "2024-02-21T17:19:30+00:00"
        self.assertEqual(expected, self.imms["occurrenceDateTime"])

    def test_primary_source_false(self):
        """it should set the primary source by converting the string to a boolean"""
        headers = OrderedDict([("primary_source", "FALSE")])

        _decorate_vaccination(self.imms, headers)

        self.assertEqual(False, self.imms["primarySource"])

    def test_primary_source_true(self):
        """it should set the primary source by converting the string to a boolean"""
        headers = OrderedDict([("primary_source", "TRUE")])

        _decorate_vaccination(self.imms, headers)

        self.assertEqual(True, self.imms["primarySource"])

    def test_report_origin(self):
        """it should set the report origin"""
        headers = OrderedDict([("report_origin", "a_report_origin")])

        _decorate_vaccination(self.imms, headers)

        expected = {"text": "a_report_origin"}
        self.assertDictEqual(expected, self.imms["reportOrigin"])

    def test_vaccination_site(self):
        """it should get the vaccination site code and term and add it to the site object"""
        headers = OrderedDict([
            ("site_of_vaccination_code", "a_site_of_vaccination_code"),
            ("site_of_vaccination_term", "a_site_of_vaccination_term"),
        ])

        _decorate_vaccination(self.imms, headers)

        expected = {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "a_site_of_vaccination_code",
                    "display": "a_site_of_vaccination_term"
                }
            ]
        }
        self.assertDictEqual(expected, self.imms["site"])

    def test_vaccination_route(self):
        """it should get the vaccination route code and term and add it to the route object"""
        headers = OrderedDict([
            ("route_of_vaccination_code", "a_route_of_vaccination_code"),
            ("route_of_vaccination_term", "a_route_of_vaccination_term"),
        ])

        _decorate_vaccination(self.imms, headers)

        expected = {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "a_route_of_vaccination_code",
                    "display": "a_route_of_vaccination_term"
                }
            ]
        }
        self.assertDictEqual(expected, self.imms["route"])

    def test_dose_quantity(self):
        """it should get the dose amount, unit code and term and add it to the doseQuantity object"""
        headers = OrderedDict([
            ("dose_amount", "123.1234"),
            ("dose_unit_code", "a_dose_unit_code"),
            ("dose_unit_term", "a_dose_unit_term"),
        ])

        _decorate_vaccination(self.imms, headers)

        expected = {
            "value": 123.1234,
            "unit": "a_dose_unit_term",
            "code": "a_dose_unit_code",
            "system": "http://unitsofmeasure.org"
        }
        self.assertDictEqual(expected, self.imms["doseQuantity"])

    def test_dose_quantity_decimal(self):
        """it should convert the string to a decimal with 4 decimal places"""
        headers = OrderedDict([
            ("dose_amount", "123.1234567"),
            ("dose_unit_code", "a_dose_unit_code"),
        ])

        _decorate_vaccination(self.imms, headers)

        expected = {
            "value": 123.1234,
            "unit": ANY,
            "system": ANY,
            "code": ANY,
        }
        self.assertDictEqual(expected, self.imms["doseQuantity"])

    def test_dose_sequence(self):
        """it should add the dose sequence to the vaccination object as int"""
        headers = OrderedDict([("dose_sequence", "12")])

        _decorate_vaccination(self.imms, headers)

        expected = [{"doseNumberPositiveInt": 12}]
        self.assertEqual(expected, self.imms["protocolApplied"])


class TestPractitionerDecorator(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

    def test_add_practitioner(self):
        """it should add the practitioner object to the contained list and the performer list"""
        headers = OrderedDict([
            ("performing_professional_body_reg_code", "a_performing_professional_body_reg_code")
        ])

        _decorate_practitioner(self.imms, headers)

        expected_imms = copy.deepcopy(raw_imms)
        expected_imms["contained"].append({
            "resourceType": "Practitioner",
            "id": "practitioner1",
            "identifier": ANY,
            "name": []
        })
        expected_imms["performer"].append({"actor": {"reference": "#practitioner1"}})

        self.assertDictEqual(expected_imms, self.imms)

    def test_add_practitioner_identifier(self):
        headers = OrderedDict([
            ("performing_professional_body_reg_code", "a_performing_professional_body_reg_code"),
            ("performing_professional_body_reg_uri", "a_performing_professional_body_reg_uri"),
        ])

        _decorate_practitioner(self.imms, headers)

        expected_imms = copy.deepcopy(raw_imms)
        expected_imms["contained"].append({
            "resourceType": "Practitioner",
            "id": ANY,
            "identifier": [{
                "system": "a_performing_professional_body_reg_uri",
                "value": "a_performing_professional_body_reg_code"
            }],
            "name": []
        })
        expected_imms["performer"].append(ANY)

        self.assertDictEqual(expected_imms, self.imms)

    def test_practitioner_name(self):
        """it should add practitioner name"""
        headers = OrderedDict([
            ("performing_professional_body_reg_code", "a_performing_professional_body_reg_code"),
            ("performing_professional_forename", "a_performing_professional_forename"),
            ("performing_professional_surname", "a_performing_professional_surname"),
        ])

        _decorate_practitioner(self.imms, headers)

        expected_imms = copy.deepcopy(raw_imms)
        expected_imms["contained"].append({
            "resourceType": "Practitioner",
            "id": ANY,
            "identifier": ANY,
            "name": [{
                "family": "a_performing_professional_surname",
                "given": ["a_performing_professional_forename"]
            }]
        })
        expected_imms["performer"].append(ANY)

        self.assertDictEqual(expected_imms, self.imms)

    def test_add_organisation(self):
        """it should add the organisation where the vaccination was given based on the site code"""
        headers = OrderedDict([
            ("site_code", "a_site_code"),
            ("site_code_type_uri", "a_site_code_type_uri"),
            ("site_name", "a_site_name"),
        ])

        _decorate_practitioner(self.imms, headers)

        expected = {
            "actor": {
                "type": "Organization",
                "identifier": {
                    "system": "a_site_code_type_uri",
                    "value": "a_site_code"
                },
                "display": "a_site_name"
            }
        }

        self.assertDictEqual(expected, self.imms["performer"][0])

    def test_org_display_is_mandatory_and_not_empty(self):
        headers = OrderedDict([
            ("site_code", "a_site_code"),
            ("site_code_type_uri", "a_site_code_type_uri"),
        ])

        _decorate_practitioner(self.imms, headers)

        expected_default = "N/A"
        expected = {
            "actor": {
                "type": "Organization",
                "identifier": {
                    "system": "a_site_code_type_uri",
                    "value": "a_site_code"
                },
                "display": expected_default
            }
        }
        self.assertDictEqual(expected, self.imms["performer"][0])

    def test_location(self):
        """it should get the location code and type and add it to the location object"""
        headers = OrderedDict([
            ("location_code", "a_location_code"),
            ("location_code_type_uri", "a_location_code_type_uri"),
        ])

        _decorate_practitioner(self.imms, headers)

        expected = {
            "identifier": {
                "value": "a_location_code",
                "system": "a_location_code_type_uri"
            }}

        self.assertDictEqual(expected, self.imms["location"])


class TestDecorateQuestionare(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.imms = copy.deepcopy(raw_imms)

    @staticmethod
    def _make_questionare(imms: dict, name: str, item: dict):
        questionare = {
            "resourceType": "QuestionnaireResponse",
            "id": ANY,
            "status": ANY,
            "item": [{
                "linkId": name,
                "answer": [item]
            }]
        }
        imms["contained"].append(questionare)

    @staticmethod
    def _make_questionare_item(name: str, item: dict):
        return {
            "linkId": name,
            "answer": [item]
        }

    @staticmethod
    def _add_questionare_item(imms: dict, name: str, item: dict):
        imms["contained"][0]["item"].append({
            "linkId": name,
            "answer": [item]
        })

    def test_reduce_validation_code(self):
        """it should add the reduceValidation if provided with the default value of false"""
        headers = OrderedDict([("reduce_validation_code", "True")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("ReduceValidation", {"valueBoolean": True})

        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_reduce_validation_reason(self):
        """it should add the ReduceValidationReason if code is provided"""
        headers = OrderedDict([
            ("reduce_validation_code", "True"),
            ("reduce_validation_reason", "a_reduce_validation_reason"),
        ])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("ReduceValidationReason",
                                                    {"valueString": "a_reduce_validation_reason"})

        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_consent(self):
        """it should add the consent to the questionare list"""
        headers = OrderedDict([
            ("consent_for_treatment_code", "a_consent_for_treatment_code"),
            ("consent_for_treatment_description", "a_consent_for_treatment_description"),
        ])

        _decorate_questionare(self.imms, headers)

        item = {"valueCoding": {
            "system": "http://snomed.info/sct",
            "code": "a_consent_for_treatment_code",
            "display": "a_consent_for_treatment_description"
        }}
        expected_item = self._make_questionare_item("Consent", item)

        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_care_setting(self):
        """it should add the care setting to the questionare list"""
        headers = OrderedDict([
            ("care_setting_type_code", "a_care_setting_type_code"),
            ("care_setting_type_description", "a_care_setting_type_description"),
        ])

        _decorate_questionare(self.imms, headers)

        item = {"valueCoding": {
            "system": "http://snomed.info/sct",
            "code": "a_care_setting_type_code",
            "display": "a_care_setting_type_description"
        }}
        expected_item = self._make_questionare_item("CareSetting", item)
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_local_patient(self):
        """it should add the local patient to the questionare list"""
        headers = OrderedDict([
            ("local_patient_id", "a_local_patient_id"),
            ("local_patient_uri", "a_local_patient_uri"),
        ])

        _decorate_questionare(self.imms, headers)

        item = {"valueReference": {
            "identifier": {
                "system": "a_local_patient_uri",
                "value": "a_local_patient_id"
            }
        }}
        expected_item = self._make_questionare_item("LocalPatient", item)
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_ip_address(self):
        """it should add the ip address to the questionare list"""
        headers = OrderedDict([("ip_address", "a_ip_address")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("IpAddress", {"valueString": "a_ip_address"})
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_user_id(self):
        """it should add the user id to the questionare list"""
        headers = OrderedDict([("user_id", "a_user_id")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("UserId", {"valueString": "a_user_id"})
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_user_name(self):
        """it should add the user name to the questionare list"""
        headers = OrderedDict([("user_name", "a_user_name")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("UserName", {"valueString": "a_user_name"})
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_user_email(self):
        """it should add the user email to the questionare list"""
        headers = OrderedDict([("user_email", "a_user_email")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("UserEmail", {"valueString": "a_user_email"})
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_submitted_timestamp(self):
        """it should convert and add the submitted timestamp to the questionare list"""
        headers = OrderedDict([("submitted_timestamp", "20240221T17193000")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("SubmittedTimeStamp",
                                                    {"valueDateTime": "2024-02-21T17:19:30+00:00"})
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

    def test_add_performer_job_role(self):
        """it should add the performer job role to the questionare list"""
        headers = OrderedDict([("sds_job_role_name", "a_sds_job_role_name")])

        _decorate_questionare(self.imms, headers)

        expected_item = self._make_questionare_item("PerformerSDSJobRole",
                                                    {"valueString": "a_sds_job_role_name"})
        self.assertIn(expected_item, self.imms["contained"][0]["item"])

"""
Test each decorator in the transformer module.
Each decorator has its own test class, which tests various potential combinations of headers.
NOTE: testing protected methods is not ideal. But in this case, we are testing the decorators in isolation.
NOTE: the public function `decorate` is tested in `TestDecorate` class.
"""

from collections import OrderedDict
from decimal import Decimal
import copy
import unittest
from unittest.mock import MagicMock, patch

from batch.decorators import (
    _decorate_patient,
    _decorate_vaccination,
    _decorate_vaccine,
    _decorate_performer,
    _decorate_questionnaire,
    decorate,
    _decorate_immunization,
)
from batch.errors import DecoratorError, TransformerFieldError, TransformerRowError, TransformerUnhandledError
from tests.test_batch.decorators_constants import AllHeaders, AllHeadersExpectedOutput, ExtensionItems
from constants import VALID_NHS_NUMBER

raw_imms: dict = {"resourceType": "Immunization", "contained": []}


class TestDecorate(unittest.TestCase):
    def setUp(self):
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
            return DecoratorError(
                errors=[TransformerFieldError(message="field a and b failed", field="a")], decorator_name="decorator_0"
            )

        def decorator_1(_imms, _record):
            return DecoratorError(
                errors=[TransformerFieldError(message="field x failed", field="b")], decorator_name="decorator_1"
            )

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
    """Tests for _decorate_immunization"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_completed_all_headers(self):
        """
        Test that all immunization fields for status 'completed' are added when all the relevant immunization fields
        contain non-empty data
        """
        _decorate_immunization(self.imms, AllHeaders.immunization_completed)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.immunization_completed)

    def test_not_done_all_headers(self):
        """
        Test that all immunization fields for status 'not-done' are added when all the relevant immunization fields
        contain non-empty data
        """
        _decorate_immunization(self.imms, AllHeaders.immunization_not_done)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.immunization_not_done)

    def test_no_immunization_headers(self):
        """Test that no fields are added when no immunization fields contain non-empty data"""
        _decorate_immunization(self.imms, OrderedDict([("unique_id", "")]))
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": []})

    def test_not_given_and_action_flag(self):
        """Test that status is set to the appropriate value based on not_given and action_flag"""
        # Valid not_given and action_flag values
        for not_given, action_flag, status in [
            ("true", "new", "not-done"),
            ("TRUE", "UPDATE", "not-done"),
            ("fAlsE", "nEw", "completed"),
            ("false", "update", "completed"),
        ]:
            _decorate_immunization(self.imms, OrderedDict([("not_given", not_given), ("action_flag", action_flag)]))
            self.assertEqual(self.imms["status"], status)

        # Invalid not_given and/ or action_flag values
        base_error_message = "  Decorator _decorate_immunization failed due to:"
        not_given_error_message = "\n    NOT_GIVEN is missing or is not a boolean"
        action_flag_error_message = "\n    ACTION_FLAG is missing or is not in the set 'new', 'update', 'delete'"

        for not_given, action_flag, error_message in [
            ("invalid_not_given", "new", not_given_error_message),
            ("", "new", not_given_error_message),
            (None, "new", not_given_error_message),
            ("false", "invalid_action_flag", action_flag_error_message),
            ("false", "", action_flag_error_message),
            ("false", None, action_flag_error_message),
            (None, None, not_given_error_message + action_flag_error_message),
        ]:
            output = _decorate_immunization(
                self.imms, OrderedDict([("not_given", not_given), ("action_flag", action_flag)])
            )
            self.assertIn(base_error_message + error_message, str(output))
            self.assertEqual(type(output), DecoratorError)

    def test_reason_not_given(self):
        """Test that only non-empty reason_not_given values are added"""
        # reason_not_given: _code non-empty, _term empty
        _decorate_immunization(self.imms, OrderedDict([("reason_not_given_code", "a_not_given_reason_code")]))
        self.assertDictEqual(self.imms["statusReason"], {"coding": [{"code": "a_not_given_reason_code"}]})

        # reason_not_given: _code empty, _term non-empty
        _decorate_immunization(self.imms, OrderedDict([("reason_not_given_term", "a_not_given_reason_term")]))
        self.assertDictEqual(self.imms["statusReason"], {"coding": [{"display": "a_not_given_reason_term"}]})

    def test_indication(self):
        """Test that only non-empty indication values are added"""
        # indication: _code non-empty, _term empty
        _decorate_immunization(self.imms, OrderedDict([("indication_code", "indication_code")]))
        self.assertListEqual(self.imms["reasonCode"], [{"coding": [{"code": "indication_code"}]}])

        # indication: _code empty, _term non-empty
        _decorate_immunization(self.imms, OrderedDict([("indication_term", "indication_term")]))
        self.assertListEqual(self.imms["reasonCode"], [{"coding": [{"display": "indication_term"}]}])

    def test_unique_id(self):
        """Test that only non-empty unique_id values are added"""
        # unique_id non-empty, unique_uri empty
        _decorate_immunization(self.imms, OrderedDict([("unique_id", "a_unique_id"), ("unique_id_uri", None)]))
        self.assertListEqual(self.imms["identifier"], [{"value": "a_unique_id"}])

        # Unique_id empty, unique_uri non-empty
        _decorate_immunization(self.imms, OrderedDict([("unique_id_uri", "a_unique_id_uri")]))
        self.assertListEqual(self.imms["identifier"], [{"system": "a_unique_id_uri"}])


class TestPatientDecorator(unittest.TestCase):
    """Tests for _decorate_patient"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_patient_headers(self):
        """Test that all patient fields are added when all patient fields contain non-empty data"""
        _decorate_patient(self.imms, AllHeaders.patient)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.patient)

    def test_no_patient_headers(self):
        """Test that no fields are added when no patient fields contain non-empty data"""
        _decorate_patient(self.imms, OrderedDict([]))
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": []})

    def test_one_patient_header(self):
        """Test that patient fields are added when one patient field contains non-empty data"""
        _decorate_patient(self.imms, OrderedDict([("person_dob", "19930821")]))
        expected_imms = {
            "resourceType": "Immunization",
            "contained": [{"resourceType": "Patient", "id": "Patient1", "birthDate": "1993-08-21"}],
            "patient": {"reference": "#Patient1"},
        }
        self.assertDictEqual(self.imms, expected_imms)

    def test_person_name(self):
        """Test that only non-empty name values are added"""
        # Surname non-empty, forename empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, OrderedDict([("person_surname", "a_surname"), ("person_forename", "")]))
        self.assertListEqual(imms["contained"][0]["name"], [{"family": "a_surname"}])

        # Surname empty, forename non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, OrderedDict([("person_forename", "a_forename")]))
        self.assertListEqual(imms["contained"][0]["name"], [{"given": ["a_forename"]}])

    def test_patient_extension(self):
        """it should add the nhs number to the patient object"""
        # nhs_number_status_indicator: _code non-empty, _description empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, OrderedDict([("nhs_number_status_indicator_code", "an_nhs_status_code")]))
        expected = {"extension": [copy.deepcopy(ExtensionItems.nhs_number_status)]}
        expected["extension"][0]["valueCodeableConcept"]["coding"][0].pop("display")
        self.assertDictEqual(imms["contained"][0]["identifier"][0], expected)

        # nhs_number_status_indicator: _code empty, _description non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, OrderedDict([("nhs_number_status_indicator_description", "an_nhs_status_description")]))
        expected = {"extension": [copy.deepcopy(ExtensionItems.nhs_number_status)]}
        expected["extension"][0]["valueCodeableConcept"]["coding"][0].pop("code")
        self.assertDictEqual(imms["contained"][0]["identifier"][0], expected)

    def test_patient_identifier(self):
        """Fill this in"""
        # nhs_number non_empty, both extension values empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, OrderedDict([("nhs_number", VALID_NHS_NUMBER)]))
        expected = [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": VALID_NHS_NUMBER}]
        self.assertListEqual(imms["contained"][0]["identifier"], expected)

        # nhs_number empty, both extension values non_empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict(
            [
                ("nhs_number_status_indicator_description", "an_nhs_status_description"),
                ("nhs_number_status_indicator_code", "an_nhs_status_code"),
            ]
        )
        _decorate_patient(imms, headers)
        expected = [{"extension": [ExtensionItems.nhs_number_status]}]
        self.assertListEqual(imms["contained"][0]["identifier"], expected)


class TestVaccineDecorator(unittest.TestCase):
    """Tests for _decorate_vaccine"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_vaccine_headers(self):
        """Test that all vaccine fields are added when all vaccine fields contain non-empty data"""
        _decorate_vaccine(self.imms, AllHeaders.vaccine)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.vaccine)

    def test_no_vaccine_headers(self):
        """Test that no fields are added when no vaccine fields contain non-empty data"""
        _decorate_vaccine(self.imms, OrderedDict([]))
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": []})

    def test_vaccine_product(self):
        """Test that only non-empty vaccine_product values are added"""
        # vaccine_product: _code non-empty, term empty
        headers = OrderedDict([("vaccine_product_code", "a_vacc_code"), ("vaccine_product_term", "")])
        _decorate_vaccine(self.imms, headers)
        expected = {"coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_code"}]}
        self.assertDictEqual(self.imms["vaccineCode"], expected)

        # vaccine_product: _code empty, term non-empty
        headers = OrderedDict([("vaccine_product_code", ""), ("vaccine_product_term", "a_vacc_term")])
        _decorate_vaccine(self.imms, headers)
        expected = {"coding": [{"system": "http://snomed.info/sct", "display": "a_vacc_term"}]}
        self.assertDictEqual(self.imms["vaccineCode"], expected)


class TestVaccinationDecorator(unittest.TestCase):
    """Tests for _decorate_vaccination"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_vaccination_headers(self):
        """Test that all vaccination fields are added when all vaccination fields contain non-empty data"""
        _decorate_vaccination(self.imms, AllHeaders.vaccination)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.vaccination)

    def test_no_vaccination_headers(self):
        """Test that no fields are added when no vaccination fields contain non-empty data"""
        _decorate_vaccination(self.imms, OrderedDict([]))
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": []})

    def test_one_extension_header(self):
        """Test that the relevant extension fields are added when one vaccination field contains non-empty data"""
        _decorate_vaccination(self.imms, OrderedDict([("vaccination_procedure_term", "a_vaccination_procedure_term")]))

        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_procedure)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("code")
        expected_output = {"resourceType": "Immunization", "contained": [], "extension": [expected_extension_item]}
        self.assertDictEqual(self.imms, expected_output)

    def test_vaccination_procedure(self):
        """Test that only non-empty vaccination_procedure values are added"""
        # vaccination_procedure: _code empty, _term non-empty
        _decorate_vaccination(self.imms, OrderedDict([("vaccination_procedure_term", "a_vaccination_procedure_term")]))
        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_procedure)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("code")
        self.assertListEqual(self.imms["extension"], [expected_extension_item])

        # vaccination_procedure: _code empty, _term non-empty
        _decorate_vaccination(self.imms, OrderedDict([("vaccination_procedure_code", "a_vaccination_procedure_code")]))
        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_procedure)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("display")
        self.assertListEqual(self.imms["extension"], [expected_extension_item])

    def test_vaccination_situation(self):
        """Test that only non-empty vaccination_situation values are added"""
        # vaccination_situation: _code empty, _term non-empty
        _decorate_vaccination(self.imms, OrderedDict([("vaccination_situation_term", "a_vaccination_situation_term")]))
        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_situation)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("code")
        self.assertListEqual(self.imms["extension"], [expected_extension_item])

        # vaccination_situation: _code empty, _term non-empty
        _decorate_vaccination(self.imms, OrderedDict([("vaccination_situation_code", "a_vaccination_situation_code")]))
        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_situation)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("display")
        self.assertListEqual(self.imms["extension"], [expected_extension_item])

    def test_site_of_vaccination(self):
        """Test that only non-empty site_of_vaccination values are added"""
        # site_of_vaccination: _code non-empty, _display empty
        _decorate_vaccination(self.imms, OrderedDict([("site_of_vaccination_code", "a_vacc_site_code")]))
        expected = {"coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_site_code"}]}
        self.assertDictEqual(self.imms["site"], expected)

        # site_of_vaccination: _code empty, _display non-empty
        _decorate_vaccination(self.imms, OrderedDict([("site_of_vaccination_term", "a_vacc_site_term")]))
        expected = {"coding": [{"system": "http://snomed.info/sct", "display": "a_vacc_site_term"}]}
        self.assertDictEqual(self.imms["site"], expected)

    def test_route_of_vaccination(self):
        """Test that only non-empty route_of_vaccination values are added"""
        # route_of_vaccination: _code non-empty, _display empty
        _decorate_vaccination(self.imms, OrderedDict([("route_of_vaccination_code", "a_vacc_route_code")]))
        expected = {"coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_route_code"}]}
        self.assertDictEqual(self.imms["route"], expected)

        # route_of_vaccination: _code empty, _display non-empty
        _decorate_vaccination(self.imms, OrderedDict([("route_of_vaccination_term", "a_vacc_route_term")]))
        expected = {"coding": [{"system": "http://snomed.info/sct", "display": "a_vacc_route_term"}]}
        self.assertDictEqual(self.imms["route"], expected)

    def test_dose_quantity(self):
        """Test that only non-empty dose_quantity values (dose_amount, dose_unit_term and dose_unit_code) are added"""
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": Decimal("0.5"), "unit": "t", "code": "code"}
        # dose: _amount non-empty, _unit_term non-empty, _unit_code empty
        headers = OrderedDict([("dose_amount", "0.5"), ("dose_unit_term", "a_dose_unit_term"), ("dose_unit_code", "")])
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": Decimal("0.5"), "unit": "a_dose_unit_term"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount non-empty, _unit_term empty, _unit_code non-empty
        headers = OrderedDict([("dose_amount", "0.5"), ("dose_unit_code", "a_dose_unit_code")])
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": Decimal("0.5"), "code": "a_dose_unit_code"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount empty, _unit_term non-empty, _unit_code non-empty
        headers = OrderedDict([("dose_unit_term", "a_dose_unit_term"), ("dose_unit_code", "a_dose_unit_code")])
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "code": "a_dose_unit_code", "unit": "a_dose_unit_term"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount non-empty, _unit_term empty, _unit_code empty
        headers = OrderedDict([("dose_amount", "2"), ("dose_unit_code", "")])
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": 2}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount empty, _unit_term non-empty, _unit_code empty
        headers = OrderedDict([("dose_unit_term", "a_dose_unit_term"), ("dose_unit_code", "")])
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "unit": "a_dose_unit_term"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount empty, _unit_term empty, _unit_code non-empty
        headers = OrderedDict([("dose_unit_code", "a_dose_unit_code")])
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "code": "a_dose_unit_code"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)


class TestPerformerDecorator(unittest.TestCase):
    """Tests for _decorate_vaccination"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_performer_headers(self):
        """Test that all performer fields are added when all performer fields contain non-empty data"""
        _decorate_performer(self.imms, AllHeaders.performer)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.performer)

    def test_no_performer_headers(self):
        """Test that no fields are added when no performer fields contain non-empty data"""
        _decorate_performer(self.imms, OrderedDict([]))
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": []})

    def test_one_performer_header(self):
        """Test that the relevant fields are added when one performer field contains non-empty data"""
        _decorate_performer(self.imms, OrderedDict([("site_name", "a_site_name")]))
        expected_output = {
            "resourceType": "Immunization",
            "contained": [],
            "performer": [
                {"actor": {"type": "Organization", "display": "a_site_name"}},
            ],
        }
        self.assertDictEqual(self.imms, expected_output)

    def test_one_practitioner_header(self):
        """Test that the relevant fields are added when one practitioner field contains non-empty data"""
        _decorate_performer(self.imms, OrderedDict([("performing_professional_forename", "a_prof_forename")]))
        expected_output = {
            "resourceType": "Immunization",
            "contained": [
                {
                    "resourceType": "Practitioner",
                    "id": "Practitioner1",
                    "name": [{"given": ["a_prof_forename"]}],
                }
            ],
            "performer": [{"actor": {"reference": "#Practitioner1"}}],
        }
        self.assertDictEqual(self.imms, expected_output)

    def test_performing_professional_body_reg(self):
        """Test that only non-empty performing_professional_body_reg values are added"""
        # performing_professional_body_reg: _code non-empty, _uri empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, OrderedDict([("performing_professional_body_reg_code", "a_prof_body_code")]))
        self.assertListEqual(imms["contained"][0]["identifier"], [{"value": "a_prof_body_code"}])

        # performing_professional_body_reg: _code empty, _uri non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, OrderedDict([("performing_professional_body_reg_uri", "a_prof_body_uri")]))
        self.assertListEqual(imms["contained"][0]["identifier"], [{"system": "a_prof_body_uri"}])

    def test_performing_professional_name(self):
        """Test that only non-empty performing_professional_name values are added"""
        # performing_professional: surname non-empty, _forename empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, OrderedDict([("performing_professional_surname", "a_prof_surname")]))
        self.assertListEqual(imms["contained"][0]["name"], [{"family": "a_prof_surname"}])

        # performing_professional: surname empty, _forename non-empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("performing_professional_forename", "a_prof_forename")])
        _decorate_performer(imms, headers)
        self.assertListEqual(imms["contained"][0]["name"], [{"given": ["a_prof_forename"]}])

    def test_site_code(self):
        """Test that only non-empty site_code values are added"""
        # site_code non-empty, site_code_type_uri empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, OrderedDict([("site_code", "a_site_code"), ("site_code_type_uri", "")]))
        self.assertDictEqual(imms["performer"][0]["actor"]["identifier"], {"value": "a_site_code"})

        # site_code empty, site_code_type_uri non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, OrderedDict([("site_code", ""), ("site_code_type_uri", "a_site_code_uri")]))
        self.assertDictEqual(imms["performer"][0]["actor"]["identifier"], {"system": "a_site_code_uri"})

    def test_location(self):
        """Test that only non-empty location values are added"""
        # location_code non-empty, location_code_type_uri empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("location_code", "a_location_code"), ("location_code_type_uri", "")])
        _decorate_performer(imms, headers)
        self.assertDictEqual(imms["location"], {"type": "Location", "identifier": {"value": "a_location_code"}})

        # location_code empty, location_code_type_uri non-empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("location_code", ""), ("location_code_type_uri", "a_location_code_uri")])
        _decorate_performer(imms, headers)
        self.assertDictEqual(imms["location"], {"type": "Location", "identifier": {"system": "a_location_code_uri"}})


class TestQuestionnaireDecorator(unittest.TestCase):
    """Tests for _decorate_questionnaire"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_questionnaire_headers(self):
        """Test that all questionnaire fields are added when all questionnaire fields contain non-empty data"""
        _decorate_questionnaire(self.imms, AllHeaders.questionnaire)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.questionnaire)

    def test_no_questionnaire_headers(self):
        """Test that no fields are added when no questionnaire fields contain non-empty data"""
        _decorate_questionnaire(self.imms, OrderedDict([]))
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": []})

    def test_one_questionnaire_header(self):
        """Test that the relevant fields are added when one questionnaire field contains non-empty data"""
        _decorate_questionnaire(self.imms, OrderedDict([("reduce_validation_code", True)]))
        expected_output = {
            "resourceType": "Immunization",
            "contained": [
                {
                    "resourceType": "QuestionnaireResponse",
                    "id": "QR1",
                    "status": "completed",
                    "item": [{"linkId": "ReduceValidation", "answer": [{"valueBoolean": True}]}],
                }
            ],
        }
        self.assertDictEqual(self.imms, expected_output)

    def test_consent_for_treatment(self):
        """Test that only non-empty consent_for_treatment values are added"""
        # consent_for_treatment: _code non-empty, _description empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("consent_for_treatment_code", "a_consent_code")])
        _decorate_questionnaire(imms, headers)
        expected_consent = {"linkId": "Consent", "answer": [{"valueCoding": {"code": "a_consent_code"}}]}
        self.assertDictEqual(imms["contained"][0]["item"][0], expected_consent)

        # consent_for_treatment: _code empty, _description non-empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("consent_for_treatment_description", "a_consent_description")])
        _decorate_questionnaire(imms, headers)
        expected_consent = {"linkId": "Consent", "answer": [{"valueCoding": {"display": "a_consent_description"}}]}
        self.assertDictEqual(imms["contained"][0]["item"][0], expected_consent)

    def test_care_setting_type(self):
        """Test that only non-empty care_setting_type values are added"""
        # care_setting_type: _code non-empty, _description empty
        imms = copy.deepcopy(self.imms)
        _decorate_questionnaire(imms, OrderedDict([("care_setting_type_code", "a_care_setting_code")]))
        expected_care_setting = {"linkId": "CareSetting", "answer": [{"valueCoding": {"code": "a_care_setting_code"}}]}
        self.assertDictEqual(imms["contained"][0]["item"][0], expected_care_setting)

        # care_setting_type: _code empty, _description non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_questionnaire(imms, OrderedDict([("care_setting_type_description", "a_care_setting_description")]))
        expected_care_setting = {
            "linkId": "CareSetting",
            "answer": [{"valueCoding": {"display": "a_care_setting_description"}}],
        }
        self.assertDictEqual(imms["contained"][0]["item"][0], expected_care_setting)

    def test_local_patient(self):
        """Test that only non-empty local_patient values are added"""
        # local_patient: _uri non-empty, _id empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("local_patient_uri", "a_local_patient_uri"), ("local_patient_id", "")])
        _decorate_questionnaire(imms, headers)
        expected_local_patient = {
            "linkId": "LocalPatient",
            "answer": [{"valueReference": {"identifier": {"system": "a_local_patient_uri"}}}],
        }
        self.assertDictEqual(imms["contained"][0]["item"][0], expected_local_patient)

        # local_patient: _uri empty, _id non-empty
        imms = copy.deepcopy(self.imms)
        headers = OrderedDict([("local_patient_uri", ""), ("local_patient_id", "a_local_patient_id")])
        _decorate_questionnaire(imms, headers)
        expected_local_patient = {
            "linkId": "LocalPatient",
            "answer": [{"valueReference": {"identifier": {"value": "a_local_patient_id"}}}],
        }
        self.assertDictEqual(imms["contained"][0]["item"][0], expected_local_patient)

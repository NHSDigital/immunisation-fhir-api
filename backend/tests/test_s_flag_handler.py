import unittest

from s_flag_handler import handle_s_flag


class TestRemovePersonalInfo(unittest.TestCase):
    input_immunization = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Practitioner",
                "id": "Pract1",
                "identifier": [
                    {
                        "system": "https://fhir.hl7.org.uk/Id/nmc-number",
                        "value": "99A9999A",
                    }
                ],
                "name": [{"family": "Nightingale", "given": ["Florence"]}],
            },
            {
                "resourceType": "Patient",
                "id": "Pat1",
                "identifier": [
                    {
                        "extension": [
                            {
                                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
                                "valueCodeableConcept": {
                                    "coding": [
                                        {
                                            "system": "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland",
                                            "code": "01",
                                            "display": "Number present and verified",
                                        }
                                    ]
                                },
                            }
                        ],
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": "9000000009",
                    }
                ],
                "name": [{"family": "Taylor", "given": ["Sarah"]}],
                "gender": "unknown",
                "birthDate": "1965-02-28",
                "address": [{"postalCode": "EC1A 1BB"}],
            },
            {
                "resourceType": "QuestionnaireResponse",
                "questionnaire": "Questionnaire/1",
                "status": "completed",
                "item": [
                    {
                        "linkId": "Consent",
                        "answer": [
                            {"valueCoding": {"code": "snomed", "display": "free text"}}
                        ],
                    },
                    {
                        "linkId": "Example",
                        "answer": [
                            {"valueCoding": {"system": "snomed", "code": "M242ND"}}
                        ],
                    },
                ],
            },
        ],
        "patient": {"reference": "#Pat1"},
        "performer": [
            {"actor": {"reference": "#Pract1"}},
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/test-organization-code",
                        "value": "B0C4P",
                    },
                    "display": "Acme Healthcare",
                }
            },
        ],
        "reportOrigin": {"text": "sample"},
        "location": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                "value": "B0C4P",
            }
        },
    }

    def test_remove_personal_info(self):
        expected_output = {
            "resourceType": "Immunization",
            "contained": [
                {
                    "resourceType": "Practitioner",
                    "id": "Pract1",
                },
                {
                    "resourceType": "Patient",
                    "id": "Pat1",
                    "identifier": [
                        {
                            "extension": [
                                {
                                    "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
                                    "valueCodeableConcept": {
                                        "coding": [
                                            {
                                                "system": "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland",
                                                "code": "01",
                                                "display": "Number present and verified",
                                            }
                                        ]
                                    },
                                }
                            ],
                            "system": "https://fhir.nhs.uk/Id/nhs-number",
                            "value": "9000000009",
                        }
                    ],
                },
                {
                    "resourceType": "QuestionnaireResponse",
                    "questionnaire": "Questionnaire/1",
                    "status": "completed",
                    "item": [
                        {
                            "linkId": "Example",
                            "answer": [
                                {"valueCoding": {"system": "snomed", "code": "M242ND"}}
                            ],
                        },
                    ],
                },
            ],
            "patient": {"reference": "#Pat1"},
            "performer": [
                {"actor": {"reference": "#Pract1"}},
                {
                    "actor": {
                        "type": "Organization",
                        "identifier": {
                            "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                            "value": "N2N9I",
                        },
                    }
                },
            ],
        }

        patient = {"meta": {"security": [{"code": "R"}]}}

        result = handle_s_flag(self.input_immunization, patient)
        self.assertEqual(result, expected_output)

    def test_when_missing_patient_fields_do_not_remove_personal_info(self):
        expected_output = self.input_immunization

        patient = {"meta": {}}

        result = handle_s_flag(self.input_immunization, patient)
        self.assertEqual(result, expected_output)

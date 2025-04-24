from decimal import Decimal


class ForwarderValues:

    MOCK_ENVIRONMENT_DICT = {
        "DYNAMODB_TABLE_NAME": "immunisation-batch-internal-dev-imms-test-table",
        "ENVIRONMENT": "internal-dev-test",
    }

    EXPECTED_KEYS = [
        "file_key",
        "row_id",
        "created_at_formatted_string",
        "local_id",
        "imms_id",
        "operation_requested",
    ]

    EXPECTED_KEYS_DIAGNOSTICS = [
        "file_key",
        "row_id",
        "created_at_formatted_string",
        "local_id",
        "diagnostics",
    ]

    EXPECTED_VALUES = {
        "file_key": "test_file_key",
        "created_at_formatted_string": "2025-01-24T12:00:00Z",
        "supplier": "test_supplier",
        "vaccine_type": "RSV",
        "local_id": "local-1",
    }

    EXPECTED_TABLE_ITEM_REINSTATED = {
        "PatientPK": "Patient#9732928395",
        "IdentifierPK": "https://www.ravs.england.nhs.uk/#UPDATE_TEST",
        "PatientSK": "RSV#4d2ac1eb-080f-4e54-9598-f2d53334687r",
        "Operation": "UPDATE",
        "SupplierSystem": "test_supplier",
        "DeletedAt": "reinstated",
    }
    EXPECTED_TABLE_ITEM = {
        "PatientPK": "Patient#9732928395",
        "IdentifierPK": "https://www.ravs.england.nhs.uk/#UPDATE_TEST",
        "PatientSK": "RSV#4d2ac1eb-080f-4e54-9598-f2d53334687r",
        "Operation": "UPDATE",
        "SupplierSystem": "test_supplier",
    }


class Urls:
    """Urls which are expected to be used within the FHIR Immunization Resource json data"""

    NHS_NUMBER = "https://fhir.nhs.uk/Id/nhs-number"
    vaccination_procedure = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    SNOMED = "http://snomed.info/sct"


GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE = (
    "Unable to process request. Issue may be transient."
)


class TargetDiseaseElements:
    """
    Class containing target disease elements for use in tests.
    IMPORTANT: THE VALUES ARE INTENTIONALLY HARD CODED FOR TESTING PURPOSES.
    """

    rsv_display = "Respiratory syncytial virus infection (disorder)"
    covid19_display = (
        "Disease caused by severe acute respiratory syndrome coronavirus 2"
    )

    RSV = [
        {
            "coding": [
                {"system": Urls.SNOMED, "code": "55735004", "display": rsv_display}
            ]
        }
    ]
    Decimal_number = Decimal("0.3")


class MockFhirImmsResources:
    """
    Mock FHIR Immunization Resources for use in tests.
    Each resource is mapped from the corresponding fields dictionary.
    """

    all_fields = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Patient",
                "id": "Patient1",
                "identifier": [{"system": Urls.NHS_NUMBER, "value": "9732928395"}],
                "name": [{"family": "PEEL", "given": ["PHYLIS"]}],
                "gender": "male",
                "birthDate": "2008-02-17",
                "address": [{"postalCode": "WD25 0DZ"}],
            },
            {
                "resourceType": "Practitioner",
                "id": "Practitioner1",
                "name": [{"family": "O'Reilly", "given": ["Ellena"]}],
            },
        ],
        "extension": [
            {
                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": Urls.SNOMED,
                            "code": "956951000000104",
                            "display": "RSV vaccination in pregnancy (procedure)",
                        }
                    ]
                },
            }
        ],
        "identifier": [
            {
                "system": "https://www.ravs.england.nhs.uk/",
                "value": "RSV_002",
            }
        ],
        "status": "completed",
        "vaccineCode": {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": "42223111000001107",
                    "display": "Quadrivalent influenza vaccine (split virion, inactivated)",
                }
            ]
        },
        "patient": {"reference": "#Patient1"},
        "occurrenceDateTime": "2024-09-04T18:33:25+00:00",
        "recorded": "2024-09-04",
        "primarySource": True,
        "manufacturer": {"display": "Sanofi Pasteur"},
        "location": {
            "identifier": {
                "value": "RJC02",
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
            }
        },
        "lotNumber": "BN92478105653",
        "expirationDate": "2024-09-15",
        "site": {
            "coding": [
                {"system": Urls.SNOMED, "code": "368209003", "display": "Right arm"}
            ]
        },
        "route": {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": "1210999013",
                    "display": "Intradermal use",
                }
            ]
        },
        "doseQuantity": {
            "value": 0.3,
            "unit": "Inhalation - unit of product usage",
            "system": Urls.SNOMED,
            "code": "2622896019",
        },
        "performer": [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                        "value": "RVVKC",
                    },
                }
            },
            {"actor": {"reference": "#Practitioner1"}},
        ],
        "reasonCode": [
            {"coding": [{"code": "1037351000000105", "system": Urls.SNOMED}]}
        ],
        "protocolApplied": [
            {
                "targetDisease": [
                    {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "55735004",
                                "display": "Respiratory syncytial virus infection (disorder)",
                            }
                        ]
                    }
                ],
                "doseNumberPositiveInt": 1,
            }
        ],
    }

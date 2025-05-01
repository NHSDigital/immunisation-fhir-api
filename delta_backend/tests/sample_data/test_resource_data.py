"""
# This module provides a function to generate a sample FHIR Immunization resource
"""


def get_test_data_resource():
    """
    The returned resource includes details about the practitioner, patient,
    vaccine code, location, and other relevant fields.
    """
    return {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Practitioner",
                "id": "Pract1",
                "name": [{"family": "O'Reilly", "given": ["Ellena"]}],
            },
            {
                "resourceType": "Patient",
                "id": "Pat1",
                "identifier": [
                    {
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": "9674963871",
                    }
                ],
                "name": [{"family": "GREIR", "given": ["SABINA"]}],
                "gender": "female",
                "birthDate": "2019-01-31",
                "address": [{"postalCode": "GU14 6TU"}],
            },
        ],
        "extension": [
            {
                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "1303503001",
                            "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)",
                        }
                    ]
                },
            }
        ],
        "identifier": [
            {
                "system": "https://www.ravs.england.nhs.uk/",
                "value": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1",
            }
        ],
        "status": "completed",
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "42605811000001109",
                    "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)",
                }
            ]
        },
        "patient": {"reference": "#Pat1"},
        "occurrenceDateTime": "2024-06-10T18:33:25+00:00",
        "recorded": "2024-06-10T18:33:25+00:00",
        "primarySource": True,
        "manufacturer": {"display": "Pfizer"},
        "location": {
            "type": "Location",
            "identifier": {
                "value": "J82067",
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
            },
        },
        "lotNumber": "RSVTEST",
        "expirationDate": "2024-12-31",
        "site": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "368208006",
                    "display": "Left upper arm structure (body structure)",
                }
            ]
        },
        "route": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "78421000",
                    "display": "Intramuscular route (qualifier value)",
                }
            ]
        },
        "doseQuantity": {
            "value": 0.5,
            "unit": "Milliliter (qualifier value)",
            "system": "http://unitsofmeasure.org",
            "code": "258773002",
        },
        "performer": [
            {"actor": {"reference": "#Pract1"}},
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                        "value": "X0X0X",
                    },
                }
            },
        ],
        "reasonCode": [
            {"coding": [{"code": "Test", "system": "http://snomed.info/sct"}]}
        ],
        "protocolApplied": [
            {
                "targetDisease": [
                    {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "840539006",
                                "display": "Disease caused by severe acute respiratory syndrome coronavirus 2",
                            }
                        ]
                    }
                ],
                "doseNumberPositiveInt": 1,
            }
        ],
        "id": "ca8ba2c6-2383-4465-b456-c1174c21cf31",
    }

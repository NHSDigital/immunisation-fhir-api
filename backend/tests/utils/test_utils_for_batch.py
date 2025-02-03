class ForwarderValues:

    mandatory_fields_only = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Patient",
                "id": "Patient1",
                "name": [{"family": "PEEL", "given": ["PHYLIS"]}],
                "gender": "male",
                "birthDate": "2008-02-17",
                "address": [{"postalCode": "WD25 0DZ"}],
            },
        ],
        "extension": [
            {
                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "Snomed URLs",
                            "code": "956951000000104",
                        }
                    ]
                },
            }
        ],
        "identifier": [
            {
                "system": "https://www.ravs.england.nhs.uk/",
                "value": "RSV_VALUE",
            }
        ],
        "status": "completed",
        "vaccineCode": {"coding": [{"system": "null codes", "code": "NAVU", "display": "Not available"}]},
        "patient": {"reference": "#Patient1"},
        "occurrenceDateTime": "2024-09-04T18:33:25+00:00",
        "recorded": "2024-09-04",
        "primarySource": True,
        "location": {"identifier": {"value": "RJC02", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}},
        "performer": [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "RVVKC"},
                }
            },
        ],
        "protocolApplied": [
            {
                "targetDisease": "RSV",
                "doseNumberString": "Dose sequence not recorded",
            }
        ],
    }

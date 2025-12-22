from decimal import Decimal

VALID_FHIR_IMMUNISATION = {
    "resourceType": "Immunization",
    "contained": [
        {
            "resourceType": "Practitioner",
            "id": "Pract1",
            "name": [{"family": "Nightingale", "given": ["Florence"]}],
        },
        {
            "resourceType": "Patient",
            "id": "Pat1",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "9000000009",
                }
            ],
            "name": [{"family": "Trailor", "given": ["Sam"]}],
            "gender": "unknown",
            "birthDate": "1965-02-28",
            "address": [{"postalCode": "EC1A 1BB"}],
        },
    ],
    "extension": [
        {
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "13246814444444",
                        "display": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)",
                        "extension": [
                            {
                                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
                                "valueString": "Test Value string 123456 COVID vaccination",
                            },
                            {
                                "url": "http://hl7.org/fhir/StructureDefinition/coding-sctdescid",
                                "valueId": "5306706018",
                            },
                        ],
                    }
                ]
            },
        }
    ],
    "identifier": [
        {
            "system": "https://supplierABC/identifiers/vacc",
            "value": "ACME-vacc123456",
        }
    ],
    "status": "completed",
    "vaccineCode": {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "39114911000001105",
                "display": "COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (AstraZeneca UK Ltd) (product)",
            }
        ]
    },
    "patient": {"reference": "#Pat1"},
    "occurrenceDateTime": "2024-05-11T12:00:00+00:00",
    "recorded": "2024-05-15",
    "primarySource": True,
    "manufacturer": {"display": "AstraZeneca Ltd"},
    "location": {
        "type": "Location",
        "identifier": {
            "value": "EC1111",
            "system": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
    },
    "lotNumber": "4120Z001",
    "expirationDate": "2024-12-02",
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
        "value": str(Decimal(0.5)),
        "unit": "milliliter",
        "system": "http://snomed.info/sct",
        "code": "258773002",
    },
    "performer": [
        {"actor": {"reference": "#Pract1"}},
        {
            "actor": {
                "type": "Organization",
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": "B0C4P",
                },
            }
        },
    ],
    "reasonCode": [{"coding": [{"code": "443684005", "system": "http://snomed.info/sct"}]}],
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
}

VALID_BATCH_IMMUNISATION = {
    "NHS_NUMBER": "9000000009",
    "PERSON_FORENAME": "JOHN",
    "PERSON_SURNAME": "DOE",
    "PERSON_DOB": "19801231",
    "PERSON_GENDER_CODE": "1",
    "PERSON_POSTCODE": "AB12 3CD",
    "DATE_AND_TIME": "20240511T120000",
    "SITE_CODE": "RJ1",
    "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
    "UNIQUE_ID": "ACME-vacc123456",
    "UNIQUE_ID_URI": "https://supplierABC/identifiers/vacc",
    "ACTION_FLAG": "UPDATE",
    "PERFORMING_PROFESSIONAL_FORENAME": "ALICE",
    "PERFORMING_PROFESSIONAL_SURNAME": "SMITH",
    "RECORDED_DATE": "20240515",
    "PRIMARY_SOURCE": "True",
    "VACCINATION_PROCEDURE_CODE": "1324681000000101",
    "VACCINATION_PROCEDURE_TERM": "Procedure Term",
    "DOSE_SEQUENCE": "1",
    "VACCINE_PRODUCT_CODE": "VACC123",
    "VACCINE_PRODUCT_TERM": "Vaccine Term",
    "VACCINE_MANUFACTURER": "Manufacturer XYZ",
    "BATCH_NUMBER": "BATCH001",
    "EXPIRY_DATE": "20241202",
    "SITE_OF_VACCINATION_CODE": "368208006",
    "SITE_OF_VACCINATION_TERM": "Left upper arm structure (body structure)",
    "ROUTE_OF_VACCINATION_CODE": "78421000",
    "ROUTE_OF_VACCINATION_TERM": "Intramuscular route (qualifier value)",
    "DOSE_AMOUNT": "0.5",
    "DOSE_UNIT_CODE": "258773002",
    "DOSE_UNIT_TERM": "milliliter",
    "INDICATION_CODE": "443684005",
    "LOCATION_CODE": "X99999",
    "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
}

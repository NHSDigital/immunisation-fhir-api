from decimal import Decimal
from helpers.mappings import EventName, Operation
from sample_data.test_resource_data import get_test_data_resource
import json
from typing import List


class RecordConfig:
    def __init__(self, event_name, operation, imms_id, expected_action_flag=None, supplier="EMIS"):
        self.event_name = event_name
        self.operation = operation
        self.supplier = supplier
        self.imms_id = imms_id
        self.expected_action_flag = expected_action_flag


class ValuesForTests:

    MOCK_ENVIRONMENT_DICT = {
        "DYNAMODB_TABLE_NAME": "immunisation-batch-internal-dev-imms-test-table",
        "ENVIRONMENT": "internal-dev-test",
    }

    json_data = {
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
                "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9000000009"}],
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
                        }
                    ]
                },
            }
        ],
        "identifier": [{"system": "https://supplierABC/identifiers/vacc", "value": "ACME-vacc123456"}],
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
        "occurrenceDateTime": "2021-02-07T13:28:17+00:00",
        "recorded": "2021-02-07T13:28:17+00:00",
        "primarySource": True,
        "manufacturer": {"display": "AstraZeneca Ltd"},
        "location": {
            "type": "Location",
            "identifier": {"value": "EC1111", "system": "https://fhir.nhs.uk/Id/ods-organization-code"},
        },
        "lotNumber": "4120Z001",
        "expirationDate": "2021-07-02",
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
            "system": "http://unitsofmeasure.org",
            "code": "ml",
        },
        "performer": [
            {"actor": {"reference": "#Pract1"}},
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
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

    json_value_for_test = json.dumps(json_data)

    @staticmethod
    def get_multi_record_event(records_config: List[RecordConfig]):
        records = []
        for config in records_config:
            # Extract values from the config dictionary
            imms_id = config.imms_id
            event_name = config.event_name
            operation = config.operation
            supplier = config.supplier

            # Generate record using the provided configuration
            records.append(
                ValuesForTests.get_test_event_record(
                    imms_id=imms_id,
                    event_name=event_name,
                    operation=operation,
                    supplier=supplier,
                )
            )
        return {"Records": records}

    @staticmethod
    def get_event(event_name=EventName.CREATE, operation=Operation.CREATE, supplier="EMIS", imms_id="12345"):
        """Create test event for the handler function."""
        return {
            "Records": [
                ValuesForTests.get_event_record(imms_id, event_name, operation, supplier)
            ]
        }

    @staticmethod
    def get_event_record(imms_id, event_name, operation, supplier="EMIS"):
        pk = f"covid#{imms_id}"
        if operation != Operation.DELETE_PHYSICAL:
            return{
                "eventName": event_name,
                "dynamodb": {
                    "ApproximateCreationDateTime": 1690896000,
                    "NewImage": {
                        "PK": {"S": pk},
                        "PatientSK": {"S": pk},
                        "IdentifierPK": {"S": "system#1"},
                        "Operation": {"S": operation},
                        "SupplierSystem": {"S": supplier},
                        "Resource": {
                            "S": json.dumps(get_test_data_resource()),
                        }
                    }
                }
            }
        else:
            return {
                "eventName": event_name,
                "dynamodb": {
                    "ApproximateCreationDateTime": 1690896000,
                    "Keys": {
                        "PK": {"S": pk},
                        "PatientSK": {"S": pk},
                        "SupplierSystem": {"S": supplier},
                        "Resource": {
                            "S": json.dumps(get_test_data_resource()),
                        }
                    }
                }
            }

    expected_static_values = {
        "VaccineType": "covid19",
        "SupplierSystem": "EMIS",
        "Source": "test-source",
        "ImmsID": "12345",
    }

    @staticmethod
    def get_expected_imms(expected_action_flag):
        """Returns expected Imms JSON data with the given action flag."""
        return {
                "NHS_NUMBER": "9000000009",
                "PERSON_FORENAME": "Sam",
                "PERSON_SURNAME": "Trailor",
                "PERSON_DOB": "19650228",
                "PERSON_GENDER_CODE": "0",
                "PERSON_POSTCODE": "EC1A 1BB",
                "DATE_AND_TIME": "20210207T13281700",
                "SITE_CODE": "B0C4P",
                "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
                "UNIQUE_ID": "ACME-vacc123456",
                "UNIQUE_ID_URI": "https://supplierABC/identifiers/vacc",
                "ACTION_FLAG": expected_action_flag,
                "PERFORMING_PROFESSIONAL_FORENAME": "Florence",
                "PERFORMING_PROFESSIONAL_SURNAME": "Nightingale",
                "RECORDED_DATE": "20210207",
                "PRIMARY_SOURCE": True,
                "VACCINATION_PROCEDURE_CODE": "13246814444444",
                "VACCINATION_PROCEDURE_TERM": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)",
                "DOSE_SEQUENCE": 1,
                "VACCINE_PRODUCT_CODE": "39114911000001105",
                "VACCINE_PRODUCT_TERM": "COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (AstraZeneca UK Ltd) (product)",
                "VACCINE_MANUFACTURER": "AstraZeneca Ltd",
                "BATCH_NUMBER": "4120Z001",
                "EXPIRY_DATE": "20210702",
                "SITE_OF_VACCINATION_CODE": "368208006",
                "SITE_OF_VACCINATION_TERM": "Left upper arm structure (body structure)",
                "ROUTE_OF_VACCINATION_CODE": "78421000",
                "ROUTE_OF_VACCINATION_TERM": "Intramuscular route (qualifier value)",
                "DOSE_AMOUNT": "0.5",
                "DOSE_UNIT_CODE": "",
                "DOSE_UNIT_TERM": "milliliter",
                "INDICATION_CODE": "443684005",
                "LOCATION_CODE": "EC1111",
                "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
                "CONVERSION_ERRORS": []
            }

    expected_imms = {
            "NHS_NUMBER": "9000000009",
            "PERSON_FORENAME": "Sam",
            "PERSON_SURNAME": "Trailor",
            "PERSON_DOB": "19650228",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "EC1A 1BB",
            "DATE_AND_TIME": "20210207T13281700",
            "SITE_CODE": "B0C4P",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "ACME-vacc123456",
            "UNIQUE_ID_URI": "https://supplierABC/identifiers/vacc",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Florence",
            "PERFORMING_PROFESSIONAL_SURNAME": "Nightingale",
            "RECORDED_DATE": "20210207",
            "PRIMARY_SOURCE": True,
            "VACCINATION_PROCEDURE_CODE": "13246814444444",
            "VACCINATION_PROCEDURE_TERM": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)",
            "DOSE_SEQUENCE": 1,
            "VACCINE_PRODUCT_CODE": "39114911000001105",
            "VACCINE_PRODUCT_TERM": "COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (AstraZeneca UK Ltd) (product)",
            "VACCINE_MANUFACTURER": "AstraZeneca Ltd",
            "BATCH_NUMBER": "4120Z001",
            "EXPIRY_DATE": "20210702",
            "SITE_OF_VACCINATION_CODE": "368208006",
            "SITE_OF_VACCINATION_TERM": "Left upper arm structure (body structure)",
            "ROUTE_OF_VACCINATION_CODE": "78421000",
            "ROUTE_OF_VACCINATION_TERM": "Intramuscular route (qualifier value)",
            "DOSE_AMOUNT": "0.5",
            "DOSE_UNIT_CODE": "",
            "DOSE_UNIT_TERM": "milliliter",
            "INDICATION_CODE": "443684005",
            "LOCATION_CODE": "EC1111",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "CONVERSION_ERRORS": []
        }

    expected_imms2 = {
            "NHS_NUMBER": "9000000009",
            "PERSON_FORENAME": "Sam",
            "PERSON_SURNAME": "Trailor",
            "PERSON_DOB": "19650228",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "EC1A 1BB",
            "DATE_AND_TIME": "20210207T13281700",
            "SITE_CODE": "B0C4P",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "ACME-vacc123456",
            "UNIQUE_ID_URI": "https://supplierABC/identifiers/vacc",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Florence",
            "PERFORMING_PROFESSIONAL_SURNAME": "Nightingale",
            "RECORDED_DATE": "20210207",
            "PRIMARY_SOURCE": True,
            "VACCINATION_PROCEDURE_CODE": "13246814444444",
            "VACCINATION_PROCEDURE_TERM": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)",
            "DOSE_SEQUENCE": 1,
            "VACCINE_PRODUCT_CODE": "39114911000001105",
            "VACCINE_PRODUCT_TERM": "COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (AstraZeneca UK Ltd) (product)",
            "VACCINE_MANUFACTURER": "AstraZeneca Ltd",
            "BATCH_NUMBER": "4120Z001",
            "EXPIRY_DATE": "20210702",
            "SITE_OF_VACCINATION_CODE": "368208006",
            "SITE_OF_VACCINATION_TERM": "Left upper arm structure (body structure)",
            "ROUTE_OF_VACCINATION_CODE": "78421000",
            "ROUTE_OF_VACCINATION_TERM": "Intramuscular route (qualifier value)",
            "DOSE_AMOUNT": "0.5",
            "DOSE_UNIT_CODE": "",
            "DOSE_UNIT_TERM": "milliliter",
            "INDICATION_CODE": "443684005",
            "LOCATION_CODE": "EC1111",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "CONVERSION_ERRORS": []
        }


class ErrorValuesForTests:

    json_dob_error = {
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
                "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": ""}],
                "name": [{"family": "Trailor", "given": ["Sam"]}],
                "gender": "unknown",
                "birthDate": "196513-28",
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
                        }
                    ]
                },
            }
        ],
        "identifier": [{"system": "https://supplierABC/identifiers/vacc", "value": "ACME-vacc123456"}],
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
        "occurrenceDateTime": "2021-02-07T13:28:17+00:00",
        "recorded": "2021-02-07T13:28:17+00:00",
        "primarySource": True,
        "manufacturer": {"display": "AstraZeneca Ltd"},
        "location": {
            "type": "Location",
            "identifier": {"value": "E712", "system": "https://fhir.nhs.uk/Id/ods-organization-code"},
        },
        "lotNumber": "4120Z001",
        "expirationDate": "2021-07-02",
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
            "system": "http://unitsofmeasure.org",
            "code": "ml",
        },
        "performer": [
            {"actor": {"reference": "#Pract1"}},
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
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

    missing_json = {}

    @staticmethod
    def get_expected_imms_error_output(expected_action_flag):
        """Returns expected Imms JSON data with the given action flag."""
        return [
            {
                "NHS_NUMBER": "9000000009",
                "PERSON_FORENAME": "Sam",
                "PERSON_SURNAME": "Trailor",
                "PERSON_DOB": "19650228",
                "PERSON_GENDER_CODE": "0",
                "PERSON_POSTCODE": "EC1A 1BB",
                "DATE_AND_TIME": "20210207T132817",
                "SITE_CODE": "B0C4P",
                "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
                "UNIQUE_ID": "ACME-vacc123456",
                "UNIQUE_ID_URI": "https://supplierABC/identifiers/vacc",
                "ACTION_FLAG": "UPDATE",
                "PERFORMING_PROFESSIONAL_FORENAME": "Florence",
                "PERFORMING_PROFESSIONAL_SURNAME": "Nightingale",
                "RECORDED_DATE": "20210207",
                "PRIMARY_SOURCE": True,
                "VACCINATION_PROCEDURE_CODE": "13246814444444",
                "VACCINATION_PROCEDURE_TERM": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)",
                "DOSE_SEQUENCE": 1,
                "VACCINE_PRODUCT_CODE": "39114911000001105",
                "VACCINE_PRODUCT_TERM": "COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (AstraZeneca UK Ltd) (product)",
                "VACCINE_MANUFACTURER": "AstraZeneca Ltd",
                "BATCH_NUMBER": "4120Z001",
                "EXPIRY_DATE": "20210702",
                "SITE_OF_VACCINATION_CODE": "368208006",
                "SITE_OF_VACCINATION_TERM": "Left upper arm structure (body structure)",
                "ROUTE_OF_VACCINATION_CODE": "78421000",
                "ROUTE_OF_VACCINATION_TERM": "Intramuscular route (qualifier value)",
                "DOSE_AMOUNT": "0.5",
                "DOSE_UNIT_CODE": "",
                "DOSE_UNIT_TERM": "milliliter",
                "INDICATION_CODE": "443684005",
                "LOCATION_CODE": "E712",
                "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
                "CONVERSION_ERRORS": []
            }
        ]

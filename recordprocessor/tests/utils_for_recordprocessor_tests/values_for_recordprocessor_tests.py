"""Values for use in tests"""

from unittest.mock import patch
import json
from decimal import Decimal
from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from constants import Urls, AuditTableKeys


REGION_NAME = "eu-west-2"


class MockUniqueIdUris:
    """Class containing mock unique ID URIs for use in tests"""

    RAVS = "https://www.ravs.england.nhs.uk/"


class MockUniqueIds:
    """Class containing mock unique IDs for use in tests"""

    COVID19_001 = "COVID_19_001"
    RSV_001 = "RSV_001"
    RSV_002 = "RSV_002"


class MockLocalIds:
    """Class containing mock local IDs for use in tests"""

    @staticmethod
    def create_local_id(unique_id: str, unique_id_uri: str) -> str:
        """Create a mock local ID. Default is to use the test unique ID URI."""
        return f"{unique_id}^{unique_id_uri}"

    COVID19_001_RAVS = create_local_id(MockUniqueIds.COVID19_001, MockUniqueIdUris.RAVS)
    RSV_001_RAVS = create_local_id(MockUniqueIds.RSV_001, MockUniqueIdUris.RAVS)
    RSV_002_RAVS = create_local_id(MockUniqueIds.RSV_002, MockUniqueIdUris.RAVS)


class TargetDiseaseElements:
    """
    Class containing target disease elements for use in tests.
    IMPORTANT: THE VALUES ARE INTENTIONALLY HARD CODED FOR TESTING PURPOSES.
    """

    rsv_display = "Respiratory syncytial virus infection (disorder)"
    covid19_display = "Disease caused by severe acute respiratory syndrome coronavirus 2"

    RSV = [{"coding": [{"system": Urls.SNOMED, "code": "55735004", "display": rsv_display}]}]

    COVID19 = [{"coding": [{"system": Urls.SNOMED, "code": "840539006", "display": covid19_display}]}]

    FLU = [{"coding": [{"system": Urls.SNOMED, "code": "6142004", "display": "Influenza"}]}]

    MMR = [
        {"coding": [{"system": Urls.SNOMED, "code": "14189004", "display": "Measles"}]},
        {"coding": [{"system": Urls.SNOMED, "code": "36989005", "display": "Mumps"}]},
        {"coding": [{"system": Urls.SNOMED, "code": "36653000", "display": "Rubella"}]},
    ]


class MockFileRows:
    """Class containing mock file rows for use in ValidMockFileContent class"""

    HEADERS = (
        "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
        "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
        "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
        "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
        "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
        "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
        "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
        "LOCATION_CODE|LOCATION_CODE_TYPE_URI"
    )

    NEW = (
        '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
        f'"https://fhir.nhs.uk/Id/ods-organization-code"|"{MockUniqueIds.RSV_001}"|"{MockUniqueIdUris.RAVS}"|'
        '"new"|"Ellena"|"O\'Reilly"|"20240101"|"TRUE"|'
        '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
        '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
        '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
        '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
        '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"'
    )

    UPDATE = (
        '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
        f'"https://fhir.nhs.uk/Id/ods-organization-code"|"{MockUniqueIds.COVID19_001}"|"{MockUniqueIdUris.RAVS}"|'
        '"update"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
        '"Administration of COVID-19 vaccine product (procedure)"|'
        '1|"1234567890"|'
        '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
        '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
        '"385219009"|"Intramuscular route (qualifier value)"|'
        '"0.3"|"258773002"|"Milliliter (qualifier value)"|"Routine"|'
        '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
    )

    DELETE = (
        '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
        f'"https://fhir.nhs.uk/Id/ods-organization-code"|"{MockUniqueIds.COVID19_001}"|"{MockUniqueIdUris.RAVS}"|'
        '"delete"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
        '"Administration of COVID-19 vaccine product (procedure)"|'
        '1|"1234567890"|'
        '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
        '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
        '"385219009"|"Intramuscular route (qualifier value)"|'
        '"0.3"|"258773002"|"Milliliter (qualifier value)"|"Routine"|'
        '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
    )


class ValidMockFileContent:
    """Class containing valid file content for use in tests"""

    headers = MockFileRows.HEADERS
    with_new = headers + "\n" + MockFileRows.NEW
    with_update = headers + "\n" + MockFileRows.UPDATE
    with_delete = headers + "\n" + MockFileRows.DELETE
    with_update_and_delete = headers + "\n" + MockFileRows.UPDATE + "\n" + MockFileRows.DELETE
    with_new_and_update = headers + "\n" + MockFileRows.NEW + "\n" + MockFileRows.UPDATE
    with_new_and_update_and_delete = (
        headers + "\n" + MockFileRows.NEW + "\n" + MockFileRows.UPDATE + "\n" + MockFileRows.DELETE
    )


class FileDetails:
    """
    Class to create and hold values for a mock file, based on the vaccine type, supplier and ods code.
    NOTE: Supplier and ODS code are hardcoded rather than mapped, for testing purposes.
    NOTE: The permissions_list and permissions_config are examples of full permissions for the suppler for the
    vaccine type.
    """

    def __init__(self, vaccine_type: str, supplier: str, ods_code: str, file_number: int = 1):
        self.name = f"{vaccine_type.upper()}/ {supplier.upper()} file"
        self.created_at_formatted_string = f"202{file_number}1120T12000000"
        self.file_key = f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv"
        self.inf_ack_file_key = (
            f"ack/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000"
            + f"_InfAck_{self.created_at_formatted_string}.csv"
        )
        self.ack_file_key = f"processedFile/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000_response.csv"
        self.vaccine_type = vaccine_type
        self.ods_code = ods_code
        self.supplier = supplier
        self.file_date_and_time_string = f"20000101T0000000{file_number}"
        self.message_id = f"{vaccine_type.lower()}_{supplier.lower()}_test_id"
        self.message_id_order = f"{vaccine_type.lower()}_{supplier.lower()}_test_id_{file_number}"
        self.full_permissions_list = [f"{vaccine_type}_FULL"]
        self.create_permissions_only = [f"{vaccine_type}_CREATE"]
        self.update_permissions_only = [f"{vaccine_type}_UPDATE"]
        self.delete_permissions_only = [f"{vaccine_type}_DELETE"]

        self.queue_name = f"{supplier}_{vaccine_type}"

        self.base_event = {
            "message_id": self.message_id,
            "vaccine_type": vaccine_type,
            "supplier": supplier,
            "filename": self.file_key,
            "created_at_formatted_string": self.created_at_formatted_string,
        }

        # Mock the event details which would be receeived from SQS message
        self.event_full_permissions_dict = {**self.base_event, "permission": self.full_permissions_list}
        self.event_create_permissions_only_dict = {**self.base_event, "permission": self.create_permissions_only}
        self.event_update_permissions_only_dict = {**self.base_event, "permission": self.update_permissions_only}
        self.event_delete_permissions_only_dict = {**self.base_event, "permission": self.delete_permissions_only}
        self.event_full_permissions = json.dumps(self.event_full_permissions_dict)
        self.event_create_permissions_only = json.dumps(self.event_create_permissions_only_dict)
        self.event_update_permissions_only = json.dumps(self.event_update_permissions_only_dict)
        self.event_delete_permissions_only = json.dumps(self.event_delete_permissions_only_dict)

        self.audit_table_entry = {
            AuditTableKeys.MESSAGE_ID: {"S": self.message_id_order},
            AuditTableKeys.FILENAME: {"S": self.file_key},
            AuditTableKeys.QUEUE_NAME: {"S": self.queue_name},
            AuditTableKeys.TIMESTAMP: {"S": self.created_at_formatted_string},
        }


class MockFileDetails:
    """Class containing mock file details for use in tests"""

    ravs_rsv_1 = FileDetails("RSV", "RAVS", "X26", file_number=1)
    ravs_rsv_2 = FileDetails("RSV", "RAVS", "X26", file_number=2)
    ravs_rsv_3 = FileDetails("RSV", "RAVS", "X26", file_number=3)
    ravs_rsv_4 = FileDetails("RSV", "RAVS", "X26", file_number=4)
    ravs_rsv_5 = FileDetails("RSV", "RAVS", "X26", file_number=5)
    rsv_ravs = FileDetails("RSV", "RAVS", "X26")
    rsv_emis = FileDetails("RSV", "EMIS", "8HK48")
    flu_emis = FileDetails("FLU", "EMIS", "YGM41")
    ravs_flu = FileDetails("FLU", "RSV", "X26")


class UnorderedFieldDictionaries:
    """
    Class containing dictionaries of the raw input fields and values.
    The dictionaries are not ordered and should therefore not be used in testing.
    They are used only for creating dictionaries in the MockFieldDictionaries class.
    """

    mandatory_fields = {
        "PERSON_FORENAME": "PHYLIS",
        "PERSON_SURNAME": "PEEL",
        "PERSON_DOB": "20080217",
        "PERSON_GENDER_CODE": "1",
        "PERSON_POSTCODE": "WD25 0DZ",
        "DATE_AND_TIME": "20240904T183325",
        "SITE_CODE": "RVVKC",
        "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        "UNIQUE_ID": MockUniqueIds.RSV_002,
        "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
        "ACTION_FLAG": "update",
        "RECORDED_DATE": "20240904",
        "PRIMARY_SOURCE": "TRUE",
        "VACCINATION_PROCEDURE_CODE": "956951000000104",
        "LOCATION_CODE": "RJC02",
        "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
    }

    non_mandatory_fields = {
        "NHS_NUMBER": "9732928395",
        "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
        "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
        "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
        "DOSE_SEQUENCE": "1",
        "VACCINE_PRODUCT_CODE": "42223111000001107",
        "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
        "VACCINE_MANUFACTURER": "Sanofi Pasteur",
        "BATCH_NUMBER": "BN92478105653",
        "EXPIRY_DATE": "20240915",
        "SITE_OF_VACCINATION_CODE": "368209003",
        "SITE_OF_VACCINATION_TERM": "Right arm",
        "ROUTE_OF_VACCINATION_CODE": "1210999013",
        "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
        "DOSE_AMOUNT": "0.3",
        "DOSE_UNIT_CODE": "2622896019",
        "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
        "INDICATION_CODE": "1037351000000105",
    }

    critical_fields = {"ACTION_FLAG": "NEW", "UNIQUE_ID": "a_unique_id", "UNIQUE_ID_URI": "a_unique_id_uri"}


class MockFieldDictionaries:
    """
    Class containing dictionaries of the raw input fields and values for use in tests.
    All dictionaries are ordered to match the expected header order in the files
    """

    field_order = [
        "NHS_NUMBER",
        "PERSON_FORENAME",
        "PERSON_SURNAME",
        "PERSON_DOB",
        "PERSON_GENDER_CODE",
        "PERSON_POSTCODE",
        "DATE_AND_TIME",
        "SITE_CODE",
        "SITE_CODE_TYPE_URI",
        "UNIQUE_ID",
        "UNIQUE_ID_URI",
        "ACTION_FLAG",
        "PERFORMING_PROFESSIONAL_FORENAME",
        "PERFORMING_PROFESSIONAL_SURNAME",
        "RECORDED_DATE",
        "PRIMARY_SOURCE",
        "VACCINATION_PROCEDURE_CODE",
        "VACCINATION_PROCEDURE_TERM",
        "DOSE_SEQUENCE",
        "VACCINE_PRODUCT_CODE",
        "VACCINE_PRODUCT_TERM",
        "VACCINE_MANUFACTURER",
        "BATCH_NUMBER",
        "EXPIRY_DATE",
        "SITE_OF_VACCINATION_CODE",
        "SITE_OF_VACCINATION_TERM",
        "ROUTE_OF_VACCINATION_CODE",
        "ROUTE_OF_VACCINATION_TERM",
        "DOSE_AMOUNT",
        "DOSE_UNIT_CODE",
        "DOSE_UNIT_TERM",
        "INDICATION_CODE",
        "LOCATION_CODE",
        "LOCATION_CODE_TYPE_URI",
    ]

    all_fields = {
        key: (
            UnorderedFieldDictionaries.mandatory_fields.get(key)
            or UnorderedFieldDictionaries.non_mandatory_fields.get(key)
            or ""
        )
        for key in field_order
    }
    mandatory_fields_only = {key: (UnorderedFieldDictionaries.mandatory_fields.get(key) or "") for key in field_order}
    critical_fields_only = {key: (UnorderedFieldDictionaries.critical_fields.get(key) or "") for key in field_order}


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
                "value": MockUniqueIds.RSV_002,
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
        "location": {"identifier": {"value": "RJC02", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}},
        "lotNumber": "BN92478105653",
        "expirationDate": "2024-09-15",
        "site": {"coding": [{"system": Urls.SNOMED, "code": "368209003", "display": "Right arm"}]},
        "route": {"coding": [{"system": Urls.SNOMED, "code": "1210999013", "display": "Intradermal use"}]},
        "doseQuantity": {
            "value": Decimal("0.3"),
            "unit": "Inhalation - unit of product usage",
            "system": Urls.SNOMED,
            "code": "2622896019",
        },
        "performer": [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "RVVKC"},
                }
            },
            {"actor": {"reference": "#Practitioner1"}},
        ],
        "reasonCode": [{"coding": [{"code": "1037351000000105", "system": Urls.SNOMED}]}],
        "protocolApplied": [
            {
                "targetDisease": TargetDiseaseElements.RSV,
                "doseNumberPositiveInt": 1,
            }
        ],
    }

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
                            "system": Urls.SNOMED,
                            "code": "956951000000104",
                        }
                    ]
                },
            }
        ],
        "identifier": [
            {
                "system": "https://www.ravs.england.nhs.uk/",
                "value": MockUniqueIds.RSV_002,
            }
        ],
        "status": "completed",
        "vaccineCode": {"coding": [{"system": Urls.NULL_FLAVOUR_CODES, "code": "NAVU", "display": "Not available"}]},
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
                "targetDisease": TargetDiseaseElements.RSV,
                "doseNumberString": "Dose sequence not recorded",
            }
        ],
    }

    critical_fields = {
        "resourceType": "Immunization",
        "status": "completed",
        "vaccineCode": {"coding": [{"system": Urls.NULL_FLAVOUR_CODES, "code": "NAVU", "display": "Not available"}]},
        "identifier": [{"system": "a_unique_id_uri", "value": "a_unique_id"}],
        "protocolApplied": [
            {
                "targetDisease": TargetDiseaseElements.RSV,
                "doseNumberString": "Dose sequence not recorded",
            }
        ],
    }


class InfAckFileRows:
    """Class containing the expected rows of the InfAck file, for use in the tests"""

    HEADERS = (
        "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|"
        + "ISSUE_DETAILS_CODE|RESPONSE_TYPE|RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|"
        + "MESSAGE_DELIVERY"
    )

    success_row = "message_id|Success|Information|OK|20013|Technical|20013|Success|created_at_formatted_string|||True"

    failure_row = (
        "message_id|Failure|Fatal|Fatal Error|10001|Technical|10002|"
        + "Infrastructure Level Response Value - Processing Error|created_at_formatted_string|||False"
    )

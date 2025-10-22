"""Store values for use in tests"""

from dataclasses import dataclass
from decimal import Decimal

# Lists of data types for 'invalid data type' testing
integers = [-1, 0, 1]
floats = [-1.3, 0.0, 1.0, 2.5]
decimals = [Decimal("-1"), Decimal("0"), Decimal("1"), Decimal("-1.3"), Decimal("2.5")]
booleans = [True, False]
dicts = [{}, {"InvalidKey": "InvalidValue"}]
lists = [[], ["Invalid"]]
strings = ["", "invalid"]


@dataclass
class InvalidDataTypes:
    """Store lists of invalid data types for tests"""

    for_integers = [None] + floats + decimals + booleans + dicts + lists + strings
    for_decimals_or_integers = [None] + floats + booleans + dicts + lists + strings
    for_booleans = [None] + integers + floats + decimals + dicts + lists + strings
    for_dicts = [None] + integers + floats + decimals + booleans + lists + strings
    for_lists = [None] + integers + decimals + floats + booleans + dicts + strings
    for_strings = [None] + integers + floats + decimals + booleans + dicts + lists


@dataclass
class ValidValues:
    """Store valid values for tests"""

    nhs_number = "9990548609"

    for_date_times_strict_timezones = [
        "2000-01-01",  # Full date only
        "2000-01-01T00:00:00+00:00",  # Time and offset all zeroes
        "2025-05-20T18:26:30+01:00",  # Date with Time with no milliseconds and positive offset
        "2000-01-01T00:00:00+01:00",  # Time and offset all zeroes
        "1933-12-31T11:11:11+01:00",  # Positive offset (with hours and minutes not 0)
        "1933-12-31T11:11:11.1+00:00",  # DateTime with milliseconds to 1 decimal place
        "2000-01-01T00:00:00.000+00:00",  # DateTime with milliseconds to 3 decimal places
        "1933-12-31T11:11:11.111111+00:00",  # DateTime with milliseconds to 6 decimal places
    ]

    for_date_times_relaxed_timezones = for_date_times_strict_timezones + [
        "2000-01-01T00:00:00+05:00",  # Time and offset all zeroes
        "1933-12-31T11:11:11-01:00",  # Negative offset (with hours and minutes not 0)
        "1933-12-31T11:11:11.1-05:00",  # DateTime with milliseconds to 1 decimal place
    ]

    for_strings_with_any_length_chars = (
        "This is a really long string with more than 100 characters to test whether the validator is working well!! "
    )

    # Not a valid snomed code, but is valid coding format for format testing
    snomed_coding_element = {"system": "http://snomed.info/sct", "code": "ABC123", "display": "test"}

    valid_dose_quantity = [
        {"value": 3, "unit": "milliliter", "system": "http://unitsofmeasure.org", "code": "ml"},
        {"value": 2, "unit": "ml", "system": "http://snomed.info/sct", "code": "258773002"},
        {"value": 4, "unit": "ml", "system": "http://snomed.info/sct"},
        {"value": 5, "unit": "ml"},
    ]

    manufacturer_resource_id_Man1 = {"resourceType": "Manufacturer", "id": "Man1"}

    practitioner_resource_id_Pract1 = {"resourceType": "Practitioner", "id": "Pract1"}

    practitioner_resource_id_Pract2 = {"resourceType": "Practitioner", "id": "Pract2"}

    patient_resource_id_Pat1 = {"resourceType": "Patient", "id": "Pat1"}

    patient_resource_id_Pat2 = {"resourceType": "Patient", "id": "Pat2"}

    questionnnaire_resource_id_QR1 = {"resourceType": "QuestionnaireResponse", "id": "QR1", "status": "completed"}

    questionnaire_immunisation = {"linkId": "Immunisation", "answer": [{"valueReference": {"reference": "#"}}]}

    questionnaire_reduce_validation_true = {"linkId": "ReduceValidation", "answer": [{"valueBoolean": True}]}

    questionnaire_reduce_validation_false = {"linkId": "ReduceValidation", "answer": [{"valueBoolean": False}]}

    questionnaire_ip_address = {"linkId": "IpAddress", "answer": [{"valueString": "IP_ADDRESS"}]}

    performer_actor_organization = {
        "actor": {
            "type": "Organization",
            "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
            "display": "Acme Healthcare",
        }
    }

    performer_actor_reference_internal_Pract1 = {"actor": {"reference": "#Pract1"}}

    performer_actor_reference_internal_Pract2 = {"actor": {"reference": "#Pract2"}}

    performer = [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "display": "Acme Healthcare"}}]

    vaccination_procedure_coding_with_one_snomed_code = [
        {
            "system": "http://snomed.info/sct",
            "code": "1324681000000101",
            "display": "Administration of first dose of severe acute "
            + "respiratory syndrome coronavirus 2 vaccine (procedure)",
        },
    ]

    vaccination_procedure_coding_with_snomed_and_dmd_codes = [
        {
            "system": "http://snomed.info/sct",
            "code": "1324681000000101",
            "display": "Administration of first dose of severe acute "
            + "respiratory syndrome coronavirus 2 vaccine (procedure)",
        },
        {
            "system": "dm+d url",
            "code": "DUMMY DM+D CODE",
            "display": "Administration of first dose of severe acute "
            + "respiratory syndrome coronavirus 2 vaccine (procedure)",
        },
    ]

    dummy_coding_with_one_snomed_code = [
        {"system": "http://snomed.info/sct", "code": "DUMMY CODE 1", "display": "DUMMY TERM 1"},
    ]

    vaccination_procedure_with_one_snomed_code = {
        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
        "valueCodeableConcept": {"coding": vaccination_procedure_coding_with_one_snomed_code},
    }

    vaccination_procedure_with_snomed_and_dmd_codes = {
        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
        "valueCodeableConcept": {"coding": vaccination_procedure_coding_with_snomed_and_dmd_codes},
    }

    vaccination_situation_with_one_snomed_code = {
        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
        "valueCodeableConcept": {"coding": dummy_coding_with_one_snomed_code},
    }

    nhs_number_coding_item = {
        "system": "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland",
        "code": "NHS_NUMBER_STATUS_INDICATOR_CODE",
        "display": "NHS_NUMBER_STATUS_INDICATOR_DESCRIPTION",
    }

    nhs_number_verification_status = {
        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
        "valueCodeableConcept": {"coding": [nhs_number_coding_item]},
    }

    test_unique_id_uri = "https://www.ravs.england.nhs.uk/"
    test_local_id = f"0002_COVID19_v1_DOSE_1^{test_unique_id_uri}"

    occurrenceDateTime = "2021-02-07T13:28:17+00:00"

    date_before_occurenceDateTime = "1900-01-01T00:00:00+00:00"

    date_after_occurenceDateatetime = "2100-01-01T00:00:00+00:00"

    valid_name_4_instances = [
        {
            "use": "official",
            "family": "Tay",
            "given": ["Sa"],
            "period": {"end": date_before_occurenceDateTime},
        },
        {
            "use": "official",
            "family": "Taylor",
            "given": ["Sarah"],
            "period": {"start": date_before_occurenceDateTime, "end": date_after_occurenceDateatetime},
        },
        {"family": "Taylor", "given": ["Sar"]},
        {"use": "old", "family": "Tray", "given": ["Sarah"]},
    ]

    valid_name_4_instances_practitioner = [
        {
            "use": "official",
            "family": "Nightingale",
            "given": ["Florence"],
            "period": {"end": date_before_occurenceDateTime},
        },
        {
            "use": "official",
            "family": "Night",
            "given": ["Florence"],
            "period": {"start": date_before_occurenceDateTime, "end": date_after_occurenceDateatetime},
        },
        {"family": "Night", "given": ["Florence"]},
        {"use": "old", "family": "Tray", "given": ["Florence"]},
    ]


class NameInstances:
    """Class containing example name instances."""

    class ValidCurrent:
        """Name instances which are both valid and current"""

        given_and_family_only = {"given": ["a_given_name"], "family": "a_family_name"}

        with_use_official = {"given": ["a_given_name"], "family": "a_family_name", "use": "official"}

        with_period_start = {
            "given": ["a_given_name"],
            "family": "a_family_name",
            "period": {"start": ValidValues.date_before_occurenceDateTime},
        }

        with_period_end = {
            "given": ["a_given_name"],
            "family": "a_family_name",
            "period": {"end": ValidValues.date_after_occurenceDateatetime},
        }

        with_use_official_and_period_start_and_end = {
            "given": ["a_given_name"],
            "family": "a_family_name",
            "period": {
                "start": ValidValues.date_before_occurenceDateTime,
                "end": ValidValues.date_after_occurenceDateatetime,
            },
            "use": "official",
        }

        use_old = {"given": ["a_given_name"], "family": "a_family_name", "use": "old"}

    class ValidNonCurrent:
        """Name instances which are valid but not current"""

        before_period_start = {"given": ["a_given_name"], "family": "a_family_name", "period": {"start": "2100-01-01"}}

        after_period_end = {
            "given": ["a_given_name"],
            "family": "a_family_name",
            "period": {"end": ValidValues.date_before_occurenceDateTime},
        }

    class Invalid:
        """Name instances which are invalid"""

        family_name_only = {"family": "a_family_name"}

        given_name_only = {"given": ["a_given_name"]}

        family_name_only_with_use_official = {"family": "a_family_name", "use": "official"}

        family_name_only_with_use_official_and_period_start_and_end = {
            "family": "a_family_name",
            "period": {"start": "1900-01-01", "end": "2100-01-01"},
            "use": "official",
        }


@dataclass
class InvalidValues:
    """Store lists of invalid values for tests"""

    for_postal_codes = [
        "SW1  1AA",  # Too many spaces in divider
        "SW 1 1A",  # Too many space dividers
        "AAA0000AA",  # Too few space dividers
        " AA00 00AA",  # Invalid additional space at start
        "AA00 00AA ",  # Invalid additional space at end
        " AA0000AA",  # Space is incorrectly at start
        "AA0000AA ",  # Space is incorrectly at end
    ]

    for_date_string_formats = [
        # Strings which are not in acceptable date format
        "",  # Empty
        "invalid",  # With letters
        "20000101",  # Without dashes
        "200001-01",  # Missing first dash
        "2000-0101",  # Missing second dash
        "2000:01:01",  # Semi-colons instead of dashes
        "2000-01-011",  # Extra digit at end
        "12000-01-01",  # Extra digit at start
        "12000-01-021",  # Extra digit at start and end
        "99-01-01",  # Year represented without century (i.e. 2 digits instead of 4)
        "01-01-1999",  # DD-MM-YYYY format
        "01-01-99",  # DD-MM-YY format
        # Strings which are in acceptable date format, but are invalid dates
        "2000-00-01",  # Month 0
        "2000-13-01",  # Month 13
        "2000-01-00",  # Day 0
        "2000-01-32",  # Day 32
        "2000-02-30",  # Invalid combination of month and day
    ]

    # Strings which are not in acceptable date time format
    for_date_time_string_formats_for_relaxed_timezone = [
        "",  # Empty string
        "invalid",  # Invalid format
        "20000101",  # Date digits only (i.e. without hypens)
        "20000101000000",  # Date and time digits only
        "200001010000000000",  # Date, time and timezone digits only
        "2000-01-01T10:34:27",  # Date with Time only
        "2000-01-01T10:34:27.234",  # Date with Time and milliseconds
        "2000",  # Year only
        "2000-01",  # Year and month only
        "2000-01-01T00:00:00+00",  # Date and time with GMT timezone offset only in hours
        "2000-01-01T00:00:00+01",  # Date and time with BST timezone offset only in hours
        "12000-01-01T00:00:00+00:00",  # Extra character at start of string
        "2000-01-01T00:00:00+00:001",  # Extra character at end of string
        "12000-01-02T00:00:00-01:001",  # Extra characters at start and end of string
        "2000-01-0122:22:22+00:00",  # Missing T
        "2000-01-0122:22:22+00:00.000",  # Missing T (with milliseconds)
        "2000-01-01T222222+00:00",  # Missing time colons
        "2000-01-01T22:22:2200:00",  # Missing timezone indicator
        "2000-01-01T22:22:22-01",  # Timezone hours only
        "99-01-01T00:00:00+00:00",  # Missing century (i.e. only 2 digits for year)
        "01-01-2000T00:00:00+00:00",  # Date in wrong order (DD-MM-YYYY)
    ]

    # Strings which are in acceptable date time format, but are invalid dates, times or timezones
    for_date_times = [
        "2000-00-01T00:00:00+00:00",  # Month 00
        "2000-13-01T00:00:00+00:00",  # Month 13
        "2000-01-00T00:00:00+00:00",  # Day 00
        "2000-01-32T00:00:00+00:00",  # Day 32
        "2000-02-30T00:00:00+00:00",  # Invalid month and day combination (30th February)
        "2000-01-01T24:00:00+00:00",  # Hour 24
        "2000-01-01T00:60:00+00:00",  # Minute 60
        "2000-01-01T00:00:60+00:00",  # Second 60
        "2000-01-01T00:00:00+24:00",  # Timezone hour +24
        "2000-01-01T00:00:00-24:00",  # Timezone hour -24
        "2000-01-01T00:00:00+00:60",  # Timezone minute 60
    ]

    for_date_time_string_formats_for_strict_timezone = for_date_time_string_formats_for_relaxed_timezone + [
        "2000-01-01T22:22:22-0100",  # Missing timezone colon
        "2000-01-01T00:00:00-01:00",  # Date and time with negative GMT timezone offset
        "2000-01-01T00:00:00-05:00",  # Date and time with negative offset asides from GMT and BST
        "2000-01-01T00:00:00+05:00",  # Date and time with offset asides from GMT and BST
        "2000-01-01T00:00:00-00:00",  # Date and time with negative GMT timezone offset
    ]

    for_lists_of_strings_of_length_1 = [[1], [False], [["Test1"]]]

    for_lists_of_dicts_of_length_1 = [[1], [False], [["Invalid"]], ["Invalid"]]

    for_strings_with_max_100_chars = [
        "This is a really long string with more than 100 characters to test whether the validator is working well"
    ]

    for_genders = ["0", "1", "2", "9", "Male", "Female", "Unknown", "Other"]

    performer_with_two_organizations = [
        {"actor": {"reference": "#Pract1", "type": "Organization"}},
        {"actor": {"type": "Organization", "display": "Acme Healthcare"}},
    ]

    performer_with_no_organizations = [
        {"actor": {"reference": "#Pract1", "type": "NotAnOrganisation"}},
        {"actor": {"type": "NotAnOrganisation", "display": "Acme Healthcare"}},
    ]

    practitioner_resource_with_no_id = {"resourceType": "Practitioner"}

    dummy_coding_with_two_snomed_codes = [
        {"system": "http://snomed.info/sct", "code": "DUMMY SNOMED CODE 1", "display": "DUMMY SNOMED TERM 1"},
        {"system": "http://snomed.info/sct", "code": "DUMMY SNOMED CODE 2", "display": "DUMMY SNOMED TERM 2"},
    ]

    vaccination_situation_with_two_snomed_codes = {
        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
        "valueCodeableConcept": {"coding": dummy_coding_with_two_snomed_codes},
    }

    name_with_missing_values = [
        {"family": "Taylor", "period": {"start": "2024-02-07T13:28:17+00:00"}},
        {"given": ["Sarah"]},
        {"use": "official", "given": ["Sarah"]},
        {"family": "Taylor", "given": ""},
    ]

    name_with_missing_values_practitioner = [
        {"family": "Nightingale", "period": {"start": "2024-02-07T13:28:17+00:00"}},
        {"given": ["Florence"]},
        {"use": "official", "given": ["Florence"]},
        {"family": "Nightingale", "given": ""},
    ]

    invalid_dose_quantity = {"value": 2, "unit": "ml", "code": "258773002"}

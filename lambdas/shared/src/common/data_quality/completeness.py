from dataclasses import dataclass

required_fields = [
    "NHS_NUMBER",
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
]
mandatory_fields = [
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
    "RECORDED_DATE",
    "PRIMARY_SOURCE",
    "VACCINATION_PROCEDURE_CODE",
    "LOCATION_CODE",
    "LOCATION_CODE_TYPE_URI",
]
optional_fields = [
    "PERFORMING_PROFESSIONAL_FORENAME",
    "PERFORMING_PROFESSIONAL_SURNAME",
]


@dataclass
class MissingFields:
    required_fields: list[str]
    mandatory_fields: list[str]
    optional_fields: list[str]


class DataQualityCompletenessChecker:
    def run_checks(self, immunisation: dict) -> MissingFields:
        return MissingFields(
            required_fields=self._get_missing_fields(immunisation, required_fields),
            mandatory_fields=self._get_missing_fields(immunisation, mandatory_fields),
            optional_fields=self._get_missing_fields(immunisation, optional_fields),
        )

    @staticmethod
    def _get_missing_fields(immunisation: dict, list_of_fields: list[str]) -> list[str]:
        missing_fields = []
        for field in list_of_fields:
            exists = immunisation.get(field)
            if not exists:
                missing_fields.append(field)

        return missing_fields

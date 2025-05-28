import decimal
import json
import exception_messages
from datetime import datetime, timedelta, timezone
from common.mappings import Gender, ConversionFieldName

class Extractor:

    # This file holds the schema/base layout that maps FHIR fields to flat JSON fields
    # Each entry tells the converter how to extract and transform a specific value
    EXTENSION_URL_VACCINATION_PRODEDURE = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    EXTENSION_URL_SCT_DESC_DISPLAY = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay"

    CODING_SYSTEM_URL_SNOMED = "http://snomed.info/sct"
    ODS_ORG_CODE_SYSTEM_URL = "https://fhir.nhs.uk/Id/ods-organization-code"
    DEFAULT_LOCATION = "X99999"
    NHS_NUMBER_SYSTEM_URL = "https://fhir.nhs.uk/Id/nhs-number"

    DATE_CONVERT_FORMAT = "%Y%m%d"
    DEFAULT_POSTCODE = "ZZ99 3CZ"

    def __init__(self, fhir_json_data, report_unexpected_exception = True):
        self.fhir_json_data = json.loads(fhir_json_data, parse_float=decimal.Decimal) if isinstance(fhir_json_data, str) else fhir_json_data
        self.report_unexpected_exception = report_unexpected_exception
        self.error_records = []

    def _get_patient(self):
        contained = self.fhir_json_data.get("contained", [])
        return next((c for c in contained if isinstance(c, dict) and c.get("resourceType") == "Patient"), "")

    def _get_valid_names(self, names, occurrence_time, resource_type="Patient"):
        
        def has_required_fields(name):
            return "given" in name and "family" in name if resource_type == "Patient" else True
        
        official_names = [n for n in names if n.get("use") == "official" and self._is_current_period(n, occurrence_time)]
        if official_names:
            filtered_official_names = [n for n in official_names if has_required_fields(n)]
            return filtered_official_names[0]

        valid_names = [n for n in names if self._is_current_period(n, occurrence_time) and n.get("use") != "old"]
        if valid_names:
            filtered_valid_names = [n for n in valid_names if has_required_fields(n)]
            return filtered_valid_names[0]
            
        return names[0]

    def _get_person_names(self):
        occurrence_time = self._get_occurance_date_time()
        patient = self._get_patient()
        names = patient.get("name", [])

        if not isinstance(names, list) or not names:
            return "", ""

        selected_name = self._get_valid_names(names, occurrence_time, resource_type="Patient")
        person_forename = " ".join(selected_name.get("given", []))
        person_surname = selected_name.get("family", "")

        if person_forename and person_surname:
            return person_forename, person_surname
        
        return "", ""
    
    def _get_practitioner_names(self):
        contained = self.fhir_json_data.get("contained", [])
        occurrence_time = self._get_occurance_date_time()
        practitioner = next((c for c in contained if isinstance(c, dict) and c.get("resourceType") == "Practitioner"), None)
        if not practitioner or "name" not in practitioner:
            return "", ""

        practitioner_names = practitioner.get("name", [])
        valid_practitioner_names = [n for n in practitioner_names if "given" in n or "family" in n]
        if not valid_practitioner_names:
            return "", ""

        selected_practitioner_name = self._get_valid_names(valid_practitioner_names, occurrence_time, resource_type="Practitioner")
        performing_professional_forename = " ".join(selected_practitioner_name.get("given", []))
        performing_professional_surname = selected_practitioner_name.get("family", "")

        return performing_professional_forename, performing_professional_surname


    def _is_current_period(self, name, occurrence_time):
        period = name.get("period")
        if not isinstance(period, dict):
            return True  # If no period is specified, assume it's valid

        start = datetime.fromisoformat(period.get("start")) if period.get("start") else None
        end = datetime.fromisoformat(period.get("end")) if period.get("end") else None

        # Ensure all datetime objects are timezone-aware
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        return (not start or start <= occurrence_time) and (not end or occurrence_time <= end)

    def _get_occurance_date_time(self) -> str:
        try:
            occurrence_time = datetime.fromisoformat(self.fhir_json_data.get("occurrenceDateTime", ""))
            if occurrence_time and occurrence_time.tzinfo is None:
                occurrence_time = occurrence_time.replace(tzinfo=timezone.utc)
                return occurrence_time
            return occurrence_time

        except Exception as e:
            message = "DateTime conversion error [%s]: %s" % (e.__class__.__name__, e)
            error = self._log_error(ConversionFieldName.DATE_AND_TIME, message, e, code=exception_messages.UNEXPECTED_EXCEPTION)
            return error

    def _get_first_snomed_code(self, coding_container: dict) -> str:
        codings = coding_container.get("coding", [])
        for coding in codings:
            if coding.get("system") == self.CODING_SYSTEM_URL_SNOMED:
                return coding.get("code", "")
        return ""

    def _get_codeable_term(self, concept: dict) -> str:
        if concept.get("text"):
            return concept["text"]

        codings = concept.get("coding", [])
        for coding in codings:
            if coding.get("system") == self.CODING_SYSTEM_URL_SNOMED:
                return self._get_snomed_display(coding)

        return ""

    def _get_snomed_display(self, coding: dict) -> str:
        for ext in coding.get("extension", []):
            if ext.get("url") == self.EXTENSION_URL_SCT_DESC_DISPLAY:
                value_string = ext.get("valueString")
                if value_string:
                    return value_string

        return coding.get("display", "")

    def _get_site_information(self):
        performers = self.fhir_json_data.get("performer", [])
        if not isinstance(performers, list) or not performers:
            return "", ""

        valid_performers = [p for p in performers if "actor" in p and "identifier" in p["actor"]]
        if not valid_performers:
            return "", ""

        selected_performer = next(
            (
                p
                for p in valid_performers
                if p.get("actor", {}).get("type") == "Organization"
                and p.get("actor", {}).get("identifier", {}).get("system") == self.ODS_ORG_CODE_SYSTEM_URL
            ),
            next(
                (
                    p
                    for p in valid_performers
                    if p.get("actor", {}).get("identifier", {}).get("system")
                    == self.ODS_ORG_CODE_SYSTEM_URL
                ),
                next(
                    (p for p in valid_performers if p.get("actor", {}).get("type") == "Organization"),
                    valid_performers[0] if valid_performers else "",
                ),
            ),
        )
        site_code = selected_performer["actor"].get("identifier", {}).get("value")
        site_code_type_uri = selected_performer["actor"].get("identifier", {}).get("system")

        return site_code, site_code_type_uri

    def _log_error(self, field_name, field_value, e, code=exception_messages.RECORD_CHECK_FAILED):
        if self.report_unexpected_exception:
            if isinstance(e, Exception):
                message = exception_messages.MESSAGES[exception_messages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, str(e))
            else:
                message = str(e)

            self.error_records.append({
                "code": code,
                "field": field_name,
                "value": field_value,
                "message": message
            })

    def _convert_date(self, field_name, date, format) -> str:
        """
        Convert a date string according to match YYYYMMDD format.
        """
        if not date or not isinstance(date, str):
            self._log_error(field_name, date, "Invalid value. Must be non empty string")
            return ""
        try:
            dt = datetime.fromisoformat(date)
            return dt.strftime(format)
        except ValueError as e:
            self._log_error(field_name, date, e)
            return ""

    def _convert_date_to_safe_format(self, field_name, date) -> str:
        try:
            dt = datetime.fromisoformat(date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            self._log_error(field_name, date, e)
            return ""

        # Allow only +00:00 or +01:00 offsets (UTC and BST) and reject unsupported timezones
        offset = dt.utcoffset()
        allowed_offsets = [timedelta(hours=0), timedelta(hours=1)]
        if offset is not None and offset not in allowed_offsets:
            self._log_error(field_name, date, "Unsupported Format or offset")
            return ""

        # remove microseconds
        dt_format = dt.replace(microsecond=0)

        formatted = dt_format.strftime("%Y%m%dT%H%M%S%z")
        return formatted.replace("+0000", "00").replace("+0100", "01")

    def extract_nhs_number(self):
        patient = self._get_patient()
        if patient:
            identifier_list = patient.get("identifier", [])
            for identifier in identifier_list:
                if identifier.get("system", "") == self.NHS_NUMBER_SYSTEM_URL:
                    return identifier.get("value", "")
        return ""

    def extract_person_forename(self):
        return self._get_person_names()[0]

    def extract_person_surname(self):
        return self._get_person_names()[1]

    def extract_person_dob(self):
        patient = self._get_patient()

        if patient:
            dob = patient.get("birthDate", "")
            return self._convert_date(ConversionFieldName.PERSON_DOB, dob, self.DATE_CONVERT_FORMAT)
        return ""

    def extract_person_gender(self):
        patient = self._get_patient()
        if patient:
            gender = patient.get("gender", "").upper()
            try:
                return Gender[gender].value
            except KeyError:
                return ""
        return ""

    def extract_valid_address(self):
        occurrence_time = self._get_occurance_date_time()
        patient = self._get_patient()

        addresses = patient.get("address", [])
        if not isinstance(addresses, list) or not addresses:
            return self.DEFAULT_POSTCODE

        valid_addresses = [a for a in addresses if "postalCode" in a and self._is_current_period(a, occurrence_time)]
        
        if len(valid_addresses) > 0:
            selected_address = next(
                (a for a in valid_addresses if a.get("use") == "home" and a.get("type") != "postal"),
                next(
                    (a for a in valid_addresses if a.get("use") != "old" and a.get("type") != "postal"),
                    next((a for a in valid_addresses if a.get("use") != "old"), valid_addresses[0]),
                ),
            )
            post_code = selected_address.get("postalCode", self.DEFAULT_POSTCODE)
            if post_code: 
                return post_code
            
        return addresses[0].get("postalCode", self.DEFAULT_POSTCODE) if addresses else self.DEFAULT_POSTCODE
    
    def extract_date_time(self) -> str: 
        date = self.fhir_json_data.get("occurrenceDateTime","")
        if date:
            return self._convert_date_to_safe_format(ConversionFieldName.DATE_AND_TIME, date)
        return ""

    def extract_site_code(self):
        return self._get_site_information()[0]

    def extract_site_code_type_uri(self):
        return self._get_site_information()[1]

    def extract_unique_id(self):
        identifier = self.fhir_json_data.get("identifier", [])
        if identifier:
            return identifier[0].get("value", "")
        return ""

    def extract_unique_id_uri(self):
        identifier = self.fhir_json_data.get("identifier", [])
        if identifier and len(identifier) == 1:
            return identifier[0].get("system", "")
        return ""

    def extract_practitioner_forename(self):
        return self._get_practitioner_names()[0]

    def extract_practitioner_surname(self):
        return self._get_practitioner_names()[1]

    def extract_recorded_date(self) -> str:
        date = self.fhir_json_data.get("recorded", "")
        return self._convert_date(ConversionFieldName.RECORDED_DATE, date, self.DATE_CONVERT_FORMAT)

    def extract_primary_source(self) -> bool | str:
        primary_source = self.fhir_json_data.get("primarySource")

        if isinstance(primary_source, bool):
            return primary_source
        return ""

    def extract_vaccination_procedure_code(self) -> str:
        extensions = self.fhir_json_data.get("extension", [])
        for ext in extensions:
            if ext.get("url") == self.EXTENSION_URL_VACCINATION_PRODEDURE:
                value_cc = ext.get("valueCodeableConcept", {})
                return self._get_first_snomed_code(value_cc)
        return ""

    def extract_vaccination_procedure_term(self) -> str:
        extensions = self.fhir_json_data.get("extension", [])
        for ext in extensions:
            if ext.get("url") == self.EXTENSION_URL_VACCINATION_PRODEDURE:
                return self._get_codeable_term(ext.get("valueCodeableConcept", {}))
        return ""

    def extract_dose_sequence(self) -> str:
        protocol_applied = self.fhir_json_data.get("protocolApplied", [])

        if protocol_applied:
            dose = protocol_applied[0].get("doseNumberPositiveInt", None)
            return str(dose) if dose else ""
        return ""

    def extract_vaccine_product_code(self) -> str:
        vaccine_code = self.fhir_json_data.get("vaccineCode", {})
        return self._get_first_snomed_code(vaccine_code)

    def extract_vaccine_product_term(self) -> str:
        return self._get_codeable_term(self.fhir_json_data.get("vaccineCode", {}))

    def extract_vaccine_manufacturer(self) -> str:
        manufacturer = self.fhir_json_data.get("manufacturer", {})
        if manufacturer:
            return manufacturer.get("display", "")
        return ""

    def extract_batch_number(self) -> str:
        return self.fhir_json_data.get("lotNumber", "")

    def extract_expiry_date(self) -> str:
        date = self.fhir_json_data.get("expirationDate","")
        return self._convert_date(ConversionFieldName.EXPIRY_DATE, date, self.DATE_CONVERT_FORMAT)

    def extract_site_of_vaccination_code(self) -> str:
        site = self.fhir_json_data.get("site", {})
        return self._get_first_snomed_code(site)

    def extract_site_of_vaccination_term(self) -> str:
        return self._get_codeable_term(self.fhir_json_data.get("site", {}))

    def extract_route_of_vaccination_code(self) -> str:
        route = self.fhir_json_data.get("route", {})
        return self._get_first_snomed_code(route)

    def extract_route_of_vaccination_term(self) -> str:
        return self._get_codeable_term(self.fhir_json_data.get("route", {}))

    def extract_dose_amount(self) -> str:
        dose_quantity = self.fhir_json_data.get("doseQuantity", {})
        return dose_quantity.get("value", "")

    def extract_dose_unit_code(self) -> str:
        dose_quantity = self.fhir_json_data.get("doseQuantity", {})
        if dose_quantity.get("system") == self.CODING_SYSTEM_URL_SNOMED and dose_quantity.get("code"):
            return dose_quantity.get("code")
        return ""

    def extract_dose_unit_term(self) -> str:
        dose_quantity = self.fhir_json_data.get("doseQuantity", {})
        return dose_quantity.get("unit", "")

    def extract_indication_code(self) -> str:
        for reason in self.fhir_json_data.get("reasonCode", []):
            codings = reason.get("coding", [])
            for coding in codings:
                if coding.get("system") == self.CODING_SYSTEM_URL_SNOMED:
                    return coding.get("code", "")
        return ""

    def extract_location_code(self) -> str:
        location = self.fhir_json_data.get("location", {})

        if location:
            identifier = location.get("identifier", {})
            return identifier.get("value", self.DEFAULT_LOCATION)

        return self.DEFAULT_LOCATION

    def extract_location_code_type_uri(self) -> str:
        location = self.fhir_json_data.get("location", {})

        if location:
            identifier = location.get("identifier", {})
            return identifier.get("system", self.ODS_ORG_CODE_SYSTEM_URL)

        return self.ODS_ORG_CODE_SYSTEM_URL

    def get_error_records(self):
        return self.error_records

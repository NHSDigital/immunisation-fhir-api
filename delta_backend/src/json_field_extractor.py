import json
import exception_messages
from datetime import datetime, timezone

class Extractor: 

    # This file holds the schema/base layout that maps FHIR fields to flat JSON fields
    # Each entry tells the converter how to extract and transform a specific value
    EXTENSION_URL_VACCINATION_PRODEDURE = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    EXTENSION_URL_SCT_DESC_DISPLAY = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay"

    CODING_SYSTEM_URL_SNOMED = "http://snomed.info/sct"
    ODS_ORG_CODE_SYSTEM_URL = "https://fhir.nhs.uk/Id/ods-organization-code"

    def __init__(self, fhir_json_data):
        self.fhir_json_data = json.loads(fhir_json_data) if isinstance(fhir_json_data, str) else fhir_json_data
        
    def _get_patient(self):
        contained = self.fhir_json_data.get("contained", [])
        return next((c for c in contained if isinstance(c, dict) and c.get("resourceType") == "Patient"), None)

    def _get_valid_names(self, names, occurrence_time):
        
        official_names = [n for n in names if n.get("use") == "official" and self._is_current_period(n, occurrence_time)]
        if official_names:
            return official_names[0]

        valid_names = [n for n in names if self._is_current_period(n, occurrence_time) and n.get("use") != "old"]
        return valid_names[0] if valid_names else names[0]

    def extract_person_forename(self):
        return self.extract_person_names()[0]
    
    def extract_person_surname(self):
        return self.extract_person_names()[1]
    
    def extract_person_names(self):
        occurrence_time = self._get_occurance_date_time()
        patient = self._get_patient()
        names = patient.get("name", [])
        
        if not isinstance(names, list) or not names:
            return "", ""

        selected_name = self._get_valid_names(names, occurrence_time)
        person_forename = " ".join(selected_name.get("given", []))
        person_surname = selected_name.get("family", "")

        return person_forename, person_surname

    def extract_valid_address(self):
        occurrence_time = self._get_occurance_date_time()
        patient = self._get_patient()
        
        addresses = patient.get("address", [])
        if not isinstance(addresses, list) or not addresses:
            return "ZZ99 3CZ"

        valid_addresses = [a for a in addresses if "postalCode" in a and self._is_current_period(a, occurrence_time)]
        if not valid_addresses:
            return "ZZ99 3CZ"

        selected_address = next(
            (a for a in valid_addresses if a.get("use") == "home" and a.get("type") != "postal"),
            next(
                (a for a in valid_addresses if a.get("use") != "old" and a.get("type") != "postal"),
                next((a for a in valid_addresses if a.get("use") != "old"), valid_addresses[0]),
            ),
        )
        return selected_address.get("postalCode", "ZZ99 3CZ")

    def extract_site_code(self):
        return self.extract_site_information()[0]
    
    def extract_site_code_type_uri(self):
        return self.extract_site_information()[1]
        
    def extract_site_information(self):
        performers = self.fhir_json_data.get("performer", [])
        if not isinstance(performers, list) or not performers:
            return None, None

        valid_performers = [p for p in performers if "actor" in p and "identifier" in p["actor"]]
        if not valid_performers:
            return None, None

        selected_performer = next(
            (
                p
                for p in valid_performers
                if p.get("actor", {}).get("type") == "Organization"
                and p.get("actor", {}).get("identifier", {}).get("system") == "https://fhir.nhs.uk/Id/ods-organization-code"
            ),
            next(
                (
                    p
                    for p in valid_performers
                    if p.get("actor", {}).get("identifier", {}).get("system")
                    == "https://fhir.nhs.uk/Id/ods-organization-code"
                ),
                next(
                    (p for p in valid_performers if p.get("actor", {}).get("type") == "Organization"),
                    valid_performers[0] if valid_performers else None,
                ),
            ),
        )
        site_code = selected_performer["actor"].get("identifier", {}).get("value")
        site_code_type_uri = selected_performer["actor"].get("identifier", {}).get("system")

        return site_code, site_code_type_uri

    def extract_practitioner_forename(self):
        return self.extract_practitioner_names()[0]
    
    def extract_practitioner_surname(self):
        return self.extract_practitioner_names()[1]
    
    def extract_practitioner_names(self):
        contained = self.fhir_json_data.get("contained", [])
        occurrence_time = self._get_occurance_date_time()
        practitioner = next((c for c in contained if isinstance(c, dict) and c.get("resourceType") == "Practitioner"), None)
        if not practitioner or "name" not in practitioner:
            return "", ""

        practitioner_names = practitioner.get("name", [])
        valid_practitioner_names = [n for n in practitioner_names if "given" in n or "family" in n]
        if not valid_practitioner_names:
            return "", ""

        selected_practitioner_name = self._get_valid_names(valid_practitioner_names, occurrence_time)
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
        
    def extract_vaccination_procedure_code(self) -> str:
        extensions = self.fhir_json_data.get("extension", [])
        for ext in extensions:
            if ext.get("url") == self.EXTENSION_URL_VACCINATION_PRODEDURE:
                value_cc = ext.get("valueCodeableConcept", {})
                return self._get_first_snomed_code(value_cc)
        return ""
    
    def extract_vaccine_product_code(self) -> str:
        vaccine_code = self.fhir_json_data.get("vaccineCode", {})
        return self._get_first_snomed_code(vaccine_code)

    def extract_site_of_vaccination_code(self) -> str:
        site = self.fhir_json_data.get("site", {})
        return self._get_first_snomed_code(site)

    def extract_route_of_vaccination_code(self) -> str:
        route = self.fhir_json_data.get("route", {})
        return self._get_first_snomed_code(route)

    def extract_indication_code(self) -> str:
        for reason in self.fhir_json_data.get("reasonCode", []):
            codings = reason.get("coding", [])
            for coding in codings:
                if coding.get("system") == self.CODING_SYSTEM_URL_SNOMED:
                    return coding.get("code", "")
        return ""

    def extract_dose_unit_code(self) -> str:
        dose_quantity = self.fhir_json_data.get("doseQuantity", {})
        if dose_quantity.get("system") == self.CODING_SYSTEM_URL_SNOMED and dose_quantity.get("code"):
            return dose_quantity.get("code")
        return ""

    def extract_dose_unit_term(self) -> str:
        dose_quantity = self.fhir_json_data.get("doseQuantity", {})
        return dose_quantity.get("unit", "")

    def _get_first_snomed_code(self, coding_container: dict) -> str:
        codings = coding_container.get("coding", [])
        for coding in codings:
            if coding.get("system") == self.CODING_SYSTEM_URL_SNOMED:
                return coding.get("code", "")
        return ""

    def _get_term_from_codeable_concept(self, concept: dict) -> str:
        if concept.get("text"):
            return concept["text"]

        codings = concept.get("coding", [])
        for coding in codings:
            if coding.get("system") == self.CODING_SYSTEM_URL_SNOMED:
                # Try SCTDescDisplay extension first
                for ext in coding.get("extension", []):
                    if ext.get("url") == self.EXTENSION_URL_SCT_DESC_DISPLAY:
                        value_string = ext.get("valueString")
                        if value_string:
                            return value_string

                # Fallback to display
                return coding.get("display", "")

        return ""

    def extract_vaccination_procedure_term(self) -> str:
        extensions = self.fhir_json_data.get("extension", [])
        for ext in extensions:
            if ext.get("url") == self.EXTENSION_URL_VACCINATION_PRODEDURE:
                return self._get_term_from_codeable_concept(ext.get("valueCodeableConcept", {}))
        return ""

    def extract_vaccine_product_term(self) -> str:
        return self._get_term_from_codeable_concept(self.fhir_json_data.get("vaccineCode", {}))

    def extract_site_of_vaccination_term(self) -> str:
        return self._get_term_from_codeable_concept(self.fhir_json_data.get("site", {}))

    def extract_route_of_vaccination_term(self) -> str:
        return self._get_term_from_codeable_concept(self.fhir_json_data.get("route", {}))

    def extract_dose_sequence(self) -> str: 
        protocol_applied = self.fhir_json_data.get("protocolApplied", [])
        
        if protocol_applied:   
            dose = protocol_applied[0].get("doseNumberPositiveInt", None)
            return str(dose) if dose else ""
        return ""
    
    def _get_occurance_date_time(self) -> str:
        try:
            #TODO: Double check if this logic is correct
            occurrence_time = datetime.fromisoformat(self.fhir_json_data.get("occurrenceDateTime", ""))
            if occurrence_time and occurrence_time.tzinfo is None:
                occurrence_time = occurrence_time.replace(tzinfo=timezone.utc)
                return occurrence_time
            return occurrence_time
        
        except Exception as e:
            message = "DateTime conversion error [%s]: %s" % (e.__class__.__name__, e)
            error = self._log_error(message, code=exception_messages.UNEXPECTED_EXCEPTION)
            return error

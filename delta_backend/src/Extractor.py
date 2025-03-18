from datetime import datetime, timezone


@staticmethod
def get_patient(json_data):
    contained = json_data.get("contained", [])
    return next((c for c in contained if isinstance(c, dict) and c.get("resourceType") == "Patient"), None)


@staticmethod
def get_valid_names(names, occurrence_time):
    official_names = [n for n in names if n.get("use") == "official" and is_current_period(n, occurrence_time)]
    if official_names:
        return official_names[0]

    valid_names = [n for n in names if is_current_period(n, occurrence_time) and n.get("use") != "old"]
    return valid_names[0] if valid_names else names[0]


@staticmethod
def extract_person_names(patient, occurrence_time):
    names = patient.get("name", [])
    if not isinstance(names, list) or not names:
        return "", ""

    selected_name = get_valid_names(names, occurrence_time)
    person_forename = " ".join(selected_name.get("given", []))
    person_surname = selected_name.get("family", "")

    return person_forename, person_surname


@staticmethod
def get_valid_address(patient, occurrence_time):
    addresses = patient.get("address", [])
    if not isinstance(addresses, list) or not addresses:
        return "ZZ99 3CZ"

    valid_addresses = [a for a in addresses if "postalCode" in a and is_current_period(a, occurrence_time)]
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


@staticmethod
def extract_site_code(json_data):
    performers = json_data.get("performer", [])
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


@staticmethod
def extract_practitioner_names(json_data, occurrence_time):
    contained = json_data.get("contained", [])
    practitioner = next((c for c in contained if isinstance(c, dict) and c.get("resourceType") == "Practitioner"), None)
    if not practitioner or "name" not in practitioner:
        return "", ""

    practitioner_names = practitioner.get("name", [])
    valid_practitioner_names = [n for n in practitioner_names if "given" in n or "family" in n]
    if not valid_practitioner_names:
        return "", ""

    selected_practitioner_name = get_valid_names(valid_practitioner_names, occurrence_time)
    performing_professional_forename = " ".join(selected_practitioner_name.get("given", []))
    performing_professional_surname = selected_practitioner_name.get("family", "")

    return performing_professional_forename, performing_professional_surname


def is_current_period(name, occurrence_time):
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
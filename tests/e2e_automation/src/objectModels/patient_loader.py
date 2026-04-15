import math

import pandas as pd

from src.objectModels.api_data_objects import Address, HumanName, Identifier, Patient

csv_path = "input/testData.csv"


def load_patient_by_id(id: str) -> Patient:
    row = read_patient_from_csv(id)  # FIXED: Correct function call

    if row is None:
        raise ValueError(f"NHS number {id} not found in {csv_path}")

    nhs_number = row.get("nhs_number", "").strip()
    nhs_number = None if not nhs_number or nhs_number.lower() in ["null", "none"] else nhs_number

    identifier = Identifier(system="https://fhir.nhs.uk/Id/nhs-number", value=nhs_number)

    name = HumanName(family=row["family_name"], given=[row["given_name"]])

    address = Address(
        use="Home",
        type="Postal",
        text="Validate Obf",
        line=[row["address_line"]],
        city=row["city"],
        district=row["district"],
        state=row["state"],
        postalCode=row["postal_code"],
        country=row["country"],
        period={"start": row["start_date"], "end": row["end_date"]},
    )

    return Patient(
        id="Pat1",
        resourceType="Patient",
        identifier=[identifier],
        name=[name],
        gender=row["gender"],
        birthDate=row["birth_date"],
        address=[address],
    )


def get_gp_code_by_nhs_number(nhs_number: str) -> str | None:
    df = pd.read_csv(csv_path, dtype=str)

    match = df[df["nhs_number"] == nhs_number.strip()]
    if match.empty:
        raise ValueError(f"NHS number {nhs_number} not found in {csv_path}")

    row = match.iloc[0]

    gp_code = safe_str(row.get("gp_code"))
    dss_end = safe_str(row.get("dss_record_end_date"))

    if gp_code == "" or gp_code.lower() in ["null", "none"]:
        return None

    if dss_end != "":
        return None

    return gp_code


def read_patient_from_csv(id: str):
    df = pd.read_csv(csv_path, dtype=str)

    valid_patients = df[df["id"] == id] if id != "Random" else df[df["id"] == "Valid_NHS"]

    if not valid_patients.empty:
        return valid_patients.sample(1).to_dict(orient="records")[0]

    return None


def safe_str(value):
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()

import os

valid_nhs_number1 = "9693632109"
valid_nhs_number2 = "9693633687"

cis2_user = "656005750104"

patient_identifier_system = "https://fhir.nhs.uk/Id/nhs-number"
valid_patient_identifier1 = f"{patient_identifier_system}|{valid_nhs_number1}"
valid_patient_identifier2 = f"{patient_identifier_system}|{valid_nhs_number2}"

env_internal_dev = os.environ.get("ENVIRONMENT", "") == "internal-dev"

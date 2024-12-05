from typing import Union

"""Constants for recordforwarder"""


class Constants:
    """Constants for recordforwarder"""

    ack_headers = [
        "MESSAGE_HEADER_ID",
        "HEADER_RESPONSE_CODE",
        "ISSUE_SEVERITY",
        "ISSUE_CODE",
        "ISSUE_DETAILS_CODE",
        "RESPONSE_TYPE",
        "RESPONSE_CODE",
        "RESPONSE_DISPLAY",
        "RECEIVED_TIME",
        "MAILBOX_FROM",
        "LOCAL_ID",
        "IMMS_ID",
        "OPERATION_OUTCOME",
        "MESSAGE_DELIVERY",
    ]

    ODS_TO_SUPPLIER_MAPPINGS = {
        "YGM41": "EMIS",
        "8J1100001": "PINNACLE",
        "8HK48": "SONAR",
        "YGA": "TPP",
        "0DE": "AGEM-NIVS",
        "0DF": "NIMS",
        "8HA94": "EVA",
        "X26": "RAVS",
        "YGMYH": "MEDICAL_DIRECTOR",
        "W00": "WELSH_DA_1",
        "W000": "WELSH_DA_2",
        "ZT001": "NORTHERN_IRELAND_DA",
        "YA7": "SCOTLAND_DA",
        "N2N9I": "COVID19_VACCINE_RESOLUTION_SERVICEDESK",
        "YGJ": "EMIS",
        "DPSREDUCED": "DPSREDUCED",
        "DPSFULL": "DPSFULL",
    }

    error_code_mapping = {
        500: [
            "application includes invalid authorization values",
            "unhandled",
            "server error",
            "rate limited",
            "Downstream service failed",
        ],
        422: ["duplicate", "duplicated"],
        403: ["unauthorized"],
        404: ["not found", "does not exist"],
        204: ["deleted", "No content"],
    }


def identify_supplier(ods_code: str) -> Union[str, None]:
    """
    Identifies the supplier from the ods code using the mapping.
    Defaults to empty string if ODS code isn't found in the mappings
    """
    return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code, "")


def extract_file_key_elements(file_key: str) -> dict:
    """
    Returns a dictionary containing each of the elements which can be extracted from the file key.
    All elements are converted to upper case.\n
    Supplier is identified using the ods_to_supplier mapping and defaulted to empty string if ODS code is not found.\n
    NOTE: This function works on the assumption that the file_key has already
    been validated as having four underscores and a single '.' which occurs after the four of the underscores.
    """
    if file_key is None or file_key == "":
        return ""

    file_key = file_key.upper()
    file_key_parts_without_extension = file_key.split(".")[0].split("_")
    file_key_elements = {
        "vaccine_type": file_key_parts_without_extension[0],
        "ods_code": file_key_parts_without_extension[3],
    }

    # Identify the supplier using the ODS code (defaults to empty string if ODS code not found)
    file_key_elements["supplier"] = identify_supplier(file_key_elements["ods_code"])

    return file_key_elements


def get_status_code_for_diagnostics(diagnostics_message: str) -> int:
    """Returns the status_code for diagnostics"""
    diagnostics_message = diagnostics_message.lower()

    default_error_code = 400

    for error_code, keywords in Constants.error_code_mapping.items():
        for keyword in keywords:
            if keyword in diagnostics_message:
                return error_code
    return default_error_code

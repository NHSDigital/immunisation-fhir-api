"""Helper module for batch End of File utilities. For more context on how we use this in the batch process refer to
https://nhsd-confluence.digital.nhs.uk/spaces/Vacc/pages/1187373499/Immunisation+FHIR+API+-+ACK+File+Management"""

EOF_TEXT = "EOF"


def make_batch_eof_message(
    file_key: str, supplier: str, vaccine_type: str, created_at: str, audit_record_id: str, total_records: int
) -> dict:
    """Creates the standard EOF message passed through the batch system to flag the end of a file processing."""
    return {
        "message": EOF_TEXT,
        "file_key": file_key,
        "row_id": f"{audit_record_id}^{total_records}",
        "supplier": supplier,
        "vax_type": vaccine_type,
        "created_at_formatted_string": created_at,
    }


def is_eof_message(message_body: dict) -> bool:
    return message_body.get("message", "") == EOF_TEXT

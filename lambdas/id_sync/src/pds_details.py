"""
Operations related to PDS (Patient Demographic Service)
"""


def get_nhs_number_from_pds_resource(pds_resource: dict) -> str:
    """Simple helper to get the NHS Number from a PDS Resource. No handling as this is a mandatory field in the PDS
    response. Must only use where we have ensured an object has been returned."""
    return pds_resource["identifier"][0]["value"]

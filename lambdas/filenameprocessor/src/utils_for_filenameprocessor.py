"""Utils for filenameprocessor lambda"""

from datetime import timedelta

from constants import AUDIT_TABLE_TTL_DAYS


def get_creation_and_expiry_times(s3_response: dict) -> (str, int):
    """Get 'created_at_formatted_string' and 'expires_at' from the response"""
    creation_datetime = s3_response["LastModified"]
    expiry_datetime = creation_datetime + timedelta(days=int(AUDIT_TABLE_TTL_DAYS))
    expiry_timestamp = int(expiry_datetime.timestamp())
    return creation_datetime.strftime("%Y%m%dT%H%M%S00"), expiry_timestamp

from typing import TypedDict


class BatchFileCreatedEvent(TypedDict):
    message_id: str
    vaccine_type: str
    supplier: str
    filename: str
    permission: list[str]
    created_at_formatted_string: str

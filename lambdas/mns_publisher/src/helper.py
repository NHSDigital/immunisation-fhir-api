def find_imms_value_in_stream(sqs_event_data: dict, target_key: str):
    if isinstance(sqs_event_data, dict):
        for key, value in sqs_event_data.items():
            if key == target_key:
                return value
            result = find_imms_value_in_stream(value, target_key)
            if result is not None:
                return result
    return None

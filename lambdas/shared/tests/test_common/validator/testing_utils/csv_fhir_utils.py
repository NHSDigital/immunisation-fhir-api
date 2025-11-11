import json


# Utility function to build CSV row strings
def build_row(header: str, csv_file: dict) -> str:
    """
    Construct a CSV row string from the provided csv_file.
    Any missing header columns get empty string values.
    """
    cols = header.split(",")
    return ",".join(str(csv_file.get(col, "")) for col in cols)


# Utility function to parse test (FHIR or schema) files
def parse_test_file(test_file_name: str) -> dict:
    with open(test_file_name) as json_file:
        return json.load(json_file)

# Utility function to build CSV row strings


def build_row(header: str, csv_file: dict) -> str:
    """
    Construct a CSV row string from the provided csv_file.
    Any missing header columns get empty string values.
    """
    cols = header.split(",")
    return ",".join(str(csv_file.get(col, "")) for col in cols)

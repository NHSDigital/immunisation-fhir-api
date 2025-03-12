import pandas as pd
from io import StringIO


def get_unique_action_flags_from_s3(csv_data):
    """
    Reads the CSV file from an S3 bucket and returns a set of unique ACTION_FLAG values.
    """
    # Load content into a pandas DataFrame
    df = pd.read_csv(StringIO(csv_data), delimiter="|", usecols=["ACTION_FLAG"])
    # Get unique ACTION_FLAG values in one step
    unique_action_flags = set(df["ACTION_FLAG"].str.upper().unique())
    return unique_action_flags

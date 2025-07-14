import pandas as pd
from io import StringIO
import logging


logger = logging.getLogger(__name__)


def get_unique_action_flags_from_s3(csv_data):
    """
    Reads the CSV file from an S3 bucket and returns a set of unique ACTION_FLAG values.
    """
    # Load content into a pandas DataFrame
    try:
        df = pd.read_csv(StringIO(csv_data), delimiter="|", usecols=["ACTION_FLAG"])
    except ValueError:
        logger.warning("ACTION_FLAG column missing or malformed in file.")
        return set()

    if "ACTION_FLAG" not in df.columns:
        logger.warning("ACTION_FLAG column is missing in file.")
        return set()
    # Get unique ACTION_FLAG values in one step
    unique_action_flags = set(
        df["ACTION_FLAG"]
        .dropna()
        .astype(str)
        .str.upper()
        .unique()
    )
    return unique_action_flags

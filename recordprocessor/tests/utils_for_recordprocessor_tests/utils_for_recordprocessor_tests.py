"""Utils for the recordprocessor tests"""

from csv import DictReader
from io import StringIO


def convert_string_to_dict_reader(data_string: str):
    """Take a data string and convert it to a csv DictReader"""
    return DictReader(StringIO(data_string), delimiter="|")

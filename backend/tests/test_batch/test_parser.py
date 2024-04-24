import io
import unittest
from botocore.response import StreamingBody

from batch.parser import DataParser


def make_a_stream() -> StreamingBody:
    # this covers all the edge cases, including:
    #  empty lines, empty values and mismatched quotes
    content = b"""
    FOO"|BAR
    "val1"|val2"
    val3 | val4
    |

    """
    return StreamingBody(io.BytesIO(content), len(content))


class TestDatParser(unittest.TestCase):
    def setUp(self):
        self.parser = DataParser(make_a_stream())

    def test_parse_headers(self):
        """it should parse the header of the dat file"""

        headers = next(self.parser.parse_rows())

        self.assertListEqual(["FOO", "BAR"], headers)

    def test_parse_rows(self):
        """it should parse the rows of the dat file"""
        parser = DataParser(make_a_stream())
        rows = parser.parse_rows()
        _ = next(rows)  # skip the header

        row1 = next(rows)
        row2 = next(rows)
        row3 = next(rows)

        self.assertListEqual(["val1", "val2"], row1)
        self.assertListEqual(["val3", "val4"], row2)
        self.assertListEqual(["", ""], row3)

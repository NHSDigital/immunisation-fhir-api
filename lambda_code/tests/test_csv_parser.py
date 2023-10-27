import unittest
import os
import sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../src")

from mesh import MeshCsvParser

csv_file_name = "data.csv"
csv_file_path = (
    f"{os.path.dirname(os.path.abspath(__file__))}/sample_data/{csv_file_name}"
)


class TestCsvParser(unittest.TestCase):
    def setUp(self):
        with open(csv_file_path, "r") as f:
            self.csv_content = f.read()

    def test_parse(self):
        parser = MeshCsvParser(self.csv_content)
        parser.parse()

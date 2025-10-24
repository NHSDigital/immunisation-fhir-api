import unittest

from common.validator.parsers.csv_line_parser import CSVLineParser


class TestCSVLineParser(unittest.TestCase):
    def test_parse_normal(self):
        p = CSVLineParser()
        p.parse_csv_line("9011011,Tom,32", "nhs_number,name,age")
        self.assertEqual(p.csv_file_data, {"nhs_number": "9011011", "name": "Tom", "age": "32"})
        self.assertEqual(p.get_key_value("name"), ["Tom"])

    def test_extra_values_ignored(self):
        p = CSVLineParser()
        p.parse_csv_line("1,2,3", "a,b")
        self.assertEqual(p.csv_file_data, {"a": "1", "b": "2"})
        self.assertEqual(p.get_key_value("b"), ["2"])

    def test_fewer_values_missing_key_raises(self):
        p = CSVLineParser()
        p.parse_csv_line("alpha,beta", "a,b,c")
        self.assertIn("a", p.csv_file_data)
        self.assertIn("b", p.csv_file_data)
        self.assertNotIn("c", p.csv_file_data)
        with self.assertRaises(KeyError):
            _ = p.get_key_value("c")

    def test_get_missing_key_raises(self):
        p = CSVLineParser()
        p.parse_csv_line("1,2", "a,b")
        with self.assertRaises(KeyError):
            _ = p.get_key_value("z")


if __name__ == "__main__":
    unittest.main()

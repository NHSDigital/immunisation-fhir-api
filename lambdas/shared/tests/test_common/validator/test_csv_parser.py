import tempfile
import unittest
from pathlib import Path

from common.validator.parsers.csv_parser import CSVParser


class TestCSVParser(unittest.TestCase):
    def _write_temp_csv(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        Path(path).write_text(content, encoding="utf-8")
        return path

    def test_parse_file_with_pipe_delimiter(self):
        csv_content = "nhs|name|age\n9011011|Tom|32\n9011012|Ana|27\n"
        path = self._write_temp_csv(csv_content)
        try:
            p = CSVParser()
            p.parse_csv_file(path, delimiter="|")
            self.assertEqual(p.get_key_value("name"), ["Tom", "Ana"])
            self.assertEqual(p.get_key_value("nhs"), ["9011011", "9011012"])
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_column_raises_keyerror(self):
        csv_content = "a|b\n1|2\n"
        path = self._write_temp_csv(csv_content)
        try:
            p = CSVParser()
            p.parse_csv_file(path, delimiter="|")
            with self.assertRaises(KeyError):
                _ = p.get_key_value("c")
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

from botocore.response import StreamingBody
from dataclasses import dataclass
from typing import List, Generator

RawRecord = List[str]


@dataclass
class DataField:
    name: str
    value: str


class DataParser:
    delimiter: str = "|"

    def __init__(self, stream: StreamingBody):
        self.stream = stream

    def parse_rows(self) -> Generator[RawRecord, None, None]:
        """Parse the rows of the dat file. It's up to the caller to skip the header
        This parser ignores whitespace and quotes. It's resilient to empty values and mismatched quotes
        The header can either be quoted or not. They are treated the same as each row"""
        for row in self.stream.iter_lines():
            row_str = row.decode("utf-8")
            if not row_str:
                continue
            raw_values = row_str.strip().split(self.delimiter)
            yield [value.strip('"').strip() for value in raw_values]


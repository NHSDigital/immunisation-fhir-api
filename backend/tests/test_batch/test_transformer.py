from collections import OrderedDict

import unittest
from unittest.mock import MagicMock, patch

from batch.transformer import DataRecordTransformer


class TestDatRecordTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = DataRecordTransformer()

    def test_transform(self):
        """it should call the decorators to transform the record"""
        record = OrderedDict({"key": "value"})

        with patch("batch.transformer.decorate") as mock_decorate:
            # by passing `decorate` by returning the raw_imms intact
            mock_decorate.return_value = self.transformer.raw_imms
            self.transformer.transform(record)

        mock_decorate.assert_called_once_with(self.transformer.raw_imms, record)


class TestTransformerImmsStatus(unittest.TestCase):
    def setUp(self):
        self.transformer = DataRecordTransformer()

        self.mock_decorate = MagicMock()
        # the default behavior is to return the raw_imms
        self.mock_decorate.return_value = self.transformer.raw_imms
        self.patcher = patch("batch.transformer.decorate", self.mock_decorate)

        self.patcher.start()

    def test_not_given(self):
        pass

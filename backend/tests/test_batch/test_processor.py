import unittest
from unittest.mock import create_autospec

from batch.errors import TransformerRowError, TransformerUnhandledError, ImmunizationApiError, \
    ImmunizationApiUnhandledError
from batch.immunization_api import ImmunizationApi
from batch.parser import DataParser
from batch.processor import BatchProcessor, BatchData, Action
from batch.report import ReportGenerator
from batch.transformer import DataRecordTransformer


class TestBatchProcessor(unittest.TestCase):
    def setUp(self):
        self.batch_data = BatchData(
            object_key="an_object_key",
            event_timestamp=1,
            process_timestamp=2,
            environment="a_env",
            source_bucket="a_source_bucket",
            destination_bucket="a_destination_bucket",
            event_id="an_event_id",
            batch_id="a_batch_id",
        )
        self.transformer = create_autospec(DataRecordTransformer)
        self.parser = create_autospec(DataParser)
        self.api = create_autospec(ImmunizationApi)
        self.report_gen = create_autospec(ReportGenerator)
        self.processor = BatchProcessor(
            batch_data=self.batch_data,
            row_transformer=self.transformer,
            parser=self.parser,
            api=self.api,
            report_generator=self.report_gen,
        )
        # default behaviour of the parser
        self.parser.parse_rows.return_value = iter([["H0", "H1", "ACTION_FLAG"], ["v0", "v1", Action.CREATE.value]])

    # def test_create_dict_record(self):
    #     """it should create a dictionary record from the headers and row"""
    #     self.parser.parse_rows.return_value = iter([["H0", "H1", "ACTION_FLAG"], ["v0", "v1", Action.CREATE.value]])

    #     self.processor.process() # circular issue

    #     # The headers should be converted to the lower case value
    #     self.transformer.transform.assert_called_once_with({"h0": "v0", "h1": "v1", "action_flag": Action.CREATE.value})

    # def test_create_transformed_record(self):
    #     """it should create a transformed record by calling the immunization api"""
    #     self.parser.parse_rows.return_value = iter([["H0", "H1", "ACTION_FLAG"], ["v0", "v1", Action.CREATE.value]])
    #     imms = {"key": "value"}
    #     self.transformer.transform.return_value = imms

    #     self.processor.process()  # circular issue

    #     self.api.create_immunization.assert_called_once_with(imms, self.processor.trace_data["correlation_id"])

    # def test_update_transformed_record(self):
    #     """it should update a transformed record by calling the immunization api"""
    #     self.parser.parse_rows.return_value = iter([["H0", "H1", "ACTION_FLAG"], ["v0", "v1", Action.UPDATE.value]])
    #     imms = {"key": "value"}
    #     self.transformer.transform.return_value = imms

    #     self.processor.process()  # circular issue

    #     self.api.update_immunization.assert_called_once_with(imms, self.processor.trace_data["correlation_id"])

    # def test_delete_transformed_record(self):
    #     """it should delete a transformed record by calling the immunization api"""
    #     self.parser.parse_rows.return_value = iter([["H0", "H1", "ACTION_FLAG"], ["v0", "v1", Action.DELETE.value]])
    #     imms = {"key": "value"}
    #     self.transformer.transform.return_value = imms

    #     self.processor.process() # circular issue

    #     self.api.delete_immunization.assert_called_once_with(imms, self.processor.trace_data["correlation_id"])

    # def test_close_report(self):
    #     """it should close the report generator, so we can upload the report"""

    #     self.processor.process()  # circular issue

    #     self.report_gen.close.assert_called_once()

    def test_continue_on_transform_handled_error(self):
        """it should continue processing if a transform error is raised"""
        self.transformer.transform.side_effect = TransformerRowError([])

        self.processor.process()

        self.api.create_immunization.assert_not_called()

    def test_continue_on_transform_unhandled_error(self):
        """it should continue processing if a transform error is raised"""
        self.transformer.transform.side_effect = TransformerUnhandledError("a_decorator")

        self.processor.process()

        self.api.create_immunization.assert_not_called()

    def test_continue_on_api_handled_error(self):
        """it should continue processing if an api error is raised"""
        self.transformer.transform.return_value = {"key": "value"}
        self.api.create_immunization.side_effect = ImmunizationApiError(0, {}, {})

        self.processor.process()

        self.api.create_immunization.assert_called_once()

    def test_continue_on_api_unhandled_error(self):
        """it should continue processing if an api error is raised"""
        self.transformer.transform.return_value = {"key": "value"}
        self.api.create_immunization.side_effect = ImmunizationApiUnhandledError({})

        self.processor.process()

        self.api.create_immunization.assert_called_once()

    def test_continue_on_action_missing(self):
        """it should continue processing if an action is missing"""
        self.parser.parse_rows.return_value = iter([["H0", "H1"], ["v0", "v1"]])

        self.processor.process()

        self.api.create_immunization.assert_not_called()

    # def test_continue_on_unrecognised_action(self):
    #     """it should continue processing if an action is not recognised"""
    #     self.parser.parse_rows.return_value = iter(
    #         [["H0", "H1", "ACTION_FLAG"],
    #          ["v0", "v1", Action.CREATE.value],
    #          ["v0", "v1", "UNRECOGNISED"]])

    #     self.processor.process()  # circular issue

    #     self.api.create_immunization.assert_called_once()

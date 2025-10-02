import unittest

from batch.batch_filename_to_events_mapper import BatchFilenameToEventsMapper
from models.errors import MessageNotSuccessfulError

MOCK_SUPPLIER_ONE_RSV_EVENT_ONE = {
    "row_id": "row-1",
    "file_key": "supplier_one_rsv_file_key",
    "created_at_formatted_string": "2025-01-24T12:00:00Z",
    "supplier": "supplier_one",
    "vax_type": "RSV",
    "local_id": "local-1",
    "operation_requested": "CREATE"
}

MOCK_SUPPLIER_ONE_RSV_EVENT_TWO = {
    "row_id": "row-2",
    "file_key": "supplier_one_rsv_file_key",
    "created_at_formatted_string": "2025-01-24T12:00:00Z",
    "supplier": "supplier_one",
    "vax_type": "RSV",
    "local_id": "local-2",
    "operation_requested": "UPDATE"
}

MOCK_SUPPLIER_TWO_COVID_EVENT_ONE = {
    "row_id": "row-1",
    "file_key": "supplier_two_covid19_file_key",
    "created_at_formatted_string": "2025-01-24T14:00:00Z",
    "supplier": "supplier_two",
    "vax_type": "COVID-19",
    "local_id": "local-1",
    "operation_requested": "CREATE"
}


class TestBatchFilenameToEventsMapper(unittest.TestCase):
    expected_key_supplier_one = "supplier_one_rsv_file_key_2025-01-24T12:00:00Z"
    expected_key_supplier_two = "supplier_two_covid19_file_key_2025-01-24T14:00:00Z"

    def setUp(self) -> None:
        self.batch_filename_to_events_mapper = BatchFilenameToEventsMapper()

    def test_add_event_creates_new_key(self):
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_ONE_RSV_EVENT_ONE)

        result = self.batch_filename_to_events_mapper.get_map()

        self.assertIn(self.expected_key_supplier_one, result)
        self.assertEqual(result[self.expected_key_supplier_one], [MOCK_SUPPLIER_ONE_RSV_EVENT_ONE])

    def test_add_event_appends_to_existing_key(self):
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_ONE_RSV_EVENT_ONE)
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_ONE_RSV_EVENT_TWO)

        result = self.batch_filename_to_events_mapper.get_map()

        self.assertIn(self.expected_key_supplier_one, result)
        self.assertEqual(result[self.expected_key_supplier_one], [
            MOCK_SUPPLIER_ONE_RSV_EVENT_ONE,
            MOCK_SUPPLIER_ONE_RSV_EVENT_TWO
        ])

    def test_mapper_handles_events_from_multiple_files(self):
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_ONE_RSV_EVENT_ONE)
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_ONE_RSV_EVENT_TWO)
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_TWO_COVID_EVENT_ONE)

        result = self.batch_filename_to_events_mapper.get_map()

        self.assertEqual(len(result.keys()), 2)
        self.assertIn(self.expected_key_supplier_one, result)
        self.assertEqual(result[self.expected_key_supplier_one], [
            MOCK_SUPPLIER_ONE_RSV_EVENT_ONE,
            MOCK_SUPPLIER_ONE_RSV_EVENT_TWO
        ])
        self.assertIn(self.expected_key_supplier_two, result)
        self.assertEqual(result[self.expected_key_supplier_two], [MOCK_SUPPLIER_TWO_COVID_EVENT_ONE])

    def test_event_with_missing_filename_data_raises_error(self):
        incomplete_event = {
            "file_key": "file1"
            # Missing 'created_at_formatted_string'
        }
        with self.assertRaises(MessageNotSuccessfulError) as error:
            self.batch_filename_to_events_mapper.add_event(incomplete_event)

        self.assertEqual(error.exception.message, "Filename data was not present")

    def test_get_map_returns_a_copy_instead_of_exact_references(self):
        self.batch_filename_to_events_mapper.add_event(MOCK_SUPPLIER_ONE_RSV_EVENT_ONE)

        result = self.batch_filename_to_events_mapper.get_map()

        self.assertNotEqual(id(result), id(self.batch_filename_to_events_mapper._filename_to_events_map))


if __name__ == "__main__":
    unittest.main()

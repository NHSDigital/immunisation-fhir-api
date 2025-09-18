import unittest
from unittest.mock import patch, MagicMock

import ieds_db_operations


class TestIedsDbOperationsConditional(unittest.TestCase):
    def setUp(self):
        # Patch logger to suppress output
        self.logger_patcher = patch('ieds_db_operations.logger')
        self.mock_logger = self.logger_patcher.start()

        # Patch get_ieds_table_name and get_ieds_table
        self.get_ieds_table_name_patcher = patch('ieds_db_operations.get_ieds_table_name')
        self.mock_get_ieds_table_name = self.get_ieds_table_name_patcher.start()
        self.mock_get_ieds_table_name.return_value = 'test-table'

        self.get_ieds_table_patcher = patch('ieds_db_operations.get_ieds_table')
        self.mock_get_ieds_table = self.get_ieds_table_patcher.start()

        # Patch dynamodb client
        self.dynamodb_client_patcher = patch('ieds_db_operations.dynamodb_client')
        self.mock_dynamodb_client = self.dynamodb_client_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_ieds_update_patient_id_empty_inputs(self):
        res = ieds_db_operations.ieds_update_patient_id('', '')
        self.assertEqual(res['status'], 'error')

    def test_ieds_update_patient_id_same_ids(self):
        res = ieds_db_operations.ieds_update_patient_id('a', 'a')
        self.assertEqual(res['status'], 'success')

    def test_ieds_update_with_items_to_update_uses_provided_list(self):
        items = [{'PK': 'Patient#1'}, {'PK': 'Patient#1#r2'}]
        # patch transact_write_items to return success
        self.mock_dynamodb_client.transact_write_items = MagicMock(return_value={'ResponseMetadata': {'HTTPStatusCode': 200}})

        res = ieds_db_operations.ieds_update_patient_id('1', '2', items_to_update=items)
        self.assertEqual(res['status'], 'success')
        # ensure transact called at least once
        self.mock_dynamodb_client.transact_write_items.assert_called()

    def test_ieds_update_batches_multiple_calls(self):
        # create 60 items to force 3 batches (25,25,10)
        items = [{'PK': f'Patient#old#{i}'} for i in range(60)]
        called = []

        def fake_transact(TransactItems):
            called.append(len(TransactItems))
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}

        self.mock_dynamodb_client.transact_write_items = MagicMock(side_effect=fake_transact)

        res = ieds_db_operations.ieds_update_patient_id('old', 'new', items_to_update=items)
        self.assertEqual(res['status'], 'success')
        # should have been called 3 times
        self.assertEqual(len(called), 3)
        self.assertEqual(called[0], 25)
        self.assertEqual(called[1], 25)
        self.assertEqual(called[2], 10)

    def test_ieds_update_non_200_response(self):
        items = [{'PK': 'Patient#1'}]
        self.mock_dynamodb_client.transact_write_items = MagicMock(return_value={'ResponseMetadata': {'HTTPStatusCode': 500}})

        res = ieds_db_operations.ieds_update_patient_id('1', '2', items_to_update=items)
        self.assertEqual(res['status'], 'error')


if __name__ == '__main__':
    unittest.main()

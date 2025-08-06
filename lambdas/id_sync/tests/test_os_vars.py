import unittest
import os
from unittest.mock import patch

import os_vars


class TestOsVars(unittest.TestCase):

    def setUp(self):
        os_vars._ieds_table_name = None
        os_vars._delta_table_name = None
        os_vars._pds_env = None

    @patch.dict(os.environ, {"IEDS_TABLE_NAME": "ieds-table", "DELTA_TABLE_NAME": "delta-table"})
    def test_get_ieds_table_name(self):
        self.assertEqual(os_vars.get_ieds_table_name(), "ieds-table")

    @patch.dict(os.environ, {"IEDS_TABLE_NAME": "ieds-table"})
    def test_get_ieds_table_name_cached(self):
        self.assertEqual(os_vars.get_ieds_table_name_cached(), "ieds-table")
        del os.environ["IEDS_TABLE_NAME"]
        self.assertEqual(os_vars.get_ieds_table_name_cached(), "ieds-table")

    @patch.dict(os.environ, {"PDS_ENV": "prod"})
    def test_get_pds_env_with_value(self):
        self.assertEqual(os_vars.get_pds_env(), "prod")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_pds_env_default(self):
        self.assertEqual(os_vars.get_pds_env(), "int")

    @patch.dict(os.environ, {"PDS_ENV": "prod"})
    def test_get_pds_env_cached(self):
        self.assertEqual(os_vars.get_pds_env_cached(), "prod")
        del os.environ["PDS_ENV"]
        self.assertEqual(os_vars.get_pds_env_cached(), "prod")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_pds_env_cached_default(self):
        self.assertEqual(os_vars.get_pds_env_cached(), "int")

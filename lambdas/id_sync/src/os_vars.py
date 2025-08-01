import os
from typing import Optional


def get_ieds_table_name() -> str:
    """Get the IEDS table name from environment variables."""
    return os.environ["IEDS_TABLE_NAME"]


def get_pds_env() -> str:
    """Get the PDS environment from environment variables."""
    return os.getenv("PDS_ENV", "int")


# Optional: Cached versions for performance
_ieds_table_name: Optional[str] = None
_pds_env: Optional[str] = None


def get_ieds_table_name_cached() -> str:
    """Get the IEDS table name (cached version)."""
    global _ieds_table_name
    if _ieds_table_name is None:
        _ieds_table_name = os.environ["IEDS_TABLE_NAME"]
    return _ieds_table_name


def get_pds_env_cached() -> str:
    """Get the PDS environment (cached version)."""
    global _pds_env
    if _pds_env is None:
        _pds_env = os.getenv("PDS_ENV", "int")
    return _pds_env

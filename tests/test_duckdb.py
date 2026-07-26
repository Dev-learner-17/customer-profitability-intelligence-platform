import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.duckdb_layer import db


def test_duckdb_connection_singleton():
    assert db is not None
    
def test_duckdb_query_execution():
    # Execute a simple in-memory query not relying on files
    res = db.query("SELECT 1 as test_col")
    assert len(res) == 1
    assert res['test_col'].iloc[0] == 1

def test_duckdb_macro_kpis():
    # It should return a dict
    kpis = db.get_macro_kpis()
    assert isinstance(kpis, dict)

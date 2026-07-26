import os
import sys
import time

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.duckdb_layer import db


def benchmark():
    parquet_path = 'legacy/ui_sample.parquet'
    
    # 1. Pandas Load Time
    start = time.time()
    try:
        pd.read_parquet(parquet_path)
        pd_load_time = time.time() - start
    except Exception as e:
        pd_load_time = -1
        print("Pandas load failed:", e)

    # 2. DuckDB Load/Query Time
    start = time.time()
    try:
        db.query(f"SELECT * FROM read_parquet('{parquet_path}')")
        duck_load_time = time.time() - start
    except Exception as e:
        duck_load_time = -1
        print("DuckDB query failed:", e)

    print("--- BENCHMARK RESULTS ---")
    print(f"Pandas read_parquet latency : {pd_load_time:.4f} seconds" if pd_load_time > 0 else "Pandas failed.")
    print(f"DuckDB SQL query latency    : {duck_load_time:.4f} seconds" if duck_load_time > 0 else "DuckDB failed.")

    with open('benchmark.md', 'w') as f:
        f.write("# Performance Benchmarking Report\n\n")
        f.write("| Metric | Latency (seconds) |\n")
        f.write("| --- | --- |\n")
        f.write(f"| Pandas `read_parquet` | {pd_load_time:.4f} |\n")
        f.write(f"| DuckDB `SELECT *` | {duck_load_time:.4f} |\n")
        
if __name__ == '__main__':
    benchmark()

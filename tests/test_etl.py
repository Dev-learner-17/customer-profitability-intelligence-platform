import numpy as np
import pandas as pd


def test_etl_financial_validation():
    # Simulate ETL dropping bad financial records
    # Order Item Total should be approximately equal to Price * Qty - Discount
    df = pd.DataFrame({
        'Order Item Product Price': [50.0, 100.0, 10.0],
        'Order Item Quantity': [2, 1, 5],
        'Order Item Discount': [10.0, 0.0, 0.0],
        'Order Item Total': [90.0, 100.0, 999.0] # 999 is invalid
    })
    
    expected = (df['Order Item Product Price'] * df['Order Item Quantity']) - df['Order Item Discount']
    discrepancy = np.abs(df['Order Item Total'] - expected)
    tolerance = 0.05
    
    valid_mask = discrepancy <= tolerance
    df_clean = df[valid_mask].copy()
    
    assert len(df_clean) == 2
    assert df_clean['Order Item Total'].iloc[0] == 90.0

def test_outlier_handling():
    # Simulate negative values handled in ETL
    df = pd.DataFrame({'Sales': [100, 200, -50, 400]})
    # In ETL, negative sales are dropped or zeroed
    df_clean = df[df['Sales'] >= 0].copy()
    assert len(df_clean) == 3
    assert df_clean['Sales'].min() == 100

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def engineer_product_features(data_dir="processed_data"):
    """
    Engineers advanced product features: Profit Density and Product Efficiency Index (PEI).
    """
    p = Path(data_dir) / "aggregations/product_agg.parquet"
    if not p.exists():
        print(f"File not found: {p}")
        return

    df = pd.read_parquet(p)
    
    # 1. Base Metrics
    df['Margin'] = np.where(df['Total_Sales'] > 0, df['Total_Profit'] / df['Total_Sales'], 0)
    df['Profit_Density'] = df['Profit_Per_Unit'] # already exists
    df['Volume_Contribution'] = df['Units_Sold'] / df['Units_Sold'].sum()

    # 2. Scaling for Index Creation
    scaler = MinMaxScaler()
    df[['Margin_Scaled', 'Profit_Density_Scaled', 'Volume_Scaled']] = scaler.fit_transform(
        df[['Margin', 'Profit_Density', 'Volume_Contribution']]
    )

    # 3. Product Efficiency Index (PEI)
    # PEI = 0.4*Margin + 0.3*Profit_Density + 0.3*Volume_Contribution
    df['Product_Efficiency_Index'] = (
        0.4 * df['Margin_Scaled'] + 
        0.3 * df['Profit_Density_Scaled'] + 
        0.3 * df['Volume_Scaled']
    )

    # Clean up scaled columns
    df = df.drop(columns=['Margin_Scaled', 'Profit_Density_Scaled', 'Volume_Scaled'])

    # Save
    out_path = Path(data_dir) / "aggregations/product_agg_advanced.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Saved advanced product features to {out_path}")


if __name__ == "__main__":
    engineer_product_features()

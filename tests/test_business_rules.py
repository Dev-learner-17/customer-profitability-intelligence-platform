import numpy as np
import pandas as pd


def test_profit_margin_calculation():
    # Margin = Total Profit / Total Sales
    df = pd.DataFrame({"Total_Sales": [100, 200, 0], "Total_Profit": [20, 50, 0]})
    df["Margin"] = np.where(
        df["Total_Sales"] > 0, df["Total_Profit"] / df["Total_Sales"], 0
    )
    assert df["Margin"][0] == 0.2
    assert df["Margin"][1] == 0.25
    assert df["Margin"][2] == 0.0


def test_discount_impact():
    # Expected Sales = Price * Qty - Discount
    df = pd.DataFrame(
        {
            "Order Item Product Price": [50.0, 100.0],
            "Order Item Quantity": [2, 1],
            "Order Item Discount": [10.0, 0.0],
            "Sales": [90.0, 100.0],
        }
    )
    expected = (df["Order Item Product Price"] * df["Order Item Quantity"]) - df[
        "Order Item Discount"
    ]
    discrepancy = np.abs(df["Sales"] - expected)
    assert discrepancy.max() == 0.0


def test_customer_segmentation():
    # Segments based on rules
    df = pd.DataFrame({"Sales": [10000, 2000, 500], "Order_Count": [15, 5, 1]})

    def get_segment(row):
        if row["Sales"] > 5000 and row["Order_Count"] >= 10:
            return "VIP"
        elif row["Sales"] > 1000:
            return "Loyal"
        else:
            return "Occasional"

    df["Segment"] = df.apply(get_segment, axis=1)
    assert df["Segment"][0] == "VIP"
    assert df["Segment"][1] == "Loyal"
    assert df["Segment"][2] == "Occasional"

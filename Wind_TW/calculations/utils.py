# Wind_TW/calculations/utils.py
import numpy as np
import pandas as pd

def interpolate_from_table(df: pd.DataFrame, target_index: float, column_name) -> float:
    """
    通用的 DataFrame 內插工具。
    用於 Kzt 的 K1, K2, K3 表格查表。
    """
    return np.interp(target_index, df.index, df[column_name])

def linear_interp(x, x1, y1, x2, y2):
    """簡單的線性內插"""
    if x <= x1: return y1
    if x >= x2: return y2
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

def get_value_from_df(df: pd.DataFrame, index_val, col_val):
    """安全地從 DataFrame 獲取值，若無則回傳 None 或處理錯誤"""
    try:
        return df.loc[index_val, col_val]
    except KeyError:
        return None
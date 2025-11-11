# Wind_TW/wind_calculations.py (setup_databases 函式更新)

import pandas as pd
import numpy as np

import os
from scipy.integrate import quad  # 用於拱形屋頂的精確計算


# Phase 1: 資料庫
def setup_databases():
    databases = {}
    terrain_data = {
        'alpha': {'A': 0.32, 'B': 0.25, 'C': 0.15}, 'zg': {'A': 500, 'B': 400, 'C': 300},
        'z_min': {'A': 18, 'B': 9, 'C': 4.5}, 'b': {'A': 0.45, 'B': 0.62, 'C': 0.94},
        'c': {'A': 0.45, 'B': 0.30, 'C': 0.20}, 'l_lambda': {'A': 55, 'B': 98, 'C': 152},
        'epsilon_bar': {'A': 0.5, 'B': 0.33, 'C': 0.20},
    }
    databases['TERRAIN_DF'] = pd.DataFrame(terrain_data)
    k1_data = {
        ('A_or_B', '山脊'): {0.20: 0.26, 0.25: 0.33, 0.30: 0.39, 0.35: 0.46, 0.40: 0.52, 0.45: 0.59, 0.50: 0.65},
        ('A_or_B', '懸崖'): {0.20: 0.15, 0.25: 0.19, 0.30: 0.23, 0.35: 0.26, 0.40: 0.33, 0.45: 0.34, 0.50: 0.38},
        ('A_or_B', '山丘'): {0.20: 0.19, 0.25: 0.24, 0.30: 0.29, 0.35: 0.33, 0.40: 0.38, 0.45: 0.43, 0.50: 0.48},
        ('C', '山脊'): {0.20: 0.29, 0.25: 0.36, 0.30: 0.43, 0.35: 0.51, 0.40: 0.58, 0.45: 0.65, 0.50: 0.72},
        ('C', '懸崖'): {0.20: 0.17, 0.25: 0.21, 0.30: 0.26, 0.35: 0.30, 0.40: 0.34, 0.45: 0.38, 0.50: 0.43},
        ('C', '山丘'): {0.20: 0.21, 0.25: 0.26, 0.30: 0.32, 0.35: 0.37, 0.40: 0.42, 0.45: 0.47, 0.50: 0.53}
    }
    k1_df = pd.DataFrame(k1_data).sort_index();
    k1_df.index.name = 'H/Lh';
    databases['K1_DF'] = k1_df
    k2_data = {
        '懸崖': {-4.00: 0.00, -1.50: 0.00, -1.00: 0.33, -0.50: 0.67, 0.00: 1.00, 0.50: 0.88, 1.00: 0.75, 1.50: 0.63,
                 4.00: 0.00},
        '山脊或山丘': {-4.00: 0.00, -1.50: 0.00, -1.00: 0.33, -0.50: 0.67, 0.00: 1.00, 0.50: 0.67, 1.00: 0.33,
                       1.50: 0.00, 4.00: 0.00}
    }
    k2_df = pd.DataFrame(k2_data).sort_index();
    k2_df.index.name = 'x/Lh';
    databases['K2_DF'] = k2_df
    k3_data = {
        '山脊': {0.00: 1.00, 0.10: 0.74, 0.50: 0.22, 1.00: 0.05, 1.50: 0.01, 2.00: 0.00},
        '懸崖': {0.00: 1.00, 0.10: 0.78, 0.50: 0.29, 1.00: 0.08, 1.50: 0.02, 2.00: 0.00},
        '山丘': {0.00: 1.00, 0.10: 0.67, 0.50: 0.14, 1.00: 0.02, 1.50: 0.00, 2.00: 0.00},
    }
    k3_df = pd.DataFrame(k3_data).sort_index();
    k3_df.index.name = 'z/Lh';
    databases['K3_DF'] = k3_df
    leeward_wall_data = {'Cp': {0: -0.5, 1: -0.5, 2: -0.3, 4: -0.2}};
    leeward_wall_df = pd.DataFrame(leeward_wall_data);
    leeward_wall_df.index.name = 'L/B';
    databases['LEEWARD_WALL_DF'] = leeward_wall_df
    roof_cp_data_pos = {
        0.0: {0.3: -0.7, 1.5: -0.7}, 10.0: {0.3: 0.2, 1.5: -0.9}, 15.0: {0.3: 0.2, 1.5: -0.9},
        20.0: {0.3: 0.2, 1.5: -0.9}, 30.0: {0.3: 0.3, 1.5: -0.9}, 40.0: {0.3: 0.4, 1.5: -0.35},
        50.0: {0.3: 0.5, 1.5: 0.2}, 60.0: {0.3: 0.6, 1.5: 0.6},
    }
    roof_cp_data_neg = {
        0.0: {0.3: -0.7, 1.5: -0.7}, 10.0: {0.3: -0.9, 1.5: -0.9}, 15.0: {0.3: -0.9, 1.5: -0.9},
        20.0: {0.3: 0.2, 1.5: -0.9}, 30.0: {0.3: 0.3, 1.5: -0.9}, 40.0: {0.3: 0.4, 1.5: -0.35},
        50.0: {0.3: 0.5, 1.5: 0.2}, 60.0: {0.3: 0.6, 1.5: 0.6},
    }
    roof_cp_df_pos = pd.DataFrame(roof_cp_data_pos);
    roof_cp_df_neg = pd.DataFrame(roof_cp_data_neg)
    roof_cp_df_pos.index.name = 'h/L';
    roof_cp_df_pos.columns.name = 'theta';
    databases['ROOF_CP_DF_POS'] = roof_cp_df_pos
    roof_cp_df_neg.index.name = 'h/L';
    roof_cp_df_neg.columns.name = 'theta';
    databases['ROOF_CP_DF_NEG'] = roof_cp_df_neg
    gcpi_data = {'開放式建築': [0.00], '部分封閉式建築': [+1.146, -1.146], '封閉式建築': [+0.375, -0.375]}
    databases['GCPI_DATA'] = gcpi_data
    lambda_data = {
        'A': {5: 0.016, 20: 0.040}, 'B': {5: 0.035, 20: 0.072}, 'C': {5: 0.092, 20: 0.142}
    }
    lambda_df = pd.DataFrame(lambda_data);
    lambda_df.index.name = 'h(m)';
    databases['LAMBDA_DF'] = lambda_df
    cpc1_data = {0: {'p': 0, 'n': 0}, 50: {'p': 0.715, 'n': 0.462}};
    cpc1_df = pd.DataFrame.from_dict(cpc1_data, orient='index');
    cpc1_df.index.name = 'theta';
    databases['CPC1_DF'] = cpc1_df
    cpc2_data = {0: {'p': -1.410, 'n': -1.410}, 50: {'p': 0.510, 'n': -0.860}};
    cpc2_df = pd.DataFrame.from_dict(cpc2_data, orient='index');
    cpc2_df.index.name = 'theta';
    databases['CPC2_DF'] = cpc2_df
    databases['CPC3_VALUE'] = -1.410
    chimney_cf_data = {
        ('方形', '垂直', '所有'): {1: 1.3, 7: 1.4, 25: 2.0}, ('方形', '對角', '所有'): {1: 1.0, 7: 1.1, 25: 1.5},
        ('六邊形或八邊形', 'N/A', '所有'): {1: 1.0, 7: 1.2, 25: 1.4},
        ('圓形', '>1.70', '中度光滑'): {1: 0.5, 7: 0.6, 25: 0.7},
        ('圓形', '>1.70', '粗糙'): {1: 0.7, 7: 0.8, 25: 0.9}, ('圓形', '>1.70', '極粗糙'): {1: 0.8, 7: 1.0, 25: 1.2},
        ('圓形', '<=1.70', '所有'): {1: 0.7, 7: 0.8, 25: 1.2},
    }
    chimney_cf_df = pd.DataFrame.from_dict(chimney_cf_data, orient='index')
    chimney_cf_df.columns = chimney_cf_df.columns.astype(float);
    chimney_cf_df.columns.name = 'h/D'
    chimney_cf_df.index = pd.MultiIndex.from_tuples(chimney_cf_df.index, names=['形狀', '條件', '粗糙度'])
    databases['CHIMNEY_CF_DF'] = chimney_cf_df

    # =================================================================
    # ==== START: 新增 ASCE 7 Fig 29.3-1 實體標示物 Cf 表格 ====
    # =================================================================
    # --- 表格一: Force Coefficients, Cf, for Case A and Case B ---
    solid_sign_case_ab_data = {
        # B/s: {s/h: Cf}
        0.05: {1: 1.80, 0.9: 1.85, 0.7: 1.90, 0.5: 1.95, 0.3: 1.95, 0.2: 1.95, 0.16: 1.95},
        0.1: {1: 1.70, 0.9: 1.75, 0.7: 1.85, 0.5: 1.85, 0.3: 1.90, 0.2: 1.90, 0.16: 1.90},
        0.2: {1: 1.65, 0.9: 1.70, 0.7: 1.75, 0.5: 1.80, 0.3: 1.85, 0.2: 1.85, 0.16: 1.85},
        0.5: {1: 1.55, 0.9: 1.60, 0.7: 1.70, 0.5: 1.75, 0.3: 1.80, 0.2: 1.80, 0.16: 1.80},
        1: {1: 1.45, 0.9: 1.55, 0.7: 1.65, 0.5: 1.75, 0.3: 1.80, 0.2: 1.80, 0.16: 1.80},
        2: {1: 1.40, 0.9: 1.50, 0.7: 1.60, 0.5: 1.70, 0.3: 1.80, 0.2: 1.80, 0.16: 1.80},
        4: {1: 1.35, 0.9: 1.45, 0.7: 1.60, 0.5: 1.70, 0.3: 1.80, 0.2: 1.80, 0.16: 1.85},
        5: {1: 1.35, 0.9: 1.45, 0.7: 1.55, 0.5: 1.70, 0.3: 1.80, 0.2: 1.80, 0.16: 1.85},
        10: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.70, 0.3: 1.80, 0.2: 1.85, 0.16: 1.85},
        20: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.70, 0.3: 1.85, 0.2: 1.90, 0.16: 1.90},
        30: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.70, 0.3: 1.85, 0.2: 1.90, 0.16: 1.90},
        45: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.75, 0.3: 1.85, 0.2: 1.95, 0.16: 1.95}
    }
    solid_sign_case_ab_df = pd.DataFrame(solid_sign_case_ab_data)
    solid_sign_case_ab_df.index.name = 's/h'
    solid_sign_case_ab_df.columns.name = 'B/s'
    databases['SOLID_SIGN_CASE_AB_DF'] = solid_sign_case_ab_df

    # --- 表格二: Force Coefficients, Cf, for Case C ---
    solid_sign_case_c_data = {
        # B/s: {'0-s': val, 's-2s': val, ...}
        2: {'0-s': 2.25, 's-2s': 1.50},
        3: {'0-s': 2.60, 's-2s': 1.70, '2s-3s': 1.15},
        4: {'0-s': 2.90, 's-2s': 1.90, '2s-3s': 1.30, '3s-10s': 1.10},
        5: {'0-s': 3.10, 's-2s': 2.00, '2s-3s': 1.45, '3s-10s': 1.05},
        6: {'0-s': 3.30, 's-2s': 2.15, '2s-3s': 1.55, '3s-10s': 1.05},
        7: {'0-s': 3.40, 's-2s': 2.25, '2s-3s': 1.65, '3s-10s': 1.05},
        8: {'0-s': 3.55, 's-2s': 2.30, '2s-3s': 1.70, '3s-10s': 1.05},
        9: {'0-s': 3.65, 's-2s': 2.35, '2s-3s': 1.75, '3s-10s': 1.00},
        10: {'0-s': 3.75, 's-2s': 2.45, '2s-3s': 1.85, '3s-10s': 0.95, '3s-4s': 0.95, '4s-5s': 0.95, '5s-10s': 0.95,
             '>10s': 0.55},
        13: {'0-s': 4.00, 's-2s': 2.60, '2s-3s': 2.00, '3s-4s': 1.50, '4s-5s': 1.35, '5s-10s': 0.90, '>10s': 0.55},
        46: {'0-s': 4.30, 's-2s': 2.55, '2s-3s': 1.95, '3s-4s': 1.85, '4s-5s': 1.85, '5s-10s': 1.10, '>10s': 0.55},
    }
    solid_sign_case_c_df = pd.DataFrame(solid_sign_case_c_data).transpose()
    solid_sign_case_c_df.index.name = 'B/s'
    solid_sign_case_c_df.columns.name = 'Region'
    databases['SOLID_SIGN_CASE_C_DF'] = solid_sign_case_c_df

    # --- 表格三: Reduction Factor for Case C with return corner ---
    reduction_factor_data = {0.3: 0.90, 1.0: 0.75, 2.0: 0.60}
    reduction_factor_series = pd.Series(reduction_factor_data)
    reduction_factor_series.index.name = 'Lr/s'
    databases['SOLID_SIGN_REDUCTION_DF'] = reduction_factor_series
    # =================================================================

    # =================================================================
    # ====   START: 新增 表 2.13 角柱體形狀之風力係數 Cf 及 R    ====
    # =================================================================
    column_cf_data = {
        # (形狀, 風向): Cf
        ('長方柱', '垂直於長邊'): 2.2,
        ('長方柱', '垂直於短邊'): 1.4,
        ('等邊三角柱', '循著頂點'): 1.2,
        ('等邊三角柱', '垂直於面'): 2.0,
        ('直角等腰三角柱', '循著直角頂'): 1.55,
    }
    databases['COLUMN_CF_DATA'] = column_cf_data  # 直接存為字典，查詢更方便

    # 表 2.13 的下半部 (修正係數 R)
    column_r_factor_data = {
        'R': {4: 0.6, 8: 0.7, 40: 0.8}
    }
    column_r_factor_df = pd.DataFrame(column_r_factor_data)
    column_r_factor_df.index.name = '2h/D_max'  # 索引代表該範圍的最大值
    databases['COLUMN_R_FACTOR_DF'] = column_r_factor_df
    # =================================================================

    # =================================================================
    # ====      START: 新增 表 2.11 中空標示物之風力係數 Cf      ====
    # =================================================================
    hollow_sign_cf_data = {
        # 索引: (構材類型, D*sqrt(q) 條件)
        ('平邊構材', 'N/A'): {'<0.1': 2.0, '0.1-0.29': 1.8, '0.3-0.7': 1.6},
        ('圓形斷面構材', '<=1.70'): {'<0.1': 1.2, '0.1-0.29': 1.3, '0.3-0.7': 1.5},
        ('圓形斷面構材', '>1.70'): {'<0.1': 0.8, '0.1-0.29': 0.9, '0.3-0.7': 1.1}
    }
    hollow_sign_cf_df = pd.DataFrame.from_dict(hollow_sign_cf_data, orient='index')
    hollow_sign_cf_df.columns.name = 'phi_range'
    hollow_sign_cf_df.index = pd.MultiIndex.from_tuples(hollow_sign_cf_df.index, names=['member_type', 'condition'])
    databases['HOLLOW_SIGN_CF_DF'] = hollow_sign_cf_df
    # =================================================================

    # =================================================================
    # ==== START: ASCE 7 Figure 27.3-4 Shed Roofs, CN (作為 Cf 使用) ====
    # =================================================================
    # 數據結構: (風向, 氣流條件, 係數類型): {(角度, 載重工況): 係數值, ...}
    shed_roof_cn_data = {
        ('gamma_0', 'clear', 'C_NW'): {(0, 'A'): 1.2, (0, 'B'): -1.1, (7.5, 'A'): -0.6, (7.5, 'B'): -1.4,
                                       (15, 'A'): -0.9, (15, 'B'): -1.9, (22.5, 'A'): -1.5, (22.5, 'B'): -2.4,
                                       (30, 'A'): -1.8, (30, 'B'): -2.5, (37.5, 'A'): -1.8, (37.5, 'B'): -2.4,
                                       (45, 'A'): -1.6, (45, 'B'): -2.3},
        ('gamma_0', 'clear', 'C_NL'): {(0, 'A'): 0.3, (0, 'B'): -0.1, (7.5, 'A'): -1.0, (7.5, 'B'): 0.0,
                                       (15, 'A'): -1.3, (15, 'B'): 0.0, (22.5, 'A'): -1.6, (22.5, 'B'): -0.3,
                                       (30, 'A'): -1.8, (30, 'B'): -0.5, (37.5, 'A'): -1.8, (37.5, 'B'): -0.6,
                                       (45, 'A'): -1.8, (45, 'B'): -0.7},
        ('gamma_0', 'obstructed', 'C_NW'): {(0, 'A'): -0.5, (0, 'B'): -1.1, (7.5, 'A'): -1.0, (7.5, 'B'): -1.7,
                                            (15, 'A'): -1.1, (15, 'B'): -2.1, (22.5, 'A'): -1.5, (22.5, 'B'): -2.3,
                                            (30, 'A'): -1.5, (30, 'B'): -2.3, (37.5, 'A'): -1.5, (37.5, 'B'): -2.2,
                                            (45, 'A'): -1.3, (45, 'B'): -1.9},
        ('gamma_0', 'obstructed', 'C_NL'): {(0, 'A'): -1.2, (0, 'B'): -0.6, (7.5, 'A'): -1.5, (7.5, 'B'): -0.8,
                                            (15, 'A'): -1.5, (15, 'B'): -0.6, (22.5, 'A'): -1.7, (22.5, 'B'): -0.9,
                                            (30, 'A'): -1.8, (30, 'B'): -1.1, (37.5, 'A'): -1.8, (37.5, 'B'): -1.1,
                                            (45, 'A'): -1.8, (45, 'B'): -1.2},
        ('gamma_180', 'clear', 'C_NW'): {(0, 'A'): 1.2, (0, 'B'): -1.1, (7.5, 'A'): 0.9, (7.5, 'B'): 1.6,
                                         (15, 'A'): 1.3, (15, 'B'): 1.8, (22.5, 'A'): 1.7, (22.5, 'B'): 2.2,
                                         (30, 'A'): 2.1, (30, 'B'): 2.6, (37.5, 'A'): 2.1, (37.5, 'B'): 2.7,
                                         (45, 'A'): 2.2, (45, 'B'): 2.6},
        ('gamma_180', 'clear', 'C_NL'): {(0, 'A'): 0.3, (0, 'B'): -0.1, (7.5, 'A'): 1.5, (7.5, 'B'): 0.3,
                                         (15, 'A'): 1.6, (15, 'B'): 0.6, (22.5, 'A'): 1.8, (22.5, 'B'): 0.7,
                                         (30, 'A'): 2.1, (30, 'B'): 1.0, (37.5, 'A'): 2.2, (37.5, 'B'): 1.1,
                                         (45, 'A'): 2.5, (45, 'B'): 1.4},
        ('gamma_180', 'obstructed', 'C_NW'): {(0, 'A'): -0.5, (0, 'B'): -1.1, (7.5, 'A'): -0.2, (7.5, 'B'): 0.8,
                                              (15, 'A'): 0.4, (15, 'B'): 1.2, (22.5, 'A'): 0.5, (22.5, 'B'): 1.3,
                                              (30, 'A'): 0.6, (30, 'B'): 1.6, (37.5, 'A'): 0.7, (37.5, 'B'): 1.9,
                                              (45, 'A'): 0.8, (45, 'B'): 2.1},
        ('gamma_180', 'obstructed', 'C_NL'): {(0, 'A'): -1.2, (0, 'B'): -0.6, (7.5, 'A'): -1.2, (7.5, 'B'): -0.3,
                                              (15, 'A'): -1.1, (15, 'B'): -0.3, (22.5, 'A'): -1.0, (22.5, 'B'): 0.0,
                                              (30, 'A'): -1.0, (30, 'B'): 0.1, (37.5, 'A'): -0.9, (37.5, 'B'): 0.3,
                                              (45, 'A'): -0.9, (45, 'B'): 0.4}
    }

    shed_roof_cn_df = pd.DataFrame(shed_roof_cn_data)
    shed_roof_cn_df.index.names = ['theta', 'load_case']
    shed_roof_cn_df.columns.names = ['wind_direction', 'flow_condition', 'coefficient_type']
    databases['SHED_ROOF_CN_DF'] = shed_roof_cn_df

    # =========================================================================
    # ==== START: 【新增】ASCE 7-16 FIGURE 30.7-1 Monoslope Roof C&C, CN  ====
    # =========================================================================
    monoslope_cc_cn_data = {
        # ('Flow Condition', Theta, 'Area Condition'): {'Zone3+': val, 'Zone3-': val, ...}
        ('Clear', 0, '<=a^2'): {'Z3+': 2.4, 'Z3-': -3.3, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 0, '>a^2, <=4a^2'): {'Z3+': 1.8, 'Z3-': -1.7, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 0, '>4a^2'): {'Z3+': 1.2, 'Z3-': -1.1, 'Z2+': 1.2, 'Z2-': -1.1, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 7.5, '<=a^2'): {'Z3+': 3.2, 'Z3-': -4.2, 'Z2+': 2.4, 'Z2-': -2.1, 'Z1+': 1.6, 'Z1-': -1.4},
        ('Clear', 7.5, '>a^2, <=4a^2'): {'Z3+': 2.4, 'Z3-': -2.1, 'Z2+': 2.4, 'Z2-': -2.1, 'Z1+': 1.6, 'Z1-': -1.4},
        ('Clear', 7.5, '>4a^2'): {'Z3+': 1.6, 'Z3-': -1.4, 'Z2+': 1.6, 'Z2-': -1.4, 'Z1+': 1.6, 'Z1-': -1.4},
        ('Clear', 15, '<=a^2'): {'Z3+': 3.6, 'Z3-': -3.8, 'Z2+': 2.7, 'Z2-': -2.9, 'Z1+': 1.8, 'Z1-': -1.9},
        ('Clear', 15, '>a^2, <=4a^2'): {'Z3+': 2.7, 'Z3-': -2.9, 'Z2+': 2.7, 'Z2-': -2.9, 'Z1+': 1.8, 'Z1-': -1.9},
        ('Clear', 15, '>4a^2'): {'Z3+': 1.8, 'Z3-': -1.9, 'Z2+': 1.8, 'Z2-': -1.9, 'Z1+': 1.8, 'Z1-': -1.9},
        ('Clear', 30, '<=a^2'): {'Z3+': 5.2, 'Z3-': -5, 'Z2+': 3.9, 'Z2-': -3.8, 'Z1+': 2.6, 'Z1-': -2.5},
        ('Clear', 30, '>a^2, <=4a^2'): {'Z3+': 3.9, 'Z3-': -3.8, 'Z2+': 3.9, 'Z2-': -3.8, 'Z1+': 2.6, 'Z1-': -2.5},
        ('Clear', 30, '>4a^2'): {'Z3+': 2.6, 'Z3-': -2.5, 'Z2+': 2.6, 'Z2-': -2.5, 'Z1+': 2.6, 'Z1-': -2.5},
        ('Clear', 45, '<=a^2'): {'Z3+': 5.2, 'Z3-': -4.6, 'Z2+': 3.9, 'Z2-': -3.5, 'Z1+': 2.6, 'Z1-': -2.3},
        ('Clear', 45, '>a^2, <=4a^2'): {'Z3+': 3.9, 'Z3-': -3.5, 'Z2+': 3.9, 'Z2-': -3.5, 'Z1+': 2.6, 'Z1-': -2.3},
        ('Clear', 45, '>4a^2'): {'Z3+': 2.6, 'Z3-': -2.3, 'Z2+': 2.6, 'Z2-': -2.3, 'Z1+': 2.6, 'Z1-': -2.3},
        ('Obstructed', 0, '<=a^2'): {'Z3+': 1, 'Z3-': -3.6, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 0, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 0, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 7.5, '<=a^2'): {'Z3+': 1.6, 'Z3-': -5.1, 'Z2+': 1.2, 'Z2-': -2.6, 'Z1+': 0.8, 'Z1-': -1.7},
        ('Obstructed', 7.5, '>a^2, <=4a^2'): {'Z3+': 1.2, 'Z3-': -2.6, 'Z2+': 1.2, 'Z2-': -2.6, 'Z1+': 0.8,
                                              'Z1-': -1.7},
        ('Obstructed', 7.5, '>4a^2'): {'Z3+': 0.8, 'Z3-': -1.7, 'Z2+': 0.8, 'Z2-': -1.7, 'Z1+': 0.8, 'Z1-': -1.7},
        ('Obstructed', 15, '<=a^2'): {'Z3+': 2.4, 'Z3-': -4.2, 'Z2+': 1.8, 'Z2-': -3.2, 'Z1+': 1.2, 'Z1-': -2.1},
        ('Obstructed', 15, '>a^2, <=4a^2'): {'Z3+': 1.8, 'Z3-': -3.2, 'Z2+': 1.8, 'Z2-': -3.2, 'Z1+': 1.2, 'Z1-': -2.1},
        ('Obstructed', 15, '>4a^2'): {'Z3+': 1.2, 'Z3-': -2.1, 'Z2+': 1.2, 'Z2-': -2.1, 'Z1+': 1.2, 'Z1-': -2.1},
        ('Obstructed', 30, '<=a^2'): {'Z3+': 3.2, 'Z3-': -4.6, 'Z2+': 2.4, 'Z2-': -3.5, 'Z1+': 1.6, 'Z1-': -2.3},
        ('Obstructed', 30, '>a^2, <=4a^2'): {'Z3+': 2.4, 'Z3-': -3.5, 'Z2+': 2.4, 'Z2-': -3.5, 'Z1+': 1.6, 'Z1-': -2.3},
        ('Obstructed', 30, '>4a^2'): {'Z3+': 1.6, 'Z3-': -2.3, 'Z2+': 1.6, 'Z2-': -2.3, 'Z1+': 1.6, 'Z1-': -2.3},
        ('Obstructed', 45, '<=a^2'): {'Z3+': 4.2, 'Z3-': -3.8, 'Z2+': 3.2, 'Z2-': -2.9, 'Z1+': 2.1, 'Z1-': -1.9},
        ('Obstructed', 45, '>a^2, <=4a^2'): {'Z3+': 3.2, 'Z3-': -2.9, 'Z2+': 3.2, 'Z2-': -2.9, 'Z1+': 2.1, 'Z1-': -1.9},
        ('Obstructed', 45, '>4a^2'): {'Z3+': 2.1, 'Z3-': -1.9, 'Z2+': 2.1, 'Z2-': -1.9, 'Z1+': 2.1, 'Z1-': -1.9},
    }
    monoslope_cc_cn_df = pd.DataFrame.from_dict(monoslope_cc_cn_data, orient='index')
    monoslope_cc_cn_df.index = pd.MultiIndex.from_tuples(monoslope_cc_cn_df.index,
                                                         names=['flow_condition', 'theta', 'area_condition'])
    databases['MONOSLOPE_CC_CN_DF'] = monoslope_cc_cn_df.sort_index()

    # =========================================================================
    # ==== START: 【新增】ASCE 7-16 FIGURE 30.7-2 Pitched Roof C&C, CN   ====
    # =========================================================================
    pitched_cc_cn_data = {
        # ('Flow Condition', Theta, 'Area Condition'): {'Zone3+': val, 'Zone3-': val, ...}
        ('Clear', 0, '<=a^2'): {'Z3+': 2.4, 'Z3-': -3.3, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 0, '>a^2, <=4a^2'): {'Z3+': 1.8, 'Z3-': -1.7, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 0, '>4a^2'): {'Z3+': 1.2, 'Z3-': -1.1, 'Z2+': 1.2, 'Z2-': -1.1, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 7.5, '<=a^2'): {'Z3+': 2.2, 'Z3-': -3.6, 'Z2+': 1.7, 'Z2-': -1.8, 'Z1+': 1.1, 'Z1-': -1.2},
        ('Clear', 7.5, '>a^2, <=4a^2'): {'Z3+': 1.7, 'Z3-': -1.8, 'Z2+': 1.7, 'Z2-': -1.8, 'Z1+': 1.1, 'Z1-': -1.2},
        ('Clear', 7.5, '>4a^2'): {'Z3+': 1.1, 'Z3-': -1.2, 'Z2+': 1.1, 'Z2-': -1.2, 'Z1+': 1.1, 'Z1-': -1.2},
        ('Clear', 15, '<=a^2'): {'Z3+': 2.2, 'Z3-': -2.2, 'Z2+': 1.7, 'Z2-': -1.7, 'Z1+': 1.1, 'Z1-': -1.1},
        ('Clear', 15, '>a^2, <=4a^2'): {'Z3+': 1.7, 'Z3-': -1.7, 'Z2+': 1.7, 'Z2-': -1.7, 'Z1+': 1.1, 'Z1-': -1.1},
        ('Clear', 15, '>4a^2'): {'Z3+': 1.1, 'Z3-': -1.1, 'Z2+': 1.1, 'Z2-': -1.1, 'Z1+': 1.1, 'Z1-': -1.1},
        ('Clear', 30, '<=a^2'): {'Z3+': 2.6, 'Z3-': -1.8, 'Z2+': 2.0, 'Z2-': -1.4, 'Z1+': 1.3, 'Z1-': -0.9},
        ('Clear', 30, '>a^2, <=4a^2'): {'Z3+': 2.0, 'Z3-': -1.4, 'Z2+': 2.0, 'Z2-': -1.4, 'Z1+': 1.3, 'Z1-': -0.9},
        ('Clear', 30, '>4a^2'): {'Z3+': 1.3, 'Z3-': -0.9, 'Z2+': 1.3, 'Z2-': -0.9, 'Z1+': 1.3, 'Z1-': -0.9},
        ('Clear', 45, '<=a^2'): {'Z3+': 2.2, 'Z3-': -1.6, 'Z2+': 1.7, 'Z2-': -1.2, 'Z1+': 1.1, 'Z1-': -0.8},
        ('Clear', 45, '>a^2, <=4a^2'): {'Z3+': 1.7, 'Z3-': -1.2, 'Z2+': 1.7, 'Z2-': -1.2, 'Z1+': 1.1, 'Z1-': -0.8},
        ('Clear', 45, '>4a^2'): {'Z3+': 1.1, 'Z3-': -0.8, 'Z2+': 1.1, 'Z2-': -0.8, 'Z1+': 1.1, 'Z1-': -0.8},
        ('Obstructed', 0, '<=a^2'): {'Z3+': 1.0, 'Z3-': -3.6, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 0, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 0, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 7.5, '<=a^2'): {'Z3+': 1.0, 'Z3-': -5.1, 'Z2+': 0.8, 'Z2-': -2.6, 'Z1+': 0.5, 'Z1-': -1.7},
        ('Obstructed', 7.5, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -2.6, 'Z2+': 0.8, 'Z2-': -2.6, 'Z1+': 0.5,
                                              'Z1-': -1.7},
        ('Obstructed', 7.5, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.7, 'Z2+': 0.5, 'Z2-': -1.7, 'Z1+': 0.5, 'Z1-': -1.7},
        ('Obstructed', 15, '<=a^2'): {'Z3+': 1.0, 'Z3-': -3.2, 'Z2+': 0.8, 'Z2-': -2.4, 'Z1+': 0.5, 'Z1-': -1.6},
        ('Obstructed', 15, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -2.4, 'Z2+': 0.8, 'Z2-': -2.4, 'Z1+': 0.5, 'Z1-': -1.6},
        ('Obstructed', 15, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.6, 'Z2+': 0.5, 'Z2-': -1.6, 'Z1+': 0.5, 'Z1-': -1.6},
        ('Obstructed', 30, '<=a^2'): {'Z3+': 1.0, 'Z3-': -2.4, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 30, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 30, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 45, '<=a^2'): {'Z3+': 1.0, 'Z3-': -2.4, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 45, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 45, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
    }
    pitched_cc_cn_df = pd.DataFrame.from_dict(pitched_cc_cn_data, orient='index')
    pitched_cc_cn_df.index = pd.MultiIndex.from_tuples(pitched_cc_cn_df.index,
                                                       names=['flow_condition', 'theta', 'area_condition'])
    databases['PITCHED_CC_CN_DF'] = pitched_cc_cn_df.sort_index()

    # =========================================================================
    # ==== START: 【新增】ASCE 7-16 FIGURE 30.7-3 Troughed Roof C&C, CN  ====
    # =========================================================================
    troughed_cc_cn_data = {
        # ('Flow Condition', Theta, 'Area Condition'): {'Zone3+': val, 'Zone3-': val, ...}
        ('Clear', 0, '<=a^2'): {'Z3+': 2.4, 'Z3-': -3.3, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 0, '>a^2, <=4a^2'): {'Z3+': 1.8, 'Z3-': -1.7, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 0, '>4a^2'): {'Z3+': 1.2, 'Z3-': -1.1, 'Z2+': 1.2, 'Z2-': -1.1, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 7.5, '<=a^2'): {'Z3+': 2.4, 'Z3-': -3.3, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 7.5, '>a^2, <=4a^2'): {'Z3+': 1.8, 'Z3-': -1.7, 'Z2+': 1.8, 'Z2-': -1.7, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 7.5, '>4a^2'): {'Z3+': 1.2, 'Z3-': -1.1, 'Z2+': 1.2, 'Z2-': -1.1, 'Z1+': 1.2, 'Z1-': -1.1},
        ('Clear', 15, '<=a^2'): {'Z3+': 2.2, 'Z3-': -2.2, 'Z2+': 1.7, 'Z2-': -1.7, 'Z1+': 1.1, 'Z1-': -1.1},
        ('Clear', 15, '>a^2, <=4a^2'): {'Z3+': 1.7, 'Z3-': -1.7, 'Z2+': 1.7, 'Z2-': -1.7, 'Z1+': 1.1, 'Z1-': -1.1},
        ('Clear', 15, '>4a^2'): {'Z3+': 1.1, 'Z3-': -1.1, 'Z2+': 1.1, 'Z2-': -1.1, 'Z1+': 1.1, 'Z1-': -1.1},
        ('Clear', 30, '<=a^2'): {'Z3+': 2.6, 'Z3-': -1.8, 'Z2+': 2.0, 'Z2-': -1.4, 'Z1+': 1.3, 'Z1-': -0.9},
        ('Clear', 30, '>a^2, <=4a^2'): {'Z3+': 2.0, 'Z3-': -1.4, 'Z2+': 2.0, 'Z2-': -1.4, 'Z1+': 1.3, 'Z1-': -0.9},
        ('Clear', 30, '>4a^2'): {'Z3+': 1.3, 'Z3-': -0.9, 'Z2+': 1.3, 'Z2-': -0.9, 'Z1+': 1.3, 'Z1-': -0.9},
        ('Clear', 45, '<=a^2'): {'Z3+': 1.6, 'Z3-': -2.2, 'Z2+': 1.2, 'Z2-': -1.7, 'Z1+': 0.8, 'Z1-': -1.1},
        ('Clear', 45, '>a^2, <=4a^2'): {'Z3+': 1.2, 'Z3-': -1.7, 'Z2+': 1.2, 'Z2-': -1.7, 'Z1+': 0.8, 'Z1-': -1.1},
        ('Clear', 45, '>4a^2'): {'Z3+': 0.8, 'Z3-': -1.1, 'Z2+': 0.8, 'Z2-': -1.1, 'Z1+': 0.8, 'Z1-': -1.1},
        ('Obstructed', 0, '<=a^2'): {'Z3+': 1.0, 'Z3-': -3.6, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 0, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 0, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 7.5, '<=a^2'): {'Z3+': 1.0, 'Z3-': -4.8, 'Z2+': 0.8, 'Z2-': -2.4, 'Z1+': 0.5, 'Z1-': -1.6},
        ('Obstructed', 7.5, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -2.4, 'Z2+': 0.8, 'Z2-': -2.4, 'Z1+': 0.5,
                                              'Z1-': -1.6},
        ('Obstructed', 7.5, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.6, 'Z2+': 0.5, 'Z2-': -1.6, 'Z1+': 0.5, 'Z1-': -1.6},
        ('Obstructed', 15, '<=a^2'): {'Z3+': 1.0, 'Z3-': -2.4, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 15, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 15, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 30, '<=a^2'): {'Z3+': 1.0, 'Z3-': -2.8, 'Z2+': 0.8, 'Z2-': -2.1, 'Z1+': 0.5, 'Z1-': -1.4},
        ('Obstructed', 30, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -2.1, 'Z2+': 0.8, 'Z2-': -2.1, 'Z1+': 0.5, 'Z1-': -1.4},
        ('Obstructed', 30, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.4, 'Z2+': 0.5, 'Z2-': -1.4, 'Z1+': 0.5, 'Z1-': -1.4},
        ('Obstructed', 45, '<=a^2'): {'Z3+': 1.0, 'Z3-': -2.4, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 45, '>a^2, <=4a^2'): {'Z3+': 0.8, 'Z3-': -1.8, 'Z2+': 0.8, 'Z2-': -1.8, 'Z1+': 0.5, 'Z1-': -1.2},
        ('Obstructed', 45, '>4a^2'): {'Z3+': 0.5, 'Z3-': -1.2, 'Z2+': 0.5, 'Z2-': -1.2, 'Z1+': 0.5, 'Z1-': -1.2},
    }
    troughed_cc_cn_df = pd.DataFrame.from_dict(troughed_cc_cn_data, orient='index')
    troughed_cc_cn_df.index = pd.MultiIndex.from_tuples(troughed_cc_cn_df.index,
                                                        names=['flow_condition', 'theta', 'area_condition'])
    databases['THROUGHED_CC_CN_DF'] = troughed_cc_cn_df.sort_index()

    # =================================================================
    # ==== START: 新增 ASCE 7-10 Figure 27.3-5 Pitched Free Roofs, CN ====
    # =================================================================
    pitched_roof_cn_data = {
        # 結構: (氣流條件, 係數類型): {(角度, 載重工況): 係數值, ...}
        ('clear', 'C_NW'): {(7.5, 'A'): 1.1, (7.5, 'B'): 0.2, (15, 'A'): 1.1, (15, 'B'): 0.1, (22.5, 'A'): 1.1,
                            (22.5, 'B'): -0.1, (30, 'A'): 1.3, (30, 'B'): -0.1, (37.5, 'A'): 1.3, (37.5, 'B'): -0.2,
                            (45, 'A'): 1.1, (45, 'B'): -0.3},
        ('clear', 'C_NL'): {(7.5, 'A'): -0.3, (7.5, 'B'): -1.2, (15, 'A'): -0.4, (15, 'B'): -1.1, (22.5, 'A'): 0.1,
                            (22.5, 'B'): -0.8, (30, 'A'): 0.3, (30, 'B'): -0.9, (37.5, 'A'): 0.6, (37.5, 'B'): -0.6,
                            (45, 'A'): 0.9, (45, 'B'): -0.5},
        ('obstructed', 'C_NW'): {(7.5, 'A'): -1.6, (7.5, 'B'): -0.9, (15, 'A'): -1.2, (15, 'B'): -0.6,
                                 (22.5, 'A'): -1.2, (22.5, 'B'): -0.8, (30, 'A'): -0.7, (30, 'B'): -0.2,
                                 (37.5, 'A'): -0.6, (37.5, 'B'): -0.3, (45, 'A'): -0.5, (45, 'B'): -0.3},
        ('obstructed', 'C_NL'): {(7.5, 'A'): -1.0, (7.5, 'B'): -1.7, (15, 'A'): -1.0, (15, 'B'): -1.6,
                                 (22.5, 'A'): -1.2, (22.5, 'B'): -1.7, (30, 'A'): -0.7, (30, 'B'): -1.1,
                                 (37.5, 'A'): -0.9, (37.5, 'B'): -0.6, (45, 'A'): -0.5, (45, 'B'): -0.7}
    }
    pitched_roof_cn_df = pd.DataFrame(pitched_roof_cn_data)
    pitched_roof_cn_df.index.names = ['theta', 'load_case']
    pitched_roof_cn_df.columns.names = ['flow_condition', 'coefficient_type']
    databases['PITCHED_ROOF_CN_DF'] = pitched_roof_cn_df

    # ==================================================================
    # ==== START: 新增 ASCE 7-10 Figure 27.3-6 Troughed Free Roofs, CN ====
    # ==================================================================
    troughed_roof_cn_data = {
        # 結構: (氣流條件, 係數類型): {(角度, 載重工況): 係數值, ...}
        ('clear', 'C_NW'): {(7.5, 'A'): -1.1, (7.5, 'B'): -0.2, (15, 'A'): -1.1, (15, 'B'): 0.1, (22.5, 'A'): -1.1,
                            (22.5, 'B'): -0.1, (30, 'A'): -1.3, (30, 'B'): -0.1, (37.5, 'A'): -1.3, (37.5, 'B'): 0.2,
                            (45, 'A'): -1.1, (45, 'B'): 0.3},
        ('clear', 'C_NL'): {(7.5, 'A'): 0.3, (7.5, 'B'): 1.2, (15, 'A'): 0.4, (15, 'B'): 1.1, (22.5, 'A'): -0.1,
                            (22.5, 'B'): 0.8, (30, 'A'): -0.3, (30, 'B'): 0.9, (37.5, 'A'): -0.6, (37.5, 'B'): 0.6,
                            (45, 'A'): -0.9, (45, 'B'): 0.5},
        ('obstructed', 'C_NW'): {(7.5, 'A'): -1.6, (7.5, 'B'): -0.9, (15, 'A'): -1.2, (15, 'B'): -0.6,
                                 (22.5, 'A'): -1.2, (22.5, 'B'): -0.8, (30, 'A'): -0.7, (30, 'B'): -0.2,
                                 (37.5, 'A'): -0.6, (37.5, 'B'): -0.3, (45, 'A'): -0.5, (45, 'B'): -0.3},
        ('obstructed', 'C_NL'): {(7.5, 'A'): -0.5, (7.5, 'B'): -0.8, (15, 'A'): -0.5, (15, 'B'): -0.8,
                                 (22.5, 'A'): -0.6, (22.5, 'B'): -0.8, (30, 'A'): -0.4, (30, 'B'): -0.5,
                                 (37.5, 'A'): -0.3, (37.5, 'B'): -0.4, (45, 'A'): -0.5, (45, 'B'): -0.4}
    }
    troughed_roof_cn_df = pd.DataFrame(troughed_roof_cn_data)
    troughed_roof_cn_df.index.names = ['theta', 'load_case']
    troughed_roof_cn_df.columns.names = ['flow_condition', 'coefficient_type']
    databases['THROUGHED_ROOF_CN_DF'] = troughed_roof_cn_df

    # ==================================================================
    # ==== START: 新增 ASCE 7-10 Fig 27.4-7 Free Roofs, Parallel Wind ====
    # ==================================================================
    parallel_wind_cn_data = {
        # 索引: (距離條件, 載重工況)
        ('<h', 'A'): {'clear': -0.8, 'obstructed': -1.2},
        ('<h', 'B'): {'clear': 0.8, 'obstructed': 0.5},
        ('>h, <2h', 'A'): {'clear': -0.6, 'obstructed': -0.9},
        ('>h, <2h', 'B'): {'clear': 0.5, 'obstructed': 0.5},
        ('>2h', 'A'): {'clear': -0.3, 'obstructed': -0.6},
        ('>2h', 'B'): {'clear': 0.3, 'obstructed': 0.3},
    }
    parallel_wind_cn_df = pd.DataFrame.from_dict(parallel_wind_cn_data, orient='index')
    parallel_wind_cn_df.columns.name = 'flow_condition'
    parallel_wind_cn_df.index = pd.MultiIndex.from_tuples(parallel_wind_cn_df.index,
                                                          names=['distance_condition', 'load_case'])
    databases['FREE_ROOF_PARALLEL_WIND_CN_DF'] = parallel_wind_cn_df
    # =================================================================

    return databases


# ==============================================================================
# Phase 2: 核心計算函式
# ==============================================================================
def calculate_unified_h(params: dict) -> float:
    """根據建築類型，統一計算平均屋頂高度 h。"""
    building_type = params.get('enclosure_status')
    geo_data = params.get('geometry_data', {})

    if building_type in ['shed-roof', 'pitched-free-roof', 'troughed-free-roof']:
        roof_params = geo_data.get('roof', {})
        h_ridge = float(roof_params.get('h_ridge', 0))
        h_eave = float(roof_params.get('h_eave', 0))
        theta = float(roof_params.get('theta', 0))
        return h_eave if theta < 10 else (h_ridge + h_eave) / 2

    elif building_type == 'chimney':
        return float(geo_data.get('h', 0))

    elif building_type == 'street-light':
        main_pole_data = geo_data.get('main_pole', {})
        return float(main_pole_data.get('h_m', 0))

    elif building_type == 'water-tower':
        body_data = geo_data.get('body', {})
        top_height = float(body_data.get('h', 0))
        clearance = float(body_data.get('C', 0))
        return top_height + clearance

    elif building_type == 'hollow-sign':
        sign_params = geo_data.get('sign', {})
        b_v = float(sign_params.get('b_v', 0))
        d = float(sign_params.get('d', 0))
        return d + (b_v / 2)

    elif building_type == 'solid-sign' or building_type == 'truss-tower':
        geo_data = params.get('geometry_data', {})
        if building_type == 'solid-sign':
            sign_params = geo_data.get('sign', {})
            b_v = float(sign_params.get('b_v', 0))
            d = float(sign_params.get('d', 0))
            return d + b_v
        elif building_type == 'truss-tower':
            manual_inputs = geo_data.get('manual_inputs', [])
            if not manual_inputs: return 0.0
            return max(item.get('height', 0) for item in manual_inputs)

    return 0.0


def interpolate_from_table(df: pd.DataFrame, target_index: float, column_name) -> float:
    return np.interp(target_index, df.index, df[column_name])


def calculate_topography_factor(topo_params: dict, z: float, db: dict) -> tuple:
    H, Lh, x, terrain, landform = topo_params['H'], topo_params['Lh'], topo_params['x'], topo_params['terrain'], \
        topo_params['landform']
    h_over_lh = H / Lh

    lookup_h_over_lh = min(h_over_lh, 0.5)
    effective_Lh = 2 * H if h_over_lh > 0.5 else Lh

    terrain_group = 'A_or_B' if terrain in ['A', 'B'] else 'C'
    k1_col = (terrain_group, landform)
    k2_col = '山脊或山丘' if landform in ['山脊', '山丘'] else '懸崖'

    K1 = interpolate_from_table(db['K1_DF'], lookup_h_over_lh, k1_col)
    K2 = interpolate_from_table(db['K2_DF'], x / effective_Lh, k2_col)
    K3 = interpolate_from_table(db['K3_DF'], z / effective_Lh, landform)

    Kzt = (1 + K1 * K2 * K3) ** 2
    return Kzt, K1, K2, K3


def calculate_velocity_pressure_coeff(z: float, terrain: str, db: dict) -> float:
    params = db['TERRAIN_DF'].loc[terrain]
    zg, alpha = params['zg'], params['alpha']
    if z <= 5: z = 5
    return 2.774 * ((z / zg) ** (2 * alpha))


def calculate_velocity_pressure(z: float, I: float, V10_C: float, terrain: str, K_zt: float, db: dict) -> float:
    K_z = calculate_velocity_pressure_coeff(z, terrain, db)
    return 0.06 * K_z * K_zt * (I * V10_C) ** 2


# Wind_TW/wind_calculations.py (替換後)

def calculate_hollow_sign_force(params: dict, db: dict) -> dict:
    """
    根據簡化後的參數計算中空標示物的總風力 F。
    此函式整合了自動分層和用戶手動輸入兩種計算 q(z) 的邏輯。
    """
    try:
        print("\n--- 開始計算中空標示物總風力 F ---")
        geo_data = params.get('geometry_data', {}).get('sign', {})
        general_params = params
        df_cf = db['HOLLOW_SIGN_CF_DF']

        # 獲取參數
        b_h = float(geo_data.get('b_h', 0))
        b_v = float(geo_data.get('b_v', 0))
        d = float(geo_data.get('d', 0))  # 支撐高度
        opening_ratio_percent = float(geo_data.get('opening_ratio', 0))
        qz_mode = geo_data.get('qz_mode', 'auto')
        layer_height = float(geo_data.get('layer_height', 2.0))

        solidity_ratio = 1.0 - (opening_ratio_percent / 100.0)

        # 確定 Cf 值 (邏輯不變)
        lookup_key = ('平邊構材', 'N/A')
        phi_column = ''
        if solidity_ratio < 0.1:
            phi_column = '<0.1'
        elif 0.1 <= solidity_ratio <= 0.29:
            phi_column = '0.1-0.29'
        else:
            phi_column = '0.3-0.7'
        cf_value = df_cf.loc[lookup_key, phi_column]
        print(f"  - 輸入參數: 實體率 φ={solidity_ratio:.3f}")
        print(f"  - ==> 查表得風力係數 Cf = {cf_value:.4f}")

        # 根據 q(z) 計算模式，計算總風力 F
        total_force = 0.0
        calculation_details = []
        qz_mode = geo_data.get('qz_mode', 'auto')

        # ==== START: 新增 Manual Mode 處理邏輯 ====
        if qz_mode == 'manual':
            manual_inputs = geo_data.get('manual_inputs', [])
            print(f"  - 採用用戶輸入模式:")
            if not manual_inputs:
                print("    - 警告: 未提供任何有效的構材輸入。")
            for item in manual_inputs:
                name, z_eff, area = item.get('name'), item.get('height'), item.get('area')
                q_z = calculate_velocity_pressure(z_eff, general_params['I'], general_params['V10_C'],
                                                  general_params['terrain'], 1.0, db)
                force = q_z * area * cf_value
                total_force += force
                calculation_details.append({
                    'layer': name,
                    'z_range': f"在 {z_eff:.2f}",
                    'z_eff': z_eff, 'q_z': q_z, 'area': area, 'force': force
                })
                print(f"    - 構材 '{name}': q({z_eff:.2f}m)={q_z:.2f}, 風力={force:.2f} kgf")
        # ==== END: 新增邏輯 ====

        else:  # 'auto' 模式
            b_h = float(geo_data.get('b_h', 0))
            b_v = float(geo_data.get('b_v', 0))
            d = float(geo_data.get('d', 0))
            layer_height = float(geo_data.get('layer_height', 2.0))

            print(f"  - 採用自動分層模式 (每層 {layer_height:.2f} m):")
            z_bottom, z_top = d, d + b_v
            cut_points = np.unique(np.append(np.arange(z_bottom, z_top, layer_height), z_top))

            for i in range(len(cut_points) - 1):
                z1, z2 = cut_points[i], cut_points[i + 1]
                z_mid = (z1 + z2) / 2
                layer_area = b_h * (z2 - z1)  # 自動模式下面積是分層面積

                q_z_mid = calculate_velocity_pressure(z_mid, general_params['I'], general_params['V10_C'],
                                                      general_params['terrain'], 1.0, db)
                layer_force = q_z_mid * layer_area * cf_value
                total_force += layer_force

                calculation_details.append({
                    'layer': f'分層 {i + 1}', 'z_range': f"{z1:.2f} - {z2:.2f}",
                    'z_eff': z_mid, 'q_z': q_z_mid, 'area': layer_area, 'force': layer_force
                })
                print(
                    f"    - 分層 {i + 1} (z={z1:.2f}-{z2:.2f}m): q({z_mid:.2f}m)={q_z_mid:.2f}, 層風力={layer_force:.2f} kgf")

        print(f"  - ==> 加總後總風力 F = {total_force:.2f} kgf")
        print("--- 中空標示物總風力 F 計算結束 ---\n")
        return {
            'total_force': total_force,
            'cf_value': cf_value,
            'solidity_ratio': solidity_ratio,
            'details': calculation_details,
            # ==== START: 新增回傳值 ====
            'support_height': d  # 將支撐高度 d 回傳給上層函式
            # ==== END: 新增回傳值 ====
        }

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_truss_tower_force(params: dict, db: dict) -> dict:
    try:
        print("\n--- 開始計算桁架高塔單一工況風力 ---")
        geo_data = params.get('geometry_data', {})
        general_params = params
        wind_dir = params.get('wind_direction', 'X')  # 獲取當前計算的風向

        # 1. 獲取 Cf 計算參數 (邏輯不變)
        shape = geo_data.get('shape')
        e = float(geo_data.get('solidity_ratio', 0))
        member_shape = geo_data.get('member_shape')
        print(f"  - 輸入參數: 形式={shape}, 實體率 ε={e:.3f}, 構件={member_shape}")

        cf_base = 4.0 * e ** 2 - 5.9 * e + 4.0 if shape == 'square' else 3.4 * e ** 2 - 4.7 * e + 3.4

        correction_rounded = 1.0
        if member_shape == 'rounded':
            correction_rounded = min(0.51 * e ** 2 + 0.57, 1.0)

        correction_diagonal = 1.0
        if shape == 'square':
            correction_diagonal = min(1 + 0.75 * e, 1.2)
            print(f"  - 方形塔: 強制採用對角線風修正係數 = {correction_diagonal:.3f}")

        cf_normal = cf_base * correction_rounded
        cf_final_diagonal = cf_normal * correction_diagonal
        print(f"  - ==> 基礎Cf={cf_normal:.3f}, 設計Cf={cf_final_diagonal:.3f}")

        # 2. 【新增】: 計算陣風反應因子 G，現在考慮特定風向
        manual_inputs = geo_data.get('manual_inputs', [])
        # ==== ▼▼▼ START: 【核心修正】根據風向選擇輸入數據 ▼▼▼ ====
        if wind_dir == 'X':
            manual_inputs = geo_data.get('manual_inputs_x', [])
            print("  - 使用 X 向風作用面幾何數據")
        else:  # wind_dir == 'Y'
            manual_inputs = geo_data.get('manual_inputs_y', [])
            print("  - 使用 Y 向風作用面幾何數據")
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

        if not manual_inputs:
            return {'status': 'error', 'message': '未提供任何有效的分段輸入。'}

        # ==== ▼▼▼ START: 【核心修正】▼▼▼ ====
        # h_tower 应该基于所有分段的最高点来决定
        h_tower = max(item.get('height', 0) for item in manual_inputs) if manual_inputs else 0
        if h_tower <= 0:
            return {'total_force_diagonal': 0, 'details': [], 'g_factor_details': None}
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====
        assumed_width = max(h_tower / 10, 2.0)

        # 根據傳入的 wind_direction 選擇對應的 fn
        wind_dir = params.get('wind_direction', 'X')
        fn_for_g = general_params.get('fnX') if wind_dir == 'X' else general_params.get('fnY')

        params_for_g = {
            'h': h_tower, 'B': assumed_width, 'L': assumed_width, 'terrain': general_params['terrain'],
            'fn': fn_for_g, 'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        common_gust_params = calculate_gust_common_params(params_for_g, db)
        rigidity = '柔性' if params_for_g['fn'] < 1.0 else '普通'

        # ==== ▼▼▼ START: 【核心修正】▼▼▼ ====
        gust_factor_details = calculate_Gf_factor(params_for_g, common_gust_params,
                                                  db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                                    common_gust_params)
        gust_factor = gust_factor_details['final_value']  # 從字典中提取數值
        print(f"  - ==> 陣風反應因子 G = {gust_factor:.3f} ({rigidity}建築)")
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

        # 3. 根據分段數據計算總風力，現在考慮地形 Kzt
        total_force_normal = 0.0
        total_force_diagonal = 0.0
        calculation_details = []
        is_topo = params.get('is_topo_site', False)
        topo_params = params.get('topo_params', {})

        for item in manual_inputs:
            name, z_eff, area_af = item.get('name'), item.get('height'), item.get('area')

            k_z = calculate_velocity_pressure_coeff(z_eff, general_params['terrain'], db)
            kzt = calculate_topography_factor(topo_params, z_eff, db)[0] if is_topo else 1.0

            q_z = calculate_velocity_pressure(z_eff, general_params['I'], general_params['V10_C'],
                                              general_params['terrain'], kzt, db)

            design_pressure = q_z * gust_factor * cf_final_diagonal
            force_normal = q_z * gust_factor * cf_normal * area_af
            force_diagonal = force_normal * correction_diagonal

            total_force_normal += force_normal
            total_force_diagonal += force_diagonal

            calculation_details.append({
                'name': name, 'z_eff': z_eff, 'area': area_af, 'K_z': k_z,
                'Kzt': kzt, 'q_z': q_z, 'design_pressure': design_pressure,
                'force_normal': force_normal, 'force_diagonal': force_diagonal,
            })

        print(f"  - ==> 總風力 F(垂直)={total_force_normal:.2f} kgf, F(對角線)={total_force_diagonal:.2f} kgf")
        return {
            'cf_normal': cf_normal,
            'cf_diagonal': cf_final_diagonal,
            'correction_factor': correction_diagonal,
            'gust_factor': gust_factor,
            'g_factor_details': gust_factor_details,  # 確保返回這個字典
            'total_force_normal': total_force_normal,
            'total_force_diagonal': total_force_diagonal, 'details': calculation_details
        }
    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_water_tower_force(params: dict, db: dict) -> dict:
    """
    計算水塔的總風力。
    【核心修正】: 新增對桁架計算結果的成功校驗，確保回傳的是有效數據。
    """
    try:
        print("\n--- 開始計算水塔總風力 F ---")
        geo_data = params.get('geometry_data', {})
        results = {}

        is_topo = params.get('is_topo_site', False)
        topo_params = params.get('topo_params', {})

        # 1. 處理水塔本體 (Body)
        body_data = geo_data.get('body', {})
        if not body_data:
            print("  - 錯誤: 找不到水塔本體的幾何資料。")
            return None

        body_H = float(body_data.get('h', 0))
        if body_H <= 0:
            print("  - 警告: 水塔本體高度為 0 或負數，跳過本體計算。")
            results['body_results'] = None
        else:
            base_height_of_body = float(body_data.get('C', 0))
            layer_height = float(body_data.get('layer_height', 2.0))
            shape_en = body_data.get('shape')
            roughness_en = body_data.get('roughness')

            if shape_en == 'circular':
                d_top = float(body_data.get('D_top', 0))
                d_bot = float(body_data.get('D_bot', 0))
                body_avg_d = (d_top + d_bot) / 2
            else:
                body_avg_d = float(body_data.get('D', 0))

            general_params_for_calc = {
                'I': params['I'], 'V10_C': params['V10_C'], 'terrain': params['terrain']
            }
            body_cf = calculate_chimney_cf(
                h=body_H, D=body_avg_d, shape_en=shape_en, roughness_en=roughness_en,
                general_params=general_params_for_calc, db=db
            )
            total_body_force = 0.0
            body_calculation_details = []
            z_bottom = base_height_of_body
            z_top = base_height_of_body + body_H
            cut_points = np.unique(np.append(np.arange(z_bottom, z_top, layer_height), z_top))

            for i in range(len(cut_points) - 1):
                z1, z2 = cut_points[i], cut_points[i + 1]
                h_layer = z2 - z1
                if h_layer < 1e-6: continue

                d_top_val = float(body_data.get('D_top', 0))
                d_bot_val = float(body_data.get('D_bot', 0))
                if shape_en == 'circular' and d_top_val != d_bot_val and body_H > 0:
                    d1 = np.interp(z1, [z_bottom, z_top], [d_bot_val, d_top_val])
                    d2 = np.interp(z2, [z_bottom, z_top], [d_bot_val, d_top_val])
                    layer_avg_d = (d1 + d2) / 2
                else:
                    layer_avg_d = body_avg_d
                    d1 = d2 = layer_avg_d

                layer_area = layer_avg_d * h_layer
                zc = (h_layer / 3) * (d1 + 2 * d2) / (d1 + d2) if (d1 + d2) > 0 else h_layer / 2
                z_eff = z1 + zc
                kzt_z_eff = calculate_topography_factor(topo_params, z_eff, db)[0] if is_topo else 1.0
                q_z_eff = calculate_velocity_pressure(z_eff, params['I'], params['V10_C'], params['terrain'], kzt_z_eff,
                                                      db)
                layer_force = q_z_eff * body_cf * layer_area if body_cf is not None else 0
                total_body_force += layer_force
                body_calculation_details.append({
                    'z_range': f"{z1:.2f}-{z2:.2f}", 'z_eff': z_eff, 'q_z': q_z_eff,
                    'cf': body_cf, 'area': layer_area, 'force': layer_force
                })

            results['body_results'] = {
                'cf': body_cf, 'total_force': total_body_force, 'details': body_calculation_details
            }

        # 2. 處理支撐結構
        support_info = geo_data.get('support', {})

        support_type = support_info.get('type')
        if support_type == 'truss':
            params_for_support_calc = params.copy()
            params_for_support_calc['geometry_data'] = support_info.get('truss_params', {})
            params_for_support_calc['is_topo_site'] = is_topo
            params_for_support_calc['topo_params'] = topo_params

            support_results = calculate_truss_tower_force(params_for_support_calc, db)

            # 【核心修正】: 檢查桁架計算是否成功，如果不成功則不回傳 support_results
            if support_results and 'total_force_diagonal' in support_results:
                results['support_results'] = support_results
            else:
                print("  - 警告: 水塔的桁架支撐結構計算失敗或未返回有效結果。")
                results['support_results'] = None

        return results
    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_gust_common_params(params: dict, db: dict) -> dict:
    """計算 G 和 Gf 所需的通用參數"""
    common = {}
    h = params['h']
    B = params['B']  # 假設已從使用者輸入取得
    terrain = params['terrain']

    terrain_props = db['TERRAIN_DF'].loc[terrain]
    z_min = terrain_props['z_min']

    # 1. 等效高度 z_bar (z-bar)
    # 規範 2.7 節說明 z 為等效結構高度，其值為 0.6h，但不可小於 z_min [14]
    z_bar = max(0.6 * h, z_min)
    common['z_bar'] = z_bar

    # 2. 在 z_bar 高度處的紊流強度 I_z
    # 依據規範式 (2.10) [14]
    c = terrain_props['c']
    I_z = c * (10 / z_bar) ** (1 / 6)
    common['I_z'] = I_z

    # 3. 在 z_bar 高度處的紊流積分尺度 L_z
    # 依據規範式 (2.12) [14]
    l_lambda_val = terrain_props['l_lambda']  # 'lambda' 是 Python 關鍵字，故換個名字
    epsilon_bar = terrain_props['epsilon_bar']
    L_z = l_lambda_val * (z_bar / 10) ** (epsilon_bar)
    common['L_z'] = L_z

    # 4. 背景反應因子 Q
    # 依據規範式 (2.11) [14]
    Q_val = np.sqrt(1 / (1 + 0.63 * ((B + h) / L_z) ** 0.63))
    common['Q'] = Q_val
    return common


def calculate_mean_wind_speed_at_height(z: float, params: dict, db: dict) -> float:
    """計算在 z 高度的每小時平均風速 V_z"""
    # 依據規範式 (2.19) [15]
    terrain = params['terrain']
    V10_C = params['V10_C']

    terrain_props = db['TERRAIN_DF'].loc[terrain]
    b = terrain_props['b']
    alpha = terrain_props['alpha']

    # 注意：規範此處 Vz 是每小時平均風速，V10(C) 是10分鐘平均風速。
    # 此處的 b 因子已將其轉換。
    V_z = b * ((z / 10) ** alpha) * V10_C
    print(f"b={b}, z={z}, alpha={alpha}, V_z={V_z}")
    return V_z


def calculate_wind_speed_at_h(z: float, params: dict, db: dict) -> float:
    """計算在 z 高度的每小時平均風速 V_z"""
    # 依據規範式 (2.19) [15]
    terrain = params['terrain']
    V10_C = params['V10_C']

    terrain_props = db['TERRAIN_DF'].loc[terrain]
    alpha = terrain_props['alpha']
    zg = terrain_props['zg']

    # 注意：規範此處 Vz 是每小時平均風速，V10(C) 是10分鐘平均風速。
    # 此處的 b 因子已將其轉換。
    V_z = 1.666 * ((z / zg) ** alpha) * V10_C
    print(f"zg={zg}, z={z}, alpha={alpha}, V_z={V_z}")
    return V_z


def calculate_G_factor(params: dict, common_gust_params: dict) -> float:
    gQ = 3.4
    gv = 3.4
    z_bar = common_gust_params['z_bar']
    L_z = common_gust_params['L_z']
    I_z = common_gust_params['I_z']
    Q = common_gust_params['Q']
    G = 1.927 * (1 + 1.7 * gQ * I_z * Q) / (1 + 1.7 * gv * I_z)

    return {'final_value': G, 'type': 'G', 'gQ': gQ, 'gv': gv, 'z_bar': z_bar, 'I_z': I_z, 'Q': Q, 'L_z': L_z}


def calculate_Gf_factor(params: dict, common_gust_params: dict, db: dict) -> float:
    """計算柔性建築物之陣風反應因子 Gf"""
    # 依據規範式 (2.13) [14]
    gQ = 3.4
    gv = 3.4
    fn = params.get('fn', 1.0)  # 加上預設值
    beta = params.get('beta', 0.02)
    h = params['h']
    B = params['B']
    L = params['L']
    I_z = common_gust_params['I_z']
    Q = common_gust_params['Q']
    L_z = common_gust_params['L_z']
    z_bar = common_gust_params['z_bar']
    if fn <= 0: return 1.88  # 避免 log(0)
    ln_3600fn = np.log(3600 * fn)
    gR = np.sqrt(2 * ln_3600fn) + (0.577 / np.sqrt(2 * ln_3600fn))
    V_z_bar = calculate_mean_wind_speed_at_height(z_bar, params, db)
    N1 = fn * L_z / V_z_bar if V_z_bar > 0 else 0
    Rn = (7.47 * N1) / ((1 + 10.3 * N1) ** (5 / 3))
    eta_h = 4.6 * fn * h / V_z_bar if V_z_bar > 0 else 0
    eta_B = 4.6 * fn * B / V_z_bar if V_z_bar > 0 else 0
    eta_L = 15.4 * fn * L / V_z_bar if V_z_bar > 0 else 0

    def get_Rj(eta):
        if eta < 1e-6: return 1.0
        return (1 / eta) - (1 / (2 * eta ** 2)) * (1 - np.exp(-2 * eta))

    Rh = get_Rj(eta_h)
    RB = get_Rj(eta_B)
    RL = get_Rj(eta_L)
    R_squared = (1 / beta) * Rn * Rh * RB * (0.53 + 0.47 * RL)
    R = np.sqrt(R_squared) if R_squared >= 0 else 0
    numerator = 1 + 1.7 * I_z * np.sqrt((gQ * Q) ** 2 + (gR * R) ** 2)
    denominator = 1 + 1.7 * gv * I_z
    Gf = 1.927 * (numerator / denominator)

    return {
        'final_value': Gf, 'type': 'Gf', 'gQ': gQ, 'gv': gv, 'gR': gR, 'I_z': I_z, 'Q': Q, 'R': R, 'z_bar': z_bar,
        'eta_h': eta_h, 'eta_B': eta_B, 'eta_L': eta_L,
        'V_z_bar': V_z_bar, 'N1': N1, 'Rn': Rn, 'Rh': Rh, 'RB': RB, 'RL': RL, 'beta': beta, 'L_z': L_z
    }


def calculate_transverse_wind_force(dir_params: dict, db: dict):
    """
    計算橫風向風力 W_Lz。
    根據規範 2.10 節，分為式 (2.21) 和 (2.22) 兩種情況。
    """
    h = dir_params.get('h', 0)
    L = dir_params.get('L', 0)
    B = dir_params.get('B', 0)

    # 檢查是否為矩形柱體，如果不是則不計算橫風
    # 這裡簡化為檢查屋頂類型，未來可擴充
    if dir_params.get('roof_type') not in ['flat', 'gable', 'shed', 'hip', 'arched', 'sawtooth_uniform',
                                           'sawtooth_irregular'] or B <= 0 or L <= 0:
        return None

    aspect_ratio = h / np.sqrt(B * L)
    condition_text = f"h/√BL = {aspect_ratio:.2f}"

    # 情況 1: 矮胖型建築 (規範 2.10 節，h/sqrt(BL) < 3)
    if aspect_ratio < 3:
        method_display = f"因 {condition_text} < 3，依據規範公式 (2.21) 計算"
        return {"method": "simplified_2_21", "factor": 0.87 * L / B, "method_display": method_display}

    # 情況 2: 細長型建築 (規範 2.10 節，3 <= h/sqrt(BL) <= 6)
    elif 3 <= aspect_ratio <= 6:
        fa = dir_params.get('fa')
        if not (0.2 <= L / B <= 5) or not fa or fa <= 0: return None

        Vh = calculate_wind_speed_at_h(h, dir_params, db)
        reduced_velocity = Vh / (fa * np.sqrt(B * L))

        if reduced_velocity > 10: return None

        method_display = f"因 3 ≤ {condition_text} ≤ 6，依據規範公式 (2.22) 計算"
        gL = np.sqrt(2 * np.log(3600 * fa)) + (0.577 / np.sqrt(2 * np.log(3600 * fa)))
        lb_ratio = L / B
        CL = 0.0082 * (lb_ratio ** 3) - 0.071 * (lb_ratio ** 2) + 0.22 * lb_ratio
        n1 = 0.12 / (1 + 0.38 * lb_ratio ** 2) ** 0.89
        n2 = 0.56 / (lb_ratio ** 0.85)
        k1, k2 = 0.85, 0.02
        beta1 = (0.12) / lb_ratio + (lb_ratio ** 4 + 2.3 * lb_ratio ** 2) / (
                2.4 * (lb_ratio ** 4) - 9.2 * (lb_ratio ** 3) + 18 * (lb_ratio ** 2) + 9.5 * lb_ratio - 0.15)
        beta2 = 0.28 * (lb_ratio ** -0.34)
        n_star = fa * B / Vh
        term1_num = 4 * k1 * (1 + 0.6 * beta1) * beta1 * (n_star / n1) ** 2
        term1_den = np.pi * ((1 - (n_star / n1) ** 2) ** 2 + 4 * (beta1 ** 2) * (n_star / n1) ** 2)
        term1 = term1_num / term1_den if term1_den > 1e-9 else 0
        term2_num = 4 * k2 * (1 + 0.6 * beta2) * beta2 * (n_star / n2) ** 2
        term2_den = np.pi * ((1 - (n_star / n2) ** 2) ** 2 + 4 * (beta2 ** 2) * (n_star / n2) ** 2)
        term2 = term2_num / term2_den if term2_den > 1e-9 else 0
        SL_n_star = term1 if lb_ratio < 3 else term1 + term2
        RLR = (np.pi * SL_n_star) / 4
        beta_damping = dir_params.get('beta', 0.02)
        calculation_factor = 3 * CL * gL * np.sqrt(1 + RLR / beta_damping)

        return {"method": "spectral_2_22", "calculation_factor": calculation_factor, "method_display": method_display,
                "CL": CL, "gL": gL, "RLR": RLR}
    else:
        return None


def calculate_torsional_moment(dir_params: dict, db: dict):
    """
    計算扭矩 MTz，並回傳詳細的計算依據和結果。
    """
    h = dir_params.get('h', 0)
    L = dir_params.get('L', 0)
    B = dir_params.get('B', 0)

    if dir_params.get('roof_type') not in ['flat', 'gable', 'shed', 'hip', 'arched', 'sawtooth_uniform',
                                           'sawtooth_irregular'] or B <= 0 or L <= 0:
        return None

    aspect_ratio = h / np.sqrt(B * L)
    condition_text = f"h/√BL = {aspect_ratio:.2f}"

    # 情況 1: 矮胖型建築 (規範 2.11 節，h/sqrt(BL) < 3)
    if aspect_ratio < 3:
        method_display = f"因 {condition_text} < 3，依據規範公式 (2.23) 計算"
        return {"method": "simplified_2_23", "factor": 0.28 * B, "method_display": method_display}

    # 情況 2: 細長型建築 (規範 2.11 節，3 <= h/sqrt(BL) <= 6)
    elif 3 <= aspect_ratio <= 6:
        lb_ratio = L / B
        ft = dir_params.get('ft')
        if not (0.2 <= lb_ratio <= 5) or not ft or ft <= 0: return None

        Vh = calculate_wind_speed_at_h(h, dir_params, db)
        reduced_velocity = Vh / (ft * np.sqrt(B * L))

        if reduced_velocity > 10: return None

        method_display = f"因 3 ≤ {condition_text} ≤ 6，依據規範公式 (2.24) 計算"
        gT = np.sqrt(2 * np.log(3600 * ft)) + (0.577 / np.sqrt(2 * np.log(3600 * ft)))
        CT = (0.0066 + 0.015 * lb_ratio ** 2) ** 0.78
        U_star = reduced_velocity

        def KT(lb, U):
            if U <= 4.5:
                return (-1.1 * lb + 0.97) / (lb ** 2 + 0.85 * lb + 3.3) + 0.17
            elif U >= 6.0:
                return (0.077 * lb - 0.16) / (lb ** 2 - 0.96 * lb + 0.42) + 0.35 / lb + 0.095
            return np.interp(U, [4.5, 6.0], [KT(lb, 4.5), KT(lb, 6.0)])

        def betaT(lb, U):
            if U <= 4.5:
                return (lb + 3.6) / (lb ** 2 - 5.1 * lb + 9.1) + 0.14 / lb + 0.14
            elif U >= 6.0:
                return (0.44 * lb ** 2 - 0.0064) / (lb ** 4 - 0.26 * lb ** 2 + 0.1) + 0.2
            return np.interp(U, [4.5, 6.0], [betaT(lb, 4.5), betaT(lb, 6.0)])

        def RTR_calc(kt, bt, us, l, b):
            lbl = max(l, b)
            return 0.036 * (kt ** 2) * (us ** (2 * bt)) * ((l * (b ** 2 + l ** 2) ** 2) / (lbl ** 2 * b ** 3))

        RTR = RTR_calc(KT(lb_ratio, U_star), betaT(lb_ratio, U_star), U_star, L, B)
        beta_damping = dir_params.get('beta', 0.02)
        calculation_factor = 1.8 * CT * B * gT * np.sqrt(1 + RTR / beta_damping)

        return {"method": "spectral_2_24", "calculation_factor": calculation_factor, "method_display": method_display,
                "CT": CT, "gT": gT, "RTR": RTR}
    else:
        return None


def calculate_wall_coeffs(L, B, db) -> dict:
    """計算牆面風壓係數 Cp, 依據 表 2.4"""
    coeffs = {}
    coeffs['windward'] = 0.8
    coeffs['side'] = -0.7
    leeward_df = db['LEEWARD_WALL_DF']
    coeffs['leeward'] = np.interp(L / B if B > 0 else 0, leeward_df.index, leeward_df['Cp'])
    return coeffs


def interpolate_cp_value(df: pd.DataFrame, theta: float, h_over_l: float) -> float:
    """
    輔助函式: 對給定的Cp表格進行內插，得到單一Cp值
    """
    # 步驟 1: 沿著角度(theta)軸，取得一個 Cp 值欄位
    thetas = df.columns.values

    # 如果 theta >= 60 度，Cp = 0.01 * theta
    if theta >= 60:
        target_cp_column = pd.Series([0.01 * theta] * len(df.index), index=df.index)

    # 如果 theta 正好落在表格的欄位上
    elif theta in thetas:
        target_cp_column = df[theta]

    # 剩下的情況，才需要對角度(theta)進行內插
    else:
        theta_clamped = np.clip(theta, thetas.min(), thetas.max())
        idx = np.searchsorted(thetas, theta_clamped)
        # 確保 idx 不會超出邊界
        if idx == 0: idx = 1
        if idx >= len(thetas): idx = len(thetas) - 1

        theta1, theta2 = thetas[idx - 1], thetas[idx]
        col1, col2 = df[theta1], df[theta2]

        # 避免除以零
        if theta1 == theta2:
            target_cp_column = col1
        else:
            ratio = (theta_clamped - theta1) / (theta2 - theta1)
            target_cp_column = col1 + (col2 - col1) * ratio

    # 步驟 2: 沿著 h/L 軸，對目標欄進行內插
    h_clamped = np.clip(h_over_l, df.index.min(), df.index.max())
    final_cp = np.interp(h_clamped, target_cp_column.index, target_cp_column.values)

    return final_cp


def calculate_roof_coeffs(params: dict, db: dict, wind_direction: str, sign: str = 'positive',
                          filter_by_sign: bool = False):
    roof_type = params.get('roof_type')
    print("屋頂形式", roof_type)
    h = params.get('h', 0)
    results = {}

    if wind_direction == 'X':
        L, B = params.get('B_X', 0), params.get('B_Y', 0)
    else:
        L, B = params.get('B_Y', 0), params.get('B_X', 0)

    # =================================================================
    # Case 1: 平屋頂 (表 2.5, theta=0)
    # =================================================================
    if roof_type == "flat":
        results['Cp_flat'] = -0.7
        return results

    # =================================================================
    # Case 2: 雙邊單斜式(山形)屋頂 / 單斜式屋頂
    # =================================================================
    if roof_type == "gable":
        theta = params['theta']
        ridge_orientation = params.get('ridge_orientation', 'X')
        is_parallel = (wind_direction == ridge_orientation)

        # 情況 2a: 風向平行於屋脊
        if is_parallel:
            print("  (判斷: 風向平行於屋脊)")
            cp_val = -0.8 if (h / L > 2.5 or h / B > 2.5) else -0.7
            results['Cp_parallel'] = cp_val

        # 情況 2b: 風向垂直於屋脊
        else:
            print("  (判斷: 風向垂直於屋脊)")
            h_over_l = h / L
            NEEDS_BOTH_CASES = (10 <= theta <= 15 and h_over_l <= 0.3)

            df_neg = db['ROOF_CP_DF_NEG']
            cp_neg_case = interpolate_cp_value(df_neg, theta, h_over_l)

            if NEEDS_BOTH_CASES:
                df_pos = db['ROOF_CP_DF_POS']
                cp_pos_case = interpolate_cp_value(df_pos, theta, h_over_l)
                results['windward_Cp_case1 (正值)'] = cp_pos_case
                results['windward_Cp_case2 (負值)'] = cp_neg_case
            else:
                results['windward_Cp'] = cp_neg_case

            results['leeward_Cp'] = -0.7

        return results

    # ==== ▼▼▼ START: 【核心修正】Shed Roof 邏輯 ▼▼▼ ====
    if roof_type == "shed":
        theta = params.get('theta', 0)
        ridge_orientation = params.get('ridge_orientation')
        is_parallel = (wind_direction == ridge_orientation)

        if is_parallel:
            cp_val = -0.8 if (h / L > 2.5 or h / B > 2.5) else -0.7
            results['側風面(風平行屋脊)'] = cp_val
        else:  # 風向垂直
            h_over_l = h / L if L > 0 else 0

            # 工況1：風從高簷側吹向低簷側 (屋頂為背風面)
            cp_high_to_low_case = -0.7

            # 工況2：風從低簷側吹向高簷側 (屋頂為迎風面)
            df_neg = db['ROOF_CP_DF_NEG']
            cp_low_to_high_case = interpolate_cp_value(df_neg, theta, h_over_l)

            # 根據 filter_by_sign 參數決定回傳內容
            if filter_by_sign:
                # 第五章需要篩選。根據您的最新要求，對調對應關係。
                if sign == 'positive':
                    # 正向風 (+X, +Y) -> 從低簷吹向高簷 (迎風面)
                    results['屋頂(風吹向高簷側)'] = cp_low_to_high_case
                else:  # sign == 'negative'
                    # 負向風 (-X, -Y) -> 從高簷吹向低簷 (背風面)
                    results['屋頂(風吹向低簷側)'] = cp_high_to_low_case
            else:
                # 第四章需要全部，顯示所有可能性
                results['屋頂(風吹向低簷側)'] = cp_high_to_low_case
                results['屋頂(風吹向高簷側)'] = cp_low_to_high_case

        return results
    # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

    # =================================================================
    # Case 3: 拱形屋頂 (表 2.6)
    # =================================================================
    if roof_type == "arched":
        ridge_orientation = params.get('ridge_orientation', 'X')
        is_parallel = (wind_direction == ridge_orientation)

        if is_parallel:
            # 當風向平行於拱頂軸線時，參照 表 2.5 平行風向的規則進行保守計算
            print("  (判斷: 風向平行於拱頂軸線，依工程實務參照 表 2.5 平行風向Cp值)")
            cp_val = -0.8 if (h / L > 2.5 or h / B > 2.5) else -0.7
            results['Cp_parallel_arch'] = cp_val
            return results
        else:
            # *** 自動計算 r 值 ***
            arch_height = params['ridge_height'] - params['eave_height']
            if params['ridge_orientation'] == 'X':
                span = params['B_Y']  # 跨度是垂直於 X 軸的 B_Y
            else:  # ridge_orientation == 'Y'
                span = params['B_X']  # 跨度是垂直於 Y 軸的 B_X

            if span > 0 and arch_height > 0:
                r = arch_height / span
                print(f"  (判斷: 風向垂直於拱頂軸線，自動計算拱高跨度比 r={r:.3f})")
            else:
                r = 0  # 視為平屋頂
                print(f"  (警告: 拱高或跨度為零，無法計算拱形屋頂，視為平屋頂)")
                results['Cp_flat_arch'] = -0.7
                return results

            if 0 < r < 0.2:
                results['windward_P_Cp'] = -0.9
                results['center_Q_Cp'] = -0.7 - r
                results['leeward_P_Cp'] = -0.5
            elif 0.2 <= r < 0.3:
                results['windward_P_Cp'] = 1.5 * r - 0.3
                results['center_Q_Cp'] = -0.7 - r
                results['leeward_P_Cp'] = -0.5
            elif 0.3 <= r <= 0.6:
                results['windward_P_Cp'] = 2.75 * r - 0.7
                results['center_Q_Cp'] = -0.7 - r
                results['leeward_P_Cp'] = -0.5
            else:
                print(f"警告: 拱高跨度比 r={r} 超出規範表 2.6 範圍 (0 < r <= 0.6)")
                return {'Error': 'r out of range'}
            return results

    # =================================================================
    # Case 4: 鋸齒狀屋頂 (表 2.8)
    # =================================================================
    if roof_type == "sawtooth_uniform" or roof_type == "sawtooth_irregular":
        ridge_orientation = params.get('ridge_orientation', 'X')
        is_parallel = (wind_direction == ridge_orientation)

        if is_parallel:
            # 當風向平行於屋脊時，參照 表 2.5 平行風向的規則進行保守計算
            print("  (判斷: 風向平行於屋脊，依工程實務參照 表 2.5 平行風向Cp值)")
            cp_val = -0.8 if (h / L > 2.5 or h / B > 2.5) else -0.7
            results['Cp_parallel_sawtooth'] = cp_val
            return results
        else:
            if roof_type == "sawtooth_uniform":
                theta = params['theta']
                num_spans = params['num_spans']
                print(f"  (判斷: 風向垂直於屋脊，依據表2.8計算)")
                h_over_l = h / L
                print(f"h/L={h_over_l}, theta={theta}")

                # 第一跨的Cp值參考表 2.5
                df_neg = db['ROOF_CP_DF_NEG']
                cp_d1 = interpolate_cp_value(df_neg, theta, h_over_l)
                results['span_1_windward_D_Cp'] = cp_d1
                results['span_1_leeward_E_Cp'] = -0.7

                # 從第二跨開始，Cp值有固定規律
                cp_map = {
                    2: (-0.5, -0.5),
                    3: (-0.5, -0.4),
                    4: (-0.4, -0.3),
                    5: (-0.3, -0.3)
                }
                for i in range(2, num_spans + 1):
                    cp_d, cp_e = cp_map.get(i, (-0.3, -0.3))
                    results[f'span_{i}_windward_D_Cp'] = cp_d
                    results[f'span_{i}_leeward_E_Cp'] = cp_e
                return results
            elif roof_type == "sawtooth_irregular":
                # --- 不規則鋸齒：執行新的、保守的計算策略 ---
                print("  (判斷: 不規則鋸齒屋頂，對每一跨獨立採用 表 2.5 進行保守分析)")
                details = params['sawtooth_details']
                theta = params['theta']
                print(details, theta, "卡卡")

                for i in range(0, len(theta)):
                    if params['h'] != params['eave_height']:
                        theta_i = theta[i]
                        # 注意：h/L 仍然使用建築物的整體參數，因為這是紊流尺度效應

                        h_over_l_i = params['h'] / params['L']
                        print(params['h'], params['L'], h_over_l_i, "卡住")

                        df_neg = db['ROOF_CP_DF_NEG']
                        # 迎風面 D: 完全採用 表 2.5 進行內插
                        cp_d = interpolate_cp_value(df_neg, theta_i, h_over_l_i)
                        # 背風面 E: 同樣採用 表 2.5 的背風面值
                        cp_e = -0.7

                        results[f'span_{i + 1}_windward_D_Cp'] = cp_d
                        results[f'span_{i + 1}_leeward_E_Cp'] = cp_e
                    else:  # 如果某一跨是平的
                        results[f'span_{i + 1}_windward_D_Cp'] = -0.7
                        results[f'span_{i + 1}_leeward_E_Cp'] = -0.7
            return results

    # --- *** 四坡水屋頂的處理 *** ---
    if roof_type == "hip":
        results = {}
        print("  (判斷: 雙斜(四坡水)屋頂，依據分向角度查表)")

        # 根據風向，選擇對應的屋頂角度和 h/L 進行分析
        if wind_direction == 'X':
            # X向風，迎風面角度為 theta_Y
            theta = params.get('theta_Y', 0)
            h_over_l = params['h'] / params['B_X'] if params['B_X'] > 0 else 0
            h_over_b = params['h'] / params['B_Y']  # B 是 B_Y
            print(f"風向 = {wind_direction}, h={params['h']}, L={params['B_X']}, L={params['B_Y']}")
            print(f"h/L = {h_over_l}, h_over_b={h_over_b}")

        elif wind_direction == 'Y':
            theta = params.get('theta_X', 0)
            h_over_l = params['h'] / params['B_Y']  # L 是 B_Y
            h_over_b = params['h'] / params['B_X']  # B 是 B_X
            print(f"風向 = {wind_direction}, h={params['h']}, L={params['B_Y']}, L={params['B_X']}")
            print(f"h/L = {h_over_l}, h_over_b={h_over_b}")

        if h_over_l <= 2.5 or h_over_b <= 2.5:
            cp_m = -0.7
            cp_l = -0.7
        elif h_over_l > 2.5 and h_over_b > 2.5:
            cp_m = -0.8
            cp_l = -0.8
        if params['hip_roof_options']['topType'] == 'ridge':
            cp_m = 0.0

        # 直接套用 表 2.5 的計算邏輯
        if theta >= 60:
            cp_w = 0.01 * theta
        else:
            df_neg = db['ROOF_CP_DF_NEG']
            cp_w = interpolate_cp_value(df_neg, theta, h_over_l)

        results[f'迎風斜面 (θ={theta:.2f}°)'] = cp_w
        results[f'背風斜面'] = cp_l
        results[f'中央頂面'] = cp_m
        return results

    return {}


def calculate_gcpi_coeff(enclosure_status: str, db: dict) -> list:
    gcpi_data = db['GCPI_DATA']
    return gcpi_data.get(enclosure_status, [0.0])


def check_low_rise_building_conditions(params: dict):
    """
    檢查建築物是否滿足規範 2.13 節的所有適用條件。
    返回一個布林值和一條說明訊息。
    """
    h = params.get('h', 0)
    B_X = params.get('B_X', 0)
    B_Y = params.get('B_Y', 0)
    roof_type = params.get('roof_type')

    # 為了檢查 L/B，我們需要考慮兩個風向
    lb_ratio_x = B_X / B_Y if B_Y > 0 else 0  # 風沿 Y 吹, L=B_X, B=B_Y
    lb_ratio_y = B_Y / B_X if B_X > 0 else 0  # 風沿 X 吹, L=B_Y, B=B_X

    conditions = {
        "高度 h <= 18m": h <= 18,
        "剛性建築 h/sqrt(BL) < 3": (h / np.sqrt(B_X * B_Y) < 3) if B_X > 0 and B_Y > 0 else False,
        "深寬比 0.2 <= L/B <= 5": (0.2 <= lb_ratio_x <= 5) and (0.2 <= lb_ratio_y <= 5),
        "近似矩形斷面/封閉式/剛性樓版": roof_type in ['flat', 'gable', 'hip'],  # 簡化判斷
        "迎/背風面積相近 (對稱性)": roof_type in ['flat', 'gable', 'hip']  # 簡化判斷，排除 shed, sawtooth 等
    }

    all_met = all(conditions.values())

    print("\n--- 規範 2.13 節 (低矮建築) 適用性檢查 ---")
    for condition, met in conditions.items():
        status = "✓ 符合" if met else "✗ 不符合"
        print(f"  - {condition:<30}: {status}")

    if not all_met:
        print("  - 結論：不滿足所有低矮建築適用條件。")
    else:
        print("  - 結論：滿足所有低矮建築適用條件。")

    return all_met, conditions


def run_low_rise_building_analysis(params: dict, db: dict):
    """
    執行規範 2.13 節的低矮建築設計風力計算。
    """
    try:
        print("\n\n" + "=" * 30 + " 開始執行 2.13 節低矮建築風力計算 " + "=" * 30)

        # 1. 獲取必要參數
        I = params.get('I', 1.0)
        V10_C = params.get('V10_C', 0)
        h = params.get('h', 0)
        B_X = params.get('B_X', 0)
        B_Y = params.get('B_Y', 0)
        terrain = params.get('terrain', 'C')
        roof_type = params.get('roof_type')

        # 2. 準備報告
        print(f"\n全域參數: I={I}, V10(C)={V10_C}, h={h}, 地況={terrain}")
        header = f"{'風力項目':<25} | {'計算公式 (簡化)':<45} | {'設計風力/扭矩':<20}"
        print(header)
        print("-" * 95)

        # 3. 遍歷兩個風向
        for wind_dir in ['X', 'Y']:
            # 準備特定方向的 Kzt 和 A_z
            if wind_dir == 'X':
                L, B = B_X, B_Y
                is_topo = params.get('is_topo_site_X', False)
                topo_params = {'landform': params.get('landform_X'),
                               'H': params.get('H_X', 0),
                               'Lh': params.get('Lh_X', 0),
                               'x': params.get('x_X', 0),
                               'terrain': terrain}
            else:  # Y
                L, B = B_Y, B_X
                is_topo = params.get('is_topo_site_Y', False)
                topo_params = {'landform': params.get('landform_Y'),
                               'H': params.get('H_Y', 0),
                               'Lh': params.get('Lh_Y', 0),
                               'x': params.get('x_Y', 0),
                               'terrain': terrain}

            Kzt_h = calculate_topography_factor(topo_params, h, db)[0] if is_topo else 1.0

            # ** 關鍵修正：從表格內插 λ 值 **
            lambda_df = db['LAMBDA_DF']
            lambda_val = interpolate_from_table(lambda_df, h, terrain)

            print(f"\n--- {wind_dir} 向風分析 ---")
            print(f"  (使用參數: L={L:.2f}, B={B:.2f}, Kzt(h)={Kzt_h:.3f}, λ={lambda_val:.4f})")

            # 4. 計算順風、橫風、扭轉牆面風力
            A_z = B * h  # 簡化為整個牆面面積
            print(f"B={B}, h={h}, Az = {A_z}")
            S_Dz = 1.49 * (I * V10_C) ** 2 * lambda_val * Kzt_h * A_z
            S_Lz = (0.6 * (L / B) + 0.05) * S_Dz if B > 0 else 0
            S_Tz = 0.21 * (B * S_Dz)

            print(
                f"{f'順風向牆面風力 S_D ({wind_dir}向)':<25} | {'1.49 * (IV10)² * λ * Kzt * Az':<45} | {S_Dz:<20.2f} kgf")
            print(
                f"{f'橫風向牆面風力 S_L ({'Y' if wind_dir == 'X' else 'X'}向)':<25} | {'(0.6*L/B + 0.05) * SDz':<45} | {S_Lz:<20.2f} kgf")
            print(f"{'扭轉向牆面扭矩 S_T':<25} | {'0.21 * (B * SDz)':<45} | {S_Tz:<20.2f} kgf-m")

            # 5. ** 新增：計算屋頂風力 **
            roof_area = B * L
            base_force_term = (I * V10_C) ** 2 * Kzt_h * roof_area

            is_parallel_wind = (wind_dir == params.get('ridge_orientation'))

            if roof_type == 'flat':
                S_RP = 1.4 * base_force_term  # 式 (2.26)
                print(f"{'平屋頂鉛直向上風力 S_RP':<25} | {'1.4 * (IV10)² * Kzt * BL':<45} | {S_RP:<20.2f} kgf")
            else:  # 斜屋頂
                theta = params.get('theta_Y' if wind_dir == 'X' else 'theta_X', params.get('theta', 0))  # 取得對應角度

                if is_parallel_wind:
                    # 風平行於屋脊 (式 2.27, Cpc,3)
                    cpc3 = db['CPC3_VALUE']
                    print(f"Cpc,3={cpc3}")
                    S_R_vertical = base_force_term * lambda_val * cpc3
                    print(
                        f"{f'斜屋頂鉛直風力 S_R (風向平行屋脊)':<25} | {'(IV10)² * Kzt * BL * C*pc,3':<45} | {S_R_vertical:<20.2f} kgf")
                else:
                    # 風垂直於屋脊 (式 2.27, Cpc,1 和 Cpc,2)
                    cpc1_df = db['CPC1_DF']
                    cpc2_df = db['CPC2_DF']

                    # 內插 Cpc,1 (水平力) - 規範只給正值，負值用 nan 處理
                    cpc1_pos = np.interp(theta, cpc1_df.index, cpc1_df['positive'].ffill())
                    cpc1_neg = np.interp(theta, cpc1_df.index, cpc1_df['negative'].ffill())
                    S_R_horizontal_pos = base_force_term * lambda_val * cpc1_pos
                    S_R_horizontal_neg = base_force_term * lambda_val * cpc1_neg
                    print(f"Cpc,1(+)={cpc1_pos}")
                    print(f"Cpc,1(-)={cpc1_neg}")
                    print("**== 風向垂直屋脊 ==**")
                    print(
                        f"{f'斜屋頂水平風力 S_R (正壓)':<25} | {'(IV10)² * Kzt * BL * C*pc,1(+)':<45} | {S_R_horizontal_pos:<20.2f} kgf")
                    print(
                        f"{f'斜屋頂水平風力 S_R (負壓)':<25} | {'(IV10)² * Kzt * BL * C*pc,1(-)':<45} | {S_R_horizontal_neg:<20.2f} kgf")

                    # 內插 Cpc,2 (垂直力) - 有正有負
                    cpc2_pos = np.interp(theta, cpc2_df.index, cpc2_df['positive'].ffill())
                    cpc2_neg = np.interp(theta, cpc2_df.index, cpc2_df['negative'].ffill())
                    S_R_vertical_pos = base_force_term * lambda_val * cpc2_pos
                    S_R_vertical_neg = base_force_term * lambda_val * cpc2_neg

                    print(f"Cpc,2(+)={cpc2_pos}")
                    print(f"Cpc,2(-)={cpc2_neg}")
                    print(
                        f"{f'斜屋頂鉛直風力 S_R (正壓)':<25} | {'(IV10)² * Kzt * BL * C*pc,2(+)':<45} | {S_R_vertical_pos:<20.2f} kgf")
                    print(
                        f"{f'斜屋頂鉛直風力 S_R (負壓)':<25} | {'(IV10)² * Kzt * BL * C*pc,2(-)':<45} | {S_R_vertical_neg:<20.2f} kgf")

        report_data = {
            "message": "局部构材风压计算完成，详细结果请查看后端终端机报告。",
            # 未来可以将上面 print 的表格数据整理成字典，放在这里
        }
        return {"status": "success", "analysis_type": "local_c_and_c", "data": report_data}
    except Exception as e:
        # ... (错误处理) ...
        return {"status": "error", "message": f"局部构材计算过程中发生错误: {str(e)}"}


def get_gcp_value(h: float, theta: float, surface: str, zone: int, area: float, db: dict):
    """
    從數據庫中查詢並內插出 (GCp) 值。

    Args:
        h (float): 建築物平均屋頂高度
        theta (float): 屋頂角度
        surface (str): 'Wall' 或 'Roof'
        zone (int): 區域編號 (1-5)
        area (float): 受風面積 A
        db (dict): 資料庫

    Returns:
        tuple: (gcp_positive, gcp_negative)
    """
    gcp_df = db['GCP_DF']

    # 1. 決定高度條件
    condition = 'h<=18' if h <= 18 else 'h>18'

    # 2. 決定角度範圍 (僅對 h<=18 的屋頂有效)
    theta_range_str = 'N/A'
    if surface == 'Roof' and condition == 'h<=18':
        if 0 <= theta <= 7:
            theta_range_str = str((0, 7))
        elif 7 < theta <= 27:
            theta_range_str = str((7, 27))
        elif 27 < theta <= 45:
            theta_range_str = str((27, 45))
        else:  # 角度超出範圍，使用最接近的
            theta_range_str = str((27, 45))
    elif surface == 'Roof' and condition == 'h>18':
        theta_range_str = 'Any'

    # 3. 查詢並內插
    gcp_positive = 0.0
    gcp_negative = 0.0
    # 查詢正壓
    try:
        # 使用 .loc 找到對應的數據列
        row_pos = gcp_df.loc[(condition, surface, theta_range_str, zone, '+')]
        # 移除 NaN 值以利內插
        row_pos = row_pos.dropna()

        # 進行對數內插
        # np.log10(area)
        # np.log10(row_pos.index) 是已知點的 X 座標
        # row_pos.values 是已知點的 Y 座標
        gcp_positive = np.interp(np.log10(area), np.log10(row_pos.index), row_pos.values)
    except KeyError:
        # 如果找不到對應的正壓曲線 (例如屋頂的 zone 2, 3)，則為 0
        gcp_positive = 0.0

    # 查詢負壓
    try:
        row_neg = gcp_df.loc[(condition, surface, theta_range_str, zone, '-')]
        row_neg = row_neg.dropna()
        gcp_negative = np.interp(np.log10(area), np.log10(row_neg.index), row_neg.values)
    except KeyError:
        gcp_negative = 0.0

    return gcp_positive, gcp_negative


def calculate_gcp_walls_asce7(zone: int, area_ft2: float):
    """
    根據 ASCE 7-22 Table C30.3-1 的方程式，精確計算牆面的 (GCp) 值。
    此函式適用於 h <= 60 ft (18.3 m) 的情況。

    Args:
        zone (int): 區域編號 (4 或 5)
        area_ft2 (float): 有效受風面積，單位為平方英尺 (ft²)

    Returns:
        tuple: (gcp_positive, gcp_negative)
    """
    gcp_pos = 0.0
    gcp_neg = 0.0
    log_A = np.log10(area_ft2) if area_ft2 > 0 else 0

    # --- 計算正風壓 (Positive Pressure) ---
    # 區域 4 和 5 的正壓公式相同
    if area_ft2 <= 10:
        gcp_pos = 1.0
    elif 10 < area_ft2 <= 500:
        # 方程式: (GCp) = 1.1766 - 0.1766 * log(A)
        gcp_pos = 1.1766 - 0.1766 * log_A
    elif area_ft2 > 500:
        gcp_pos = 0.7

    # --- 計算負風壓 (Negative Pressure) ---
    if zone == 4:
        if area_ft2 <= 10:
            gcp_neg = -1.1
        elif 10 < area_ft2 <= 500:
            # 方程式: (GCp) = -1.2766 + 0.1766 * log(A)
            gcp_neg = -1.2766 + 0.1766 * log_A
        else:  # area_ft2 > 500
            gcp_neg = -0.8
    elif zone == 5:
        if area_ft2 <= 10:
            gcp_neg = -1.4
        elif 10 < area_ft2 <= 500:
            # 方程式: (GCp) = -1.7532 + 0.3532 * log(A)
            gcp_neg = -1.7532 + 0.3532 * log_A
        else:  # area_ft2 > 500
            gcp_neg = -0.8

    return gcp_pos, gcp_neg


def calculate_gcp_gable_roof_asce7(theta: float, zone: int, area_ft2: float, has_overhang: bool):
    """
    根據 ASCE 7-22 Tables C30.3-2/3/4/5 的方程式，精確計算山形屋頂的 (GCp) 值。
    此函式適用於 h <= 60 ft (18.3 m) 的情況。

    Args:
        theta (float): 屋頂斜角 (度)
        zone (int): 區域編號 (1, 2, 3, 1', 2e, 2r, 3e, 3r)
        area_ft2 (float): 有效受風面積，單位為平方英尺 (ft²)
        has_overhang (bool): 是否有懸挑屋簷

    Returns:
        tuple: (gcp_positive, gcp_negative)
    """
    gcp_pos = 0.0
    gcp_neg = 0.0
    log_A = np.log10(area_ft2) if area_ft2 > 0 else 0

    # --- Case 1: θ <= 7° (Table C30.3-2) ==> (Figure 30.3-2A) ---
    if 0 <= theta <= 7:
        if not has_overhang:
            # 正風壓 (所有區域相同)
            if area_ft2 <= 10:
                gcp_pos = 0.3
            elif 10 < area_ft2 <= 100:
                gcp_pos = 0.4000 - 0.1000 * log_A
            else:  # A > 100
                gcp_pos = 0.2

            # 負風壓
            if zone == "1'":
                if area_ft2 <= 100:
                    gcp_neg = -0.9
                elif 100 < area_ft2 <= 1000:
                    gcp_neg = -1.9000 + 0.5000 * log_A
                else:
                    gcp_neg = -0.4
            elif zone == 1:
                if area_ft2 <= 10:
                    gcp_neg = -1.7
                elif 10 < area_ft2 <= 500:
                    gcp_neg = -2.1120 + 0.4120 * log_A
                else:
                    gcp_neg = -1.0
            elif zone == 2:
                if area_ft2 <= 10:
                    gcp_neg = -2.3
                elif 10 < area_ft2 <= 500:
                    gcp_neg = -2.8297 + 0.5297 * log_A
                else:
                    gcp_neg = -1.4
            elif zone == 3:
                if area_ft2 <= 10:
                    gcp_neg = -3.2
                elif 10 < area_ft2 <= 500:
                    gcp_neg = -4.2595 + 1.0595 * log_A
                else:
                    gcp_neg = -1.4
        else:  # 有懸挑
            if zone in [1, "1'"]:
                if area_ft2 <= 10:
                    gcp_neg = -1.7
                elif 10 < area_ft2 <= 100:
                    gcp_neg = -1.8000 + 0.1000 * log_A
                elif 100 < area_ft2 <= 500:
                    gcp_neg = -3.3168 + 0.8584 * log_A
                else:
                    gcp_neg = -1.0
            elif zone == 2:
                if area_ft2 <= 10:
                    gcp_neg = -2.3
                elif 10 < area_ft2 <= 500:
                    gcp_neg = -3.0063 + 0.7063 * log_A
                else:
                    gcp_neg = -1.1
            elif zone == 3:
                if area_ft2 <= 10:
                    gcp_neg = -3.2
                elif 10 < area_ft2 <= 500:
                    gcp_neg = -4.4360 + 1.2360 * log_A
                else:
                    gcp_neg = -1.1

    # --- Case 2: 7° < θ <= 20° (Table C30.3-3) ==> (Figure 30.3-2B)  ---
    elif 7 < theta <= 20:
        # 正風壓
        if area_ft2 <= 10:
            gcp_pos = 0.6
        elif 10 < area_ft2 <= 200:
            gcp_pos = 0.8306 - 0.2306 * log_A
        else:
            gcp_pos = 0.3
        # 負風壓
        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -2.0
            elif 10 < area_ft2 <= 300:
                gcp_neg = -3.0155 + 1.0155 * log_A
            else:
                gcp_neg = -0.5
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.7
            elif 10 < area_ft2 <= 200:
                gcp_neg = -4.0067 + 1.3066 * log_A
            else:
                gcp_neg = -1.0
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -3.6
            elif 10 < area_ft2 <= 100:
                gcp_neg = -5.4000 + 1.8000 * log_A
            else:
                gcp_neg = -1.8


    # --- Case 3: 20° < θ <= 27° (Table C30.3-4) ==> (Figure 30.3-2C) ---
    elif 20 < theta <= 27:
        # 正風壓
        if area_ft2 <= 10:
            gcp_pos = 0.6
        elif 10 < area_ft2 <= 200:
            gcp_pos = 0.8306 - 0.2306 * log_A
        else:
            gcp_pos = 0.3
        # 負風壓
        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.5
            elif 10 < area_ft2 <= 200:
                gcp_neg = -2.0380 + 0.5380 * log_A
            else:
                gcp_neg = -0.8
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.5
            elif 10 < area_ft2 <= 100:
                gcp_neg = -3.800 + 1.300 * log_A
            else:
                gcp_neg = -1.2
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -3.0
            elif 10 < area_ft2 <= 100:
                gcp_neg = -4.6 + 1.600 * log_A
            else:
                gcp_neg = -1.5


    # --- Case 4: 27° < θ <= 45° (Table C30.3-5) ==> (Figure 30.3-2D)  ---
    elif 27 < theta <= 45:
        # 正風壓
        if area_ft2 <= 10:
            gcp_pos = 0.9
        elif 10 < area_ft2 <= 200:
            gcp_pos = 1.2074 - 0.3074 * log_A
        else:
            gcp_pos = 0.5
        # 負風壓
        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.8
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.8000 + 1.0000 * log_A
            else:
                gcp_neg = -0.8
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.0
            elif 10 < area_ft2 <= 200:
                gcp_neg = -2.7686 + 0.7686 * log_A
            else:
                gcp_neg = -1.0
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -3.2
            elif 10 < area_ft2 <= 200:
                gcp_neg = -3.6529 + 1.1529 * log_A
            else:
                gcp_neg = -1.0
    return gcp_pos, gcp_neg


def calculate_gcp_hip_roof_asce7(theta: float, h_over_b: float, zone: int, area_ft2: float, has_overhang: bool):
    """
    根據 ASCE 7-22 Tables C30.3-6/7/8/9 的方程式，精確計算四坡水屋頂的 (GCp) 值。
    此函式適用於 h <= 60 ft (18.3 m) 的情況。
    """
    gcp_pos = 0.0
    gcp_neg = 0.0
    log_A = np.log10(area_ft2) if area_ft2 > 0 else 0

    # 內部輔助函式，用於線性內插
    def linear_interp(x, x1, y1, x2, y2):
        if x <= x1: return y1
        if x >= x2: return y2
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    # --- 7° < θ <= 20° (Table C30.3-6) ==> (Figure 30.3-2E)  ---
    if 7 < theta <= 20:
        # 正風壓
        if area_ft2 <= 10:
            gcp_pos = 0.7
        elif 10 < area_ft2 <= 100:
            gcp_pos = 1.1000 - 0.4000 * log_A
        else:
            gcp_pos = 0.3

        # 負風壓
        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.8
            elif 10 < area_ft2 <= 200:
                gcp_neg = -2.5686 + 0.7686 * log_A
            else:
                gcp_neg = -0.8
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.4
            elif 10 < area_ft2 <= 200:
                gcp_neg = -3.2455 + 0.8455 * log_A
            else:
                gcp_neg = -1.3
        elif zone in 3:
            if area_ft2 <= 10:
                gcp_neg = -2.6
            elif 10 < area_ft2 <= 200:
                gcp_neg = -3.5223 + 0.9223 * log_A
            else:
                gcp_neg = -1.4

    # --- 20° < θ <= 27° (Table C30.3-8) ==> (Figure 30.3-2F)  ---
    elif 20 < theta <= 27:
        # 正風壓
        if area_ft2 <= 10:
            gcp_pos = 0.7
        elif 10 < area_ft2 <= 100:
            gcp_pos = 1.1000 - 0.4000 * log_A
        else:
            gcp_pos = 0.3

        # 負風壓
        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.4
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.0000 + 0.6000 * log_A
            else:
                gcp_neg = -0.8
        elif zone in [2, 3]:
            if area_ft2 <= 10:
                gcp_neg = -2.0
            elif 10 < area_ft2 <= 100:
                gcp_neg = -3.000 + 1.000 * log_A
            else:
                gcp_neg = -1.0

    # --- θ = 27° (Table C30.3-9) ==> (Figure 30.3-2G)  ---
    elif theta == 45:
        # 正風壓 (無懸挑)
        if area_ft2 <= 10:
            gcp_pos = 0.7
        elif 10 < area_ft2 <= 100:
            gcp_pos = 1.100 - 0.400 * log_A
        elif area_ft2 >= 100:
            gcp_pos = 0.3

        if zone == 1:
            # 負風壓
            if area_ft2 <= 10:
                gcp_neg = -1.5
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.300 + 0.800 * log_A
            else:
                gcp_neg = -0.700
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -1.8
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.800 + 1.000 * log_A
            else:
                gcp_neg = -0.800
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -2.4
            elif 10 < area_ft2 <= 100:
                gcp_neg = -3.800 + 1.400 * log_A
            else:
                gcp_neg = -1.000
    return gcp_pos, gcp_neg


def calculate_gcp_multispan_gable_roof_asce7(theta: float, zone: int, area_ft2: float, has_overhang: bool):
    gcp_pos = 0.0
    gcp_neg = 0.0
    log_A = np.log10(area_ft2) if area_ft2 > 0 else 0

    # --- Case 1: 10 <= θ <= 30° (Figure 30.3-4) ---
    if 10 < theta <= 30:
        # 正風壓 (所有區域相同)
        if area_ft2 <= 10:
            gcp_pos = 0.6
        elif 10 < area_ft2 <= 100:
            gcp_pos = 0.800 - 0.200 * log_A
        else:  # A > 100
            gcp_pos = 0.4

        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.6
            elif 10 < area_ft2 <= 100:
                gcp_neg = -1.800 + 0.200 * log_A
            else:
                gcp_neg = -1.4
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.2
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.700 + 0.500 * log_A
            else:
                gcp_neg = -1.7
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.7
            elif 10 < area_ft2 <= 100:
                gcp_neg = -3.700 + 1.000 * log_A
            else:
                gcp_neg = -1.7

    # --- Case 2: 30° < θ <= 45° (Figure 30.3-4) ---
    elif 30 < theta <= 45:
        if zone == 1:
            if area_ft2 <= 10:
                gcp_pos = 1.0
                gcp_neg = -2.0
            elif 10 < area_ft2 <= 100:
                gcp_pos = 1.2 - 0.2 * log_A
                gcp_neg = -2.9 + 0.9 * log_A
            else:
                gcp_pos = 0.8
                gcp_neg = -1.1
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_pos = 1.0
                gcp_neg = -2.5
            elif 10 < area_ft2 <= 100:
                gcp_pos = 1.2 - 0.2 * log_A
                gcp_neg = -3.3 + 0.8 * log_A
            else:
                gcp_pos = 0.8
                gcp_neg = -1.7
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_pos = 1.0
                gcp_neg = -2.6
            elif 10 < area_ft2 <= 100:
                gcp_pos = 1.2 - 0.2 * log_A
                gcp_neg = -3.5 + 0.9 * log_A
            else:
                gcp_pos = 0.8
                gcp_neg = -1.7

    return gcp_pos, gcp_neg


def calculate_gcp_shed_roof_asce7(theta: float, zone: int, area_ft2: float, has_overhang: bool):
    gcp_pos = 0.0
    gcp_neg = 0.0
    log_A = np.log10(area_ft2) if area_ft2 > 0 else 0

    # --- Case 1: θ <= 3° (Figure 30.3-2A) ---
    if theta <= 3:
        # 正風壓 (所有區域相同)
        if area_ft2 <= 10:
            gcp_pos = 0.3
        elif 10 < area_ft2 <= 100:
            gcp_pos = 0.4000 - 0.1000 * log_A
        else:  # A > 100
            gcp_pos = 0.2

        if zone == "1'":
            if area_ft2 <= 100:
                gcp_neg = -0.9
            elif 100 < area_ft2 <= 1000:
                gcp_neg = -1.9000 + 0.5000 * log_A
            else:
                gcp_neg = -0.4
        elif zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.7
            elif 10 < area_ft2 <= 500:
                gcp_neg = -2.1120 + 0.4120 * log_A
            else:
                gcp_neg = -1.0
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.3
            elif 10 < area_ft2 <= 500:
                gcp_neg = -2.8297 + 0.5297 * log_A
            else:
                gcp_neg = -1.4
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -3.2
            elif 10 < area_ft2 <= 500:
                gcp_neg = -4.2595 + 1.0595 * log_A
            else:
                gcp_neg = -1.4

    elif 3 <= theta <= 10:
        if area_ft2 <= 10:
            gcp_pos = 0.3
        elif 10 < area_ft2 <= 100:
            gcp_pos = 0.4 - 0.1 * log_A
        else:
            gcp_pos = 0.2

        if zone == 1:
            gcp_neg = -1.1

        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -1.3
            elif 10 < area_ft2 <= 100:
                gcp_neg = -1.4 + 0.1 * log_A
            else:
                gcp_neg = -1.2

        elif zone == "2'":
            if area_ft2 <= 10:
                gcp_neg = -1.6
            elif 10 < area_ft2 <= 100:
                gcp_neg = -1.7 + 0.1 * log_A
            else:
                gcp_neg = -1.5

        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -1.8
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.4 + 0.6 * log_A
            else:
                gcp_neg = -1.2

        elif zone == "3'":
            if area_ft2 <= 10:
                gcp_neg = -2.6
            elif 10 < area_ft2 <= 100:
                gcp_neg = -3.6 + 1.0 * log_A
            else:
                gcp_neg = -1.6

    elif 10 < theta <= 30:
        if area_ft2 <= 10:
            gcp_pos = 0.4
        elif 10 < area_ft2 <= 100:
            gcp_pos = 0.5 - 0.1 * log_A
        else:
            gcp_pos = 0.3

        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.3
            elif 10 < area_ft2 <= 100:
                gcp_neg = -1.5 + 0.2 * log_A
            else:
                gcp_neg = -1.1

        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -1.8
            elif 10 < area_ft2 <= 100:
                gcp_neg = -2.4 + 0.6 * log_A
            else:
                gcp_neg = -1.2

        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -2.9
            elif 10 < area_ft2 <= 100:
                gcp_neg = -3.8 + 0.9 * log_A
            else:
                gcp_neg = -2.0

    return gcp_pos, gcp_neg


def calculate_gcp_arched_roof_asce7(params: dict, zone: str, area_ft2: float, db: dict):
    """
    依據 ASCE 7-22 Fig 30.3-6 及其註解，計算拱形屋頂的 C&C 風壓係數。
    - 周邊區域 (C) 借用山形屋頂的 Zone 2 和 3 進行計算。
    - 內部區域 (A, B) 使用圖中提供的係數。
    """
    # 從 params 中提取計算所需參數
    rise = params.get('ridge_height', 0) - params.get('eave_height', 0)
    gcp_pos, gcp_neg = 0, 0

    # 跨度 B 是垂直于拱頂軸線的寬度
    span = params.get('B_Y') if params.get('ridge_orientation') == 'X' else params.get('B_X')

    r = rise / span if span > 0 else 0
    is_at_ground_level = params.get('is_at_ground_level', False)

    if zone in ['C-2', 'C-3']:  # 代表周邊區域，借用 Gable Roof Zone 2 或 3
        theta_equivalent = 0.0
        if rise > 0 and span > 0:
            try:
                radius = ((span ** 2) / 4 + rise ** 2) / (2 * rise)
                ratio_for_asin = (span / 2) / radius
                if -1 <= ratio_for_asin <= 1:
                    theta_equivalent = np.rad2deg(np.arcsin(ratio_for_asin))
                else:
                    theta_equivalent = 90.0  # 理論上不會發生
            except ZeroDivisionError:
                theta_equivalent = 0.0

        # **關鍵**：複用我們為 Gable Roof 寫的函式
        gable_zone = 2 if zone == 'C-2' else 3
        # 假設沒有懸挑，因為規範圖並未針對拱形屋頂的懸挑提供詳細說明
        gcp_pos, gcp_neg = calculate_gcp_gable_roof_asce7(theta_equivalent, gable_zone, area_ft2, False)
        return gcp_pos, gcp_neg

    elif zone == 'A':
        if not is_at_ground_level:
            if 0 < r < 0.2:
                gcp_pos = 1.8 * r - 0.36
                gcp_neg = -1.08
            elif 0.2 <= r < 0.3:
                gcp_pos = 7.2 * r - 2.52
                gcp_neg = -0.6
            elif 0.3 <= r < 0.6:
                gcp_pos = 3.3 * r - 0.84
                gcp_neg = -0.6
        elif is_at_ground_level:
            if 0 < r <= 0.6:
                gcp_pos = 1.68 * r
                gcp_neg = -0.6
    elif zone == 'B':
        gcp_pos = 0
        gcp_neg = -0.84 - 1.2 * r

    return gcp_pos, gcp_neg


def calculate_gcp_walls_flatroof_hover18_asce7(zone: int, area_ft2: float, surface: str):
    gcp_pos = 0.0
    gcp_neg = 0.0
    log_A = np.log10(area_ft2) if area_ft2 > 0 else 0
    if surface == "walls":
        if zone == 4:
            if area_ft2 <= 20:
                gcp_pos = 0.9
                gcp_neg = -0.9
            elif 20 < area_ft2 <= 500:
                gcp_pos = 1.1792 - 0.2146 * log_A
                gcp_neg = -1.0862 + 0.1431 * log_A
            else:
                gcp_pos = 0.6
                gcp_neg = -0.7
        elif zone == 5:
            if area_ft2 <= 20:
                gcp_pos = 0.9
                gcp_neg = -1.8
            elif 20 < area_ft2 <= 500:
                gcp_pos = 1.1792 - 0.2146 * log_A
                gcp_neg = -2.5445 + 0.5722 * log_A
            else:
                gcp_pos = 0.6
                gcp_neg = -1.0

    elif surface == "flat":
        if zone == 1:
            if area_ft2 <= 10:
                gcp_neg = -1.4
            elif 10 < area_ft2 <= 500:
                gcp_neg = -1.6943 + 0.2943 * log_A
            else:
                gcp_neg = -0.9
        elif zone == 2:
            if area_ft2 <= 10:
                gcp_neg = -2.3
            elif 10 < area_ft2 <= 500:
                gcp_neg = -2.7120 + 0.4120 * log_A
            else:
                gcp_neg = -1.6
        elif zone == 3:
            if area_ft2 <= 10:
                gcp_neg = -3.2
            elif 10 < area_ft2 <= 500:
                gcp_neg = -3.7297 + 0.5297 * log_A
            else:
                gcp_neg = -2.3
    return gcp_pos, gcp_neg


def calculate_parameter_a(h: float, B: float, L: float, theta: float):
    """
    根據 ASCE 7-16 (或類似的台灣規範) 計算局部構材的區域劃分寬度 'a'。
    包含所有上下限及例外條款。所有單位應為公尺(m)。

    Args:
        h (float): 平均屋頂高度 (m)
        B (float): 垂直於風向的建築寬度 (m)
        L (float): 平行於風向的建築深度 (m)
        theta (float): 屋頂斜角 (度)

    Returns:
        float: 計算出的 a 值 (m)
    """
    # 找到最小水平尺寸
    least_horizontal_dim = min(B, L)

    # 1. 基本計算：取 0.1 * 最小寬度 或 0.4 * h 中的較小值
    val1 = 0.1 * least_horizontal_dim
    val2 = 0.4 * h
    a_intermediate = min(val1, val2)

    # 2. 檢查下限：不得小於 0.04 * 最小寬度 或 0.9 公尺
    min1 = 0.04 * least_horizontal_dim
    min2 = 0.9  # 單位為公尺
    lower_bound = max(min1, min2)  # 取兩個下限中的較大者

    a_final = max(a_intermediate, lower_bound)  # a 的值必須大於等於下限

    # 3. 檢查例外條款 (針對大型緩坡屋頂)
    # 條件: θ <= 7° 且 最小水平尺寸 > 90 公尺
    if theta <= 7 and least_horizontal_dim > 90:
        upper_bound = 0.8 * h
        # 如果計算出的 a 超過了上限，就取上限值
        if a_final > upper_bound:
            print(f"  - (例外條款) a={a_final:.2f}m 超出上限 0.8*h={upper_bound:.2f}m，取上限值。")
            a_final = upper_bound

    return a_final


def get_terrain_parameters(terrain_category: str, db: dict):
    """根据地况类别，从数据库中提取所有相关参数"""
    if terrain_category in db['TERRAIN_DF'].index:
        return db['TERRAIN_DF'].loc[terrain_category].to_dict()
    return {}


def consolidate_wall_segments(segments: list, eave_height: float):
    """
    將多個牆面分段合併為矩形部分和山牆部分。
    Args:
        segments (list): 從 generate_wall_segments 得到的原始分段列表。
        eave_height (float): 建築物的簷高，用於區分矩形和山牆部分。

    Returns:
        list: 一個包含合併後分段資訊的列表，每個元素代表一個合併區塊。
    """
    if not segments:
        return []

    rect_part = [s for s in segments if s['z_end'] <= eave_height]
    gable_part = [s for s in segments if s['z_end'] > eave_height]

    consolidated_list = []

    # 處理 0 到簷高的矩形部分
    if rect_part:
        total_area = sum(s['area'] for s in rect_part)
        if total_area > 1e-9:
            moment = sum(s['area'] * s['centroid_z'] for s in rect_part)
            centroid = moment / total_area
            min_z = min(s['z_start'] for s in rect_part)
            max_z = max(s['z_end'] for s in rect_part)
            consolidated_list.append({
                'elevation': f"{min_z:.2f}-{max_z:.2f}",
                'z_bar': centroid
            })

    # 處理簷高以上的山牆部分
    if gable_part:
        total_area = sum(s['area'] for s in gable_part)
        if total_area > 1e-9:
            moment = sum(s['area'] * s['centroid_z'] for s in gable_part)
            centroid = moment / total_area
            min_z = min(s['z_start'] for s in gable_part)
            max_z = max(s['z_end'] for s in gable_part)
            consolidated_list.append({
                'elevation': f"{min_z:.2f}-{max_z:.2f}",
                'z_bar': centroid
            })

    return consolidated_list


# ==============================================================================
# Phase 3: 牆面分段與報告生成
# ==============================================================================
def wall_classification(params: dict):
    print("這裡是牆面分類")
    print(params)
    roof_type = params['roof_type']
    eave_h = params['eave_height']
    ridge_h = params['ridge_height']

    # print(f"屋頂形式 = {roof_type}, 屋簷高 = {eave_h}, 屋脊高 = {ridge_h}")

    ## 雙斜屋頂狀態下，四個面牆高都到簷高的地方而已
    ## 下面再依照屋頂形式及屋脊(拱軸線方向)去改變各個面牆高

    fourside_wall_hieght = {"wall_X_pos_h": eave_h, "wall_X_neg_h": eave_h,
                            "wall_Y_pos_h": eave_h, "wall_Y_neg_h": eave_h}
    if roof_type in ["flat", "gable", "shed", "arched", "sawtooth_uniform", "sawtooth_irregular"]:
        ridge_orientation = params['ridge_orientation']
        if ridge_orientation == "X":
            ### 垂直於X風向的牆面 ###
            fourside_wall_hieght = {"wall_X_pos_h": ridge_h, "wall_X_neg_h": ridge_h,
                                    "wall_Y_pos_h": eave_h, "wall_Y_neg_h": eave_h}
            if roof_type == "shed":
                fourside_wall_hieght = {"wall_X_pos_h": ridge_h, "wall_X_neg_h": ridge_h,
                                        "wall_Y_pos_h": ridge_h, "wall_Y_neg_h": eave_h}
        elif ridge_orientation == "Y":
            ### 垂直於Y風向的牆面 ###
            fourside_wall_hieght = {"wall_X_pos_h": eave_h, "wall_X_neg_h": eave_h,
                                    "wall_Y_pos_h": ridge_h, "wall_Y_neg_h": ridge_h}
            if roof_type == "shed":
                fourside_wall_hieght = {"wall_X_pos_h": eave_h, "wall_X_neg_h": ridge_h,
                                        "wall_Y_pos_h": eave_h, "wall_Y_neg_h": eave_h}
    return fourside_wall_hieght


def generate_wall_segments(base_width, eave_h, ridge_h, roof_type, segment_height=2.0):
    rect_segments = generate_rectangular_segments(base_width, eave_h, 0, segment_height)
    gable_segments = []
    if ridge_h > eave_h:
        gable_segments_above_eave = generate_gable_segments(base_width, eave_h, ridge_h, roof_type, segment_height)
        gable_segments = rect_segments + gable_segments_above_eave
    else:
        gable_segments = rect_segments
    wall_segments = rect_segments + gable_segments
    return wall_segments


def generate_rectangular_segments(base_width, top_h, bottom_h=0, segment_height=2.0, wallname="牆",
                                  important_heights=None):
    segments = []
    cut_points = [bottom_h]

    # ===== START OF MODIFICATION =====
    # 核心修正：將重要的中間高度（如簷高）加入分割點
    if important_heights:
        for h in important_heights:
            if bottom_h < h < top_h:
                cut_points.append(h)
    # ===== END OF MODIFICATION =====

    if (top_h - bottom_h) > 5 and bottom_h < 5:
        cut_points.append(5.0)
        start_h = 5.0
    else:
        start_h = bottom_h

    # 產生規律的分割點
    additional_cuts = np.arange(start_h + segment_height, top_h, segment_height)
    cut_points.extend(additional_cuts.tolist())
    cut_points.append(top_h)

    # 移除重複並排序
    cut_points = np.unique(np.array(cut_points))

    for i in range(len(cut_points) - 1):
        z1, z2 = cut_points[i], cut_points[i + 1]
        area = base_width * (z2 - z1)
        centroid = (z1 + z2) / 2
        segments.append({'z_start': z1, 'z_end': z2, 'area': area, 'centroid_z': centroid, "wallname": wallname})
    return segments


def generate_gable_segments(base_width, eave_h, ridge_h, roof_type, simplify_gable=False, segment_height=2.0,
                            wallname="牆"):
    gable_segments = []
    if simplify_gable and roof_type != "arched":
        # 簡化模式：將簷高以上視為一個單一的三角形
        z1, z2 = eave_h, ridge_h
        area = base_width * (ridge_h - eave_h) / 2
        # 三角形形心在高度的 1/3 處
        centroid = eave_h + (ridge_h - eave_h) / 3
        gable_segments.append({'z_start': z1, 'z_end': z2, 'area': area, 'centroid_z': centroid, 'wallname': wallname})

    elif roof_type == "arched":
        # --- *** 拱形山牆精確計算 *** ---
        arch_h = ridge_h - eave_h
        half_b = base_width / 2

        if arch_h > 0:
            y_center = (arch_h ** 2 - half_b ** 2) / (2 * arch_h)
            radius = arch_h - y_center

            def get_x_from_y(y):  # y 相對於簷高
                if radius ** 2 - (y - y_center) ** 2 < 0: return 0
                return np.sqrt(radius ** 2 - (y - y_center) ** 2)

            # 積分求面積和形心
            from scipy.integrate import quad

            gable_cuts = np.arange(eave_h, ridge_h, segment_height)
            gable_cuts = np.append(gable_cuts, ridge_h)
            gable_cuts = np.unique(gable_cuts)
            for i in range(len(gable_cuts) - 1):
                z1, z2 = gable_cuts[i], gable_cuts[i + 1]
                y1, y2 = z1 - eave_h, z2 - eave_h

                # 面積 = 2 * integral(x dy) from y1 to y2
                area, _ = quad(lambda y: 2 * get_x_from_y(y), y1, y2)

                # 形心 = integral(y * dA) / integral(dA)
                # dA = 2 * x * dy
                moment_of_area, _ = quad(lambda y: y * 2 * get_x_from_y(y), y1, y2)
                if area > 1e-6:
                    centroid_y = moment_of_area / area
                    centroid = eave_h + centroid_y
                else:
                    centroid = (z1 + z2) / 2

                gable_segments.append(
                    {'z_start': z1, 'z_end': z2, 'area': area, 'centroid_z': centroid, 'wallname': wallname})

    else:
        # 三角形山牆
        gable_cuts = np.arange(eave_h, ridge_h, segment_height)
        gable_cuts = np.append(gable_cuts, ridge_h)
        gable_cuts = np.unique(gable_cuts)
        for i in range(len(gable_cuts) - 1):
            z1, z2 = gable_cuts[i], gable_cuts[i + 1]
            h_gable = ridge_h - eave_h
            h1 = z1 - eave_h  # 梯形下底距山牆底的高度
            h2 = z2 - eave_h  # 梯形上底距山牆底的高度

            # 計算梯形的上下底寬
            w1 = base_width * (1 - h1 / h_gable)  # 下底寬
            w2 = base_width * (1 - h2 / h_gable)  # 上底寬
            area = (w1 + w2) / 2 * (z2 - z1)

            h_trap = z2 - z1
            if (w1 + w2) > 0:  # 避免除以零
                centroid_y_from_base = (h_trap / 3) * (2 * w2 + w1) / (w1 + w2)
                centroid = z1 + centroid_y_from_base
            else:  # 如果是最後一個小三角形，面積趨近於零
                centroid = z1

            gable_segments.append(
                {'z_start': z1, 'z_end': z2, 'area': area, 'centroid_z': centroid, 'wallname': wallname})
    return gable_segments


def get_wall_segments(dir_params: dict, wind_dir: str):
    """根據風向和屋脊方向，回傳迎風/背風牆和側風牆的分段列表"""
    eave_h = dir_params['eave_height']
    ridge_h = dir_params['ridge_height']
    roof_type = dir_params['roof_type']
    seg_h = dir_params['segmentHeight']

    is_parallel_wind = (wind_dir == dir_params.get('ridge_orientation'))
    side_wall_components = {}

    # 如果是平屋頂、四坡水屋頂或無斜度屋頂
    if roof_type in ['flat', 'hip'] or ridge_h <= eave_h:
        windward_segments = generate_rectangular_segments(dir_params['B'], eave_h, segment_height=seg_h,
                                                          wallname="迎風牆")
        leeward_segments = generate_rectangular_segments(dir_params['B'], eave_h, segment_height=seg_h,
                                                         wallname="背風牆")
        side_wall_segments = generate_rectangular_segments(dir_params['L'], eave_h, segment_height=seg_h,
                                                           wallname="側風牆")
        side_wall_components['main'] = side_wall_segments
        return windward_segments, leeward_segments, side_wall_components

    # 如果風平行於屋脊
    if is_parallel_wind:
        # 迎風/背風牆是山牆
        rect_part_windward = generate_rectangular_segments(dir_params['B'], eave_h, segment_height=seg_h,
                                                           wallname="迎風牆")
        gable_part_windward = generate_gable_segments(dir_params['B'], eave_h, ridge_h, roof_type, segment_height=seg_h,
                                                      wallname="迎風牆")
        windward_segments = rect_part_windward + gable_part_windward

        rect_part_leeward = generate_rectangular_segments(dir_params['B'], eave_h, segment_height=seg_h,
                                                          wallname="背風牆")
        gable_part_leeward = generate_gable_segments(dir_params['B'], eave_h, ridge_h, roof_type, segment_height=seg_h,
                                                     wallname="背風牆")
        leeward_segments = rect_part_leeward + gable_part_leeward

        if roof_type == 'shed':
            side_wall_low_segments = generate_rectangular_segments(dir_params['L'], eave_h, segment_height=seg_h,
                                                                   wallname="側風牆(低)")
            side_wall_high_segments = generate_rectangular_segments(
                dir_params['L'],
                ridge_h,
                segment_height=seg_h,
                wallname="側風牆(高)",
                important_heights=[eave_h]  # <--- 在此傳入簷高
            )
            side_wall_components['low'] = side_wall_low_segments
            side_wall_components['high'] = side_wall_high_segments
        else:
            side_wall_segments = generate_rectangular_segments(dir_params['L'], eave_h, segment_height=seg_h,
                                                               wallname="側風牆")
            side_wall_components['main'] = side_wall_segments

        return windward_segments, leeward_segments, side_wall_components


    else:  # 風垂直於屋脊
        leeward_segments = generate_rectangular_segments(dir_params['B'], eave_h, segment_height=seg_h,
                                                         wallname='背風牆')

        if roof_type == 'shed':
            windward_segments_wind_positive = generate_rectangular_segments(dir_params['B'], eave_h,
                                                                            segment_height=seg_h, wallname='迎風牆(低)')
            leeward_segments_wind_positive = generate_rectangular_segments(dir_params['B'], ridge_h,
                                                                           segment_height=seg_h, wallname='背風牆(高)')
            windward_segments_wind_negative = generate_rectangular_segments(dir_params['B'], ridge_h,
                                                                            segment_height=seg_h, wallname='迎風牆(高)')
            leeward_segments_wind_negative = generate_rectangular_segments(dir_params['B'], eave_h,
                                                                           segment_height=seg_h, wallname='背風牆(低)')
            windward_segments = [windward_segments_wind_positive, windward_segments_wind_negative]
            leeward_segments = [leeward_segments_wind_positive, leeward_segments_wind_negative]
        else:
            windward_segments = generate_rectangular_segments(dir_params['B'], eave_h, segment_height=seg_h,
                                                              wallname='迎風牆')

            # 側風牆是山牆
            rect_part_L = generate_rectangular_segments(dir_params['L'], eave_h, segment_height=seg_h,
                                                        wallname='側風牆')
            gable_part_L = generate_gable_segments(dir_params['L'], eave_h, ridge_h, roof_type, segment_height=seg_h,
                                                   wallname='側風牆')
            side_wall_segments = rect_part_L + gable_part_L
            side_wall_components['main'] = side_wall_segments

        return windward_segments, leeward_segments, side_wall_components


def run_general_method_analysis(params: dict):
    """
    執行完整的風力分析，並在後端終端機打印詳細報告。
    """
    try:
        db = setup_databases()

        # 建立一个字典来储存所有计算结果
        analysis_results = {
            'summary': {},
            'X_dir': {},
            'Y_dir': {}
        }

        # 1. 计算与风向无关的通用参数
        analysis_results['summary']['h'] = params.get('h')
        analysis_results['summary']['theta'] = params.get('theta')
        # 如果是四坡水屋顶，则分别记录
        if params.get('roof_type') == 'hip':
            analysis_results['summary']['theta_X'] = params.get('theta_X')
            analysis_results['summary']['theta_Y'] = params.get('theta_Y')

        # 获取内风压系数
        gcpi_values = calculate_gcpi_coeff(params.get('enclosure_status', '封閉式建築'), db)
        analysis_results['summary']['gcpi'] = gcpi_values

        for wind_dir in ['X', 'Y']:
            print("\n\n" + "=" * 30 + f" 開始 {wind_dir} 向風力分析 " + "=" * 30)

            # 1. 準備特定方向的參數
            dir_params = params.copy()
            if wind_dir == 'X':
                dir_params['L'], dir_params['B'] = dir_params['B_X'], dir_params['B_Y']
                dir_params['fn'] = dir_params.get('fn_X', 1.0)  # 使用 .get 提供預設值
                dir_params['fa'] = dir_params.get('fn_Y', 1.0)  # 使用 .get 提供預設值
                dir_params['ft'] = dir_params.get('ft', 1.0)  # 使用 .get 提供預設值

                if dir_params.get('is_topo_site_X'):
                    dir_params.update({
                        'landform': dir_params.get('landform_X'), 'H': dir_params.get('H_X', 0),
                        'Lh': dir_params.get('Lh_X', 0), 'x': dir_params.get('x_X', 0), 'is_topo_site': True
                    })
                else:
                    dir_params['is_topo_site'] = False
            else:  # Y
                dir_params['L'], dir_params['B'] = dir_params['B_Y'], dir_params['B_X']
                dir_params['fn'] = dir_params.get('fn_Y', 1.0)
                dir_params['fa'] = dir_params.get('fn_X', 1.0)
                dir_params['ft'] = dir_params.get('ft', 1.0)  # 使用 .get 提供預設值

                if dir_params.get('is_topo_site_Y'):
                    dir_params.update({
                        'landform': dir_params.get('landform_Y'), 'H': dir_params.get('H_Y', 0),
                        'Lh': dir_params.get('Lh_Y', 0), 'x': dir_params.get('x_Y', 0), 'is_topo_site': True
                    })
                else:
                    dir_params['is_topo_site'] = False

            dir_params['building_rigidity'] = '普通' if dir_params['fn'] >= 1.0 else '柔性'

            # 2. 計算全域參數
            if dir_params.get('is_topo_site'):
                kzt_at_h, _, _, _ = calculate_topography_factor(dir_params, dir_params['h'], db)
                dir_params['Kzt'] = kzt_at_h
            else:
                dir_params['Kzt'] = 1.0

            common_gust_params = calculate_gust_common_params(dir_params, db)

            if dir_params['building_rigidity'] == "普通":
                G_factor = calculate_G_factor(dir_params, common_gust_params)['final_value']
            else:
                G_factor = calculate_Gf_factor(dir_params, common_gust_params, db)['final_value']

            print("我也想幹黃貞瑜")
            q_h = calculate_velocity_pressure(dir_params['h'], dir_params['I'], dir_params['V10_C'],
                                              dir_params['terrain'], dir_params['Kzt'], db)

            # 呼叫橫風向計算函式
            transverse_results = calculate_transverse_wind_force(dir_params, db)
            torsional_results = calculate_torsional_moment(dir_params, db)

            # 3. 獲取所有風壓係數
            wall_cp = calculate_wall_coeffs(dir_params['L'], dir_params['B'], db)
            roof_cp_results = calculate_roof_coeffs(dir_params, db, wind_dir)
            gcpi_values = calculate_gcpi_coeff(params.get('enclosure_status', '封閉式建築'), db)

            # 4. 準備牆面分段
            four_side_wall = wall_classification(params)
            windward_segments, leeward_segments, side_wall_segments = get_wall_segments(dir_params, wind_dir)

            # 5. 建立所有計算工況
            cases_to_run = []
            if 'windward_Cp_case1 (正值)' in roof_cp_results:
                for gcpi in gcpi_values:
                    # 工况1: 使用正值Cp
                    roof_cp_copy1 = roof_cp_results.copy()
                    roof_cp_copy1['windward_Cp'] = roof_cp_copy1.pop('windward_Cp_case1 (正值)')
                    roof_cp_copy1.pop('windward_Cp_case2 (负值)', None)
                    cases_to_run.append(
                        {'gcpi': gcpi, 'roof_cp': roof_cp_copy1, 'case_name': f"GCpi={gcpi:+.3f}, Roof_Cp(pos)"})
                    # 工况2: 使用负值Cp
                    roof_cp_copy2 = roof_cp_results.copy()
                    roof_cp_copy2['windward_Cp'] = roof_cp_copy2.pop('windward_Cp_case2 (负值)')
                    roof_cp_copy2.pop('windward_Cp_case1 (正值)', None)
                    cases_to_run.append(
                        {'gcpi': gcpi, 'roof_cp': roof_cp_copy2, 'case_name': f"GCpi={gcpi:+.3f}, Roof_Cp(neg)"})
            else:
                for gcpi in gcpi_values:
                    cases_to_run.append({'gcpi': gcpi, 'roof_cp': roof_cp_results, 'case_name': f"GCpi={gcpi:+.3f}"})

            # 6. 遍歷工況並打印報告
            for case in cases_to_run:
                gcpi = case['gcpi']
                current_roof_cp = case['roof_cp']
                print("\n" + "-" * 120)
                print(f"計算工況: {wind_dir} 向風, {case['case_name']}")
                print(f"全域參數: Kzt={dir_params['Kzt']:.3f}, G={G_factor:.3f}, q(h)={q_h:.2f} kgf/m²")
                header = (
                    f"{'表面':<8} |"
                    f" {'高度 z(m)':<12} |"
                    f" {'cz(m)':<8} |"
                    f" {'K(z)':<7} | "
                    f"{'Kzt_z':<7} | "
                    f"{'q(z)':<8} |"
                    f" {'G':<5} | "
                    f"{'Cp':<6} | "
                    f"{'K(h)':<7} | "
                    f"{'q(h)':<8} | "
                    f"{'GCpi':<7} | "
                    f"{'p_順風(kgf/m²)':<15} |"
                    f"{'p_橫風(kgf/m²)':<15} |"
                    f"{'M_扭矩(kgf/m²)':<15}"
                )
                print(header)
                print("-" * 120)

                # --- 迎風牆 ---
                if params['roof_type'] == 'shed' and wind_dir != params['ridge_orientation']:
                    for i in range(0, 2):
                        windward_segments_shed = windward_segments[i]
                        leeward_segments_shed = leeward_segments[i]
                        if i == 0:
                            print("------------------------------")
                            print(f"風向為+{wind_dir}向")
                            print("------------------------------")
                        elif i == 1:
                            print("------------------------------")
                            print(f"風向為-{wind_dir}向")
                            print("------------------------------")

                        for seg in windward_segments_shed:
                            wallname = seg['wallname']
                            z_start, z_end, centroid_z = seg['z_start'], seg['z_end'], seg['centroid_z']
                            area = seg['area']
                            z_mid = (z_start + z_end) / 2
                            kzt_z = calculate_topography_factor(dir_params, z_mid, db)[0] if dir_params.get(
                                'is_topo_site') else 1.0
                            q_z = calculate_velocity_pressure(z_mid, dir_params['I'], dir_params['V10_C'],
                                                              dir_params['terrain'], kzt_z, db)
                            p_z = q_z * G_factor * wall_cp['windward'] - q_h * gcpi
                            W_d_z = p_z * area

                            k_z = calculate_velocity_pressure_coeff(z_mid, dir_params['terrain'], db)
                            k_h = calculate_velocity_pressure_coeff(dir_params['h'], dir_params['terrain'], db)

                            if transverse_results:
                                if transverse_results['method'] == 'simplified_2_21':
                                    p_l_z = transverse_results['factor'] * p_z
                                elif transverse_results['method'] == 'spectral_2_22':
                                    p_l_z = q_h * transverse_results['calculation_factor'] * (z_mid / dir_params['h'])

                            if torsional_results:
                                if torsional_results['method'] == 'simplified_2_23':
                                    m_t_z = torsional_results['factor'] * p_z
                                elif torsional_results['method'] == 'spectral_2_24':
                                    m_t_z = q_h * torsional_results['calculation_factor'] * (z_mid / dir_params['h'])

                            print(
                                f"{wallname:<8} | "
                                f"{seg['z_start']:.2f}-{seg['z_end']:.2f}{' ' * (15 - 11)} |"
                                f"{centroid_z:<8.3f} | "
                                f"{k_z:<7.3f} | "
                                f"{kzt_z:<7.3f} |"
                                f"{q_z:<8.2f} |"
                                f"{G_factor:<7.3f} |"
                                f"{wall_cp['windward']:<7.2f} |"
                                f"{k_h:<7.3f} |"
                                f"{q_h:<7.3f} |"
                                f"{gcpi:<7.3f} |"
                                f"{p_z:<15.2f}"
                                f"{p_l_z:<15.2f} |"
                                f"{m_t_z:<15.2f}"
                            )

                        for seg in leeward_segments_shed:  # 假設背風牆總是矩形
                            wallname = seg['wallname']
                            p_h = q_h * (G_factor * wall_cp['leeward'] - gcpi)
                            z_start, z_end, centroid_z = seg['z_start'], seg['z_end'], seg['centroid_z']
                            print(
                                f"{wallname:<8} | "
                                f"{seg['z_start']:.2f}-{seg['z_end']:.2f}{' ' * (15 - 11)} |"
                                f"{centroid_z:<8.3f} | "
                                f"{'-':<7} | "
                                f"{'-':<7} |"
                                f"{'-':<8} |"
                                f"{G_factor:<7.3f} |"
                                f"{wall_cp['leeward']:<7.2f} |"
                                f"{k_h:<7.3f} |"
                                f"{q_h:<7.3f} |"
                                f"{gcpi:<7.3f} |"
                                f"{p_h:<15.2f}")

                else:
                    for seg in windward_segments:
                        wallname = seg['wallname']
                        z_start, z_end, centroid_z = seg['z_start'], seg['z_end'], seg['centroid_z']
                        area = seg['area']
                        z_mid = (z_start + z_end) / 2
                        kzt_z = calculate_topography_factor(dir_params, z_mid, db)[0] if dir_params.get(
                            'is_topo_site') else 1.0
                        q_z = calculate_velocity_pressure(z_mid, dir_params['I'], dir_params['V10_C'],
                                                          dir_params['terrain'], kzt_z, db)
                        p_z = q_z * G_factor * wall_cp['windward'] - q_h * gcpi
                        W_d_z = p_z * area

                        k_z = calculate_velocity_pressure_coeff(z_mid, dir_params['terrain'], db)
                        k_h = calculate_velocity_pressure_coeff(dir_params['h'], dir_params['terrain'], db)

                        if transverse_results:
                            if transverse_results['method'] == 'simplified_2_21':
                                p_l_z = transverse_results['factor'] * p_z
                            elif transverse_results['method'] == 'spectral_2_22':
                                p_l_z = q_h * transverse_results['calculation_factor'] * (z_mid / dir_params['h'])

                        if torsional_results:
                            if torsional_results['method'] == 'simplified_2_23':
                                m_t_z = torsional_results['factor'] * p_z
                            elif torsional_results['method'] == 'spectral_2_24':
                                m_t_z = q_h * torsional_results['calculation_factor'] * (z_mid / dir_params['h'])

                        print(
                            f"{wallname:<8} | "
                            f"{seg['z_start']:.2f}-{seg['z_end']:.2f}{' ' * (15 - 11)} |"
                            f"{centroid_z:<8.3f} | "
                            f"{k_z:<7.3f} | "
                            f"{kzt_z:<7.3f} |"
                            f"{q_z:<8.2f} |"
                            f"{G_factor:<7.3f} |"
                            f"{wall_cp['windward']:<7.2f} |"
                            f"{k_h:<7.3f} |"
                            f"{q_h:<7.3f} |"
                            f"{gcpi:<7.3f} |"
                            f"{p_z:<15.2f} |"
                            f"{p_l_z:<15.2f} |"
                            f"{m_t_z:<15.2f}"
                        )

                    # --- 背風牆 ---
                    for seg in leeward_segments:  # 假設背風牆總是矩形
                        wallname = seg['wallname']
                        p_h = q_h * (G_factor * wall_cp['leeward'] - gcpi)
                        z_start, z_end, centroid_z = seg['z_start'], seg['z_end'], seg['centroid_z']
                        print(
                            f"{wallname:<8} | "
                            f"{seg['z_start']:.2f}-{seg['z_end']:.2f}{' ' * (15 - 11)} |"
                            f"{centroid_z:<8.3f} | "
                            f"{'-':<7} | "
                            f"{'-':<7} |"
                            f"{'-':<8} |"
                            f"{G_factor:<7.3f} |"
                            f"{wall_cp['leeward']:<7.2f} |"
                            f"{k_h:<7.3f} |"
                            f"{q_h:<7.3f} |"
                            f"{gcpi:<7.3f} |"
                            f"{p_h:<15.2f}")

                # ===== START OF MODIFICATION =====
                # --- 側風牆/山牆 ---
                # 核心修正：處理新的 side_wall_segments 字典結構
                p_h_side = q_h * (G_factor * wall_cp['side'] - gcpi)
                # 建立一個空列表，用來收集所有側風牆的分段
                all_side_segments = []
                if 'low' in side_wall_segments and 'high' in side_wall_segments:
                    # 如果是單斜屋頂的特殊情況，將高低牆的分段都加入列表
                    all_side_segments.extend(side_wall_segments['low'])
                    all_side_segments.extend(side_wall_segments['high'])
                else:
                    # 對於所有其他情況，從 'main' 鍵取出分段列表
                    all_side_segments.extend(side_wall_segments.get('main', []))

                # 現在可以安全地遍歷這個只包含字典的列表
                for seg in all_side_segments:
                    wallname = seg['wallname']
                    z_start, z_end, centroid_z = seg['z_start'], seg['z_end'], seg['centroid_z']
                    k_h = calculate_velocity_pressure_coeff(dir_params['h'], dir_params['terrain'], db)  # 確保 k_h 有定義
                    print(
                        f"{wallname:<8} |"
                        f"{z_start:.2f}-{z_end:.2f}{' ' * (15 - 11)} |"
                        f"{centroid_z:<8.3f} | "
                        f"{'-':<7} | "
                        f"{'-':<7} |"  # Kzt_z
                        f"{'-':<8} |"  # q(z)
                        f"{G_factor:<7.3f} |"
                        f"{wall_cp['side']:<7.2f} |"
                        f"{k_h:<7.3f} |"
                        f"{q_h:<8.2f} |"
                        f"{gcpi:<7.3f} |"
                        f"{p_h_side:<15.2f}")
                # ===== END OF MODIFICATION =====

                # --- 屋頂 ---
                for name, cp in current_roof_cp.items():
                    p_roof = q_h * (G_factor * cp - gcpi)
                    print(f"{name:<12} |"
                          f"{'-':<15} |"
                          f"{dir_params['h']:<7} |"
                          f"{'-':<7} |"
                          f"{'-':<8} |"
                          f"{'-':<8} |"
                          f"{G_factor:<7.3f} |"
                          f"{cp:<7.4f} |"
                          f"{k_h:<7.3f} |"
                          f"{q_h:<8.2f} |"
                          f"{gcpi:<7.3f} |"
                          f"{p_roof:<15.2f}")

                    # 储存该方向的所有结果
                    target_key = f"{wind_dir}_dir"
                    analysis_results[target_key] = {
                        'rigidity': dir_params['building_rigidity'] + "建築物",
                        'G_factor': round(G_factor, 3),
                        'kzt': round(dir_params['Kzt'], 3),
                        'L_over_B': round(dir_params['L'] / dir_params['B'], 3) if dir_params['B'] > 0 else 0,
                        'h_over_L': round(dir_params['h'] / dir_params['L'], 3) if dir_params['L'] > 0 else 0,
                        'h_over_B': round(dir_params['h'] / dir_params['B'], 3) if dir_params['B'] > 0 else 0,
                        'wall_cp_windward': wall_cp.get('windward'),
                        'wall_cp_leeward': wall_cp.get('leeward'),
                        'wall_cp_side': wall_cp.get('side'),
                        'roof_cp': roof_cp_results  # 这是一个字典，包含屋顶所有部分的Cp值
                    }
        return {"status": "success", "analysis_type": "general", "data": analysis_results}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"計算過程中發生錯誤: {str(e)}"}


# ==============================================================================
# Phase 5: 第三章 局部构材与被覆物风压计算 (全新)
# ==============================================================================

def run_local_pressure_analysis(params: dict):
    """
    執行規範第三章，局部構材風壓計算，並返回一個包含所有表格數據的字典。
    """
    try:
        db = setup_databases()
        results = {'status': 'success', 'data': {}}

        h = params.get('h', 0)
        B_X = params.get('B_X', 0)
        B_Y = params.get('B_Y', 0)
        I = params.get('I', 1.0)
        V10_C = params.get('V10_C', 0)
        terrain = params.get('terrain', 'C')
        roof_type = params.get('roof_type')
        roof_shape_map = {'flat': '平屋頂', 'gable': '山形屋頂', 'shed': '單邊單斜式屋頂',
                          'hip': '四坡水屋頂', 'arched': '拱形屋頂', 'sawtooth_uniform': '規則鋸齒狀屋頂'}
        standard_areas_ft2 = [1, 10, 20, 50, 100, 200, 500, 1000]
        M2_PER_FT2 = 0.092903
        gcpi_values = calculate_gcpi_coeff(params.get('enclosure_status', '封閉式建築'), db)
        gcp_i_pos = max(gcpi_values) if any(v > 0 for v in gcpi_values) else 0.0
        gcp_i_neg = min(gcpi_values) if any(v < 0 for v in gcpi_values) else 0.0

        # 2. 確定分析用的參數 (風向垂直於屋脊)
        ridge_dir = params.get('ridge_orientation')
        if ridge_dir == 'X':
            B, L, wind_dir = B_Y, B_X, 'Y'
        else:
            B, L, wind_dir = B_X, B_Y, 'X'

        dir_params = params.copy()
        dir_params['B'], dir_params['L'] = B, L

        if wind_dir == 'X':
            is_topo = params.get('is_topo_site_X', False)
            if is_topo:
                dir_params.update(
                    {'landform': params.get('landform_X'), 'H': params.get('H_X', 0), 'Lh': params.get('Lh_X', 0),
                     'x': params.get('x_X', 0), 'is_topo_site': True, 'terrain': terrain})
        else:
            is_topo = params.get('is_topo_site_Y', False)
            if is_topo:
                dir_params.update(
                    {'landform': params.get('landform_Y'), 'H': params.get('H_Y', 0), 'Lh': params.get('Lh_Y', 0),
                     'x': params.get('x_Y', 0), 'is_topo_site': True, 'terrain': terrain})

        if not is_topo:
            dir_params['is_topo_site'] = False

        # 確認角度
        theta = 0
        theta_x = params.get('theta_X', 0)
        theta_y = params.get('theta_Y', 0)
        if roof_type == 'hip':
            theta = theta_x if wind_dir == 'Y' else theta_y
        else:
            theta = params.get('theta', 0)

        a_value = calculate_parameter_a(h, B, L, theta)
        kzt_at_h = calculate_topography_factor(dir_params, h, db)[0] if is_topo else 1.0
        q_h = calculate_velocity_pressure(h, I, V10_C, terrain, kzt_at_h, db)

        results['data'].update({
            'h': h, 'q_h': q_h, 'gcp_i_pos': gcp_i_pos, 'gcp_i_neg': gcp_i_neg, 'a_value': a_value,
            'is_low_rise_for_cc': h <= 18.3,
            'standard_areas': [{'ft2': ft, 'm2': ft * M2_PER_FT2} for ft in [10.0, 100.0, 500.0]]
        })

        if h <= 18.3:
            wall_rows = []
            for area_ft in standard_areas_ft2:
                gcp_w4_pos, gcp_w4_neg = calculate_gcp_walls_asce7(4, area_ft)
                gcp_w5_pos, gcp_w5_neg = calculate_gcp_walls_asce7(5, area_ft)
                if theta <= 10:
                    gcp_w4_pos *= 0.9;
                    gcp_w4_neg *= 0.9;
                    gcp_w5_pos *= 0.9;
                    gcp_w5_neg *= 0.9
                wall_rows.append({
                    'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2,
                    'p_w4_pos': q_h * (gcp_w4_pos - gcp_i_neg), 'p_w4_neg': q_h * (gcp_w4_neg - gcp_i_pos),
                    'p_w5_pos': q_h * (gcp_w5_pos - gcp_i_neg), 'p_w5_neg': q_h * (gcp_w5_neg - gcp_i_pos),
                })
            results['data']['wall_tables'] = [{'title': "外牆設計風壓 (h <= 18.3m)", 'rows': wall_rows}]

        elif h > 18.3:
            report_areas_ft2 = [10.0, 100.0, 500.0]
            # --- 情況二：高層建築 ---
            wall_pos_rows = []
            wall_top_h = params.get('ridge_height', h)

            segments = generate_rectangular_segments(base_width=1.0, top_h=wall_top_h)
            for seg in segments:
                z_mid = seg['centroid_z']
                kzt_z = calculate_topography_factor(dir_params, z_mid, db)[0] if is_topo else 1.0
                q_z = calculate_velocity_pressure(z_mid, I, V10_C, terrain, kzt_z, db)
                pressures_for_this_segment = []
                for area_ft in report_areas_ft2:
                    gcp_w4_pos, _ = calculate_gcp_walls_flatroof_hover18_asce7(4, area_ft, "walls")
                    gcp_w5_pos, _ = calculate_gcp_walls_flatroof_hover18_asce7(5, area_ft, "walls")
                    pressures_for_this_segment.append({
                        'p4_pos': q_z * (gcp_w4_pos - gcp_i_neg),
                        'p5_pos': q_z * (gcp_w5_pos - gcp_i_neg)
                    })
                wall_pos_rows.append({
                    'elevation': f"{seg['z_start']:.2f} - {seg['z_end']:.2f}",
                    'pressures_by_area': pressures_for_this_segment
                })
            results['data']['wall_tables'] = [{'title': "正風壓", 'rows': wall_pos_rows}]

            # *** 核心修正：新增高層建築負風壓表格的計算邏輯 ***
            wall_neg_rows = []
            for area_ft in report_areas_ft2:
                _, gcp_w4_neg = calculate_gcp_walls_flatroof_hover18_asce7(4, area_ft, "walls")
                _, gcp_w5_neg = calculate_gcp_walls_flatroof_hover18_asce7(5, area_ft, "walls")
                # *** 核心修正：將 area_display 拆分為 area_ft 和 area_m2 ***
                wall_neg_rows.append({
                    'area_ft': area_ft,
                    'area_m2': area_ft * M2_PER_FT2,
                    'p4_neg': q_h * (gcp_w4_neg - gcp_i_pos),
                    'p5_neg': q_h * (gcp_w5_neg - gcp_i_pos)
                })
            results['data']['wall_neg_pressure_table'] = {'rows': wall_neg_rows}
            # *** 修正結束 ***

        ## 屋頂部分：因高層建築與低矮建築部分屋頂計算外風壓是共用的，所以放在一起，不一樣的部分再來中間處理
        roof_pos_rows, roof_neg_rows = [], []
        roof_headers = []
        roof_title = "屋頂設計風壓"
        has_overhang = params.get('has_overhang', False)

        def process_roof_area(area_ft, gcp_calcs):
            pos_pressures, neg_pressures = [], []
            for calc in gcp_calcs:
                gcp_pos, gcp_neg = calc()
                pos_pressures.append({'pos': q_h * (gcp_pos - gcp_i_neg)})
                neg_pressures.append({'neg': q_h * (gcp_neg - gcp_i_pos)})
            return pos_pressures, neg_pressures

        # START: 核心修改 - 角度超限判斷與邏輯切換
        use_wall_coeffs = False
        angle_limit = 45.0

        # 判斷是否超限
        if roof_type in ['gable', 'sawtooth_uniform', 'arched']:
            if theta > 45:
                use_wall_coeffs = True
                roof_title = f"{roof_shape_map.get(roof_type)} (θ={theta:.1f}° > 45°，採用牆面係數)"
        elif roof_type == 'hip':
            if theta_x > 45 or theta_y > 45:
                use_wall_coeffs = True
                roof_title = f"四坡水屋頂 (θx={theta_x:.1f}°, θy={theta_y:.1f}° > 45°，採用牆面係數)"
        elif roof_type == 'shed':
            angle_limit = 30.0
            if theta > 30:
                use_wall_coeffs = True
                roof_title = f"單邊單斜式屋頂 (θ={theta:.1f}° > 30°，採用牆面係數)"

        # 根據是否超限，決定計算方式
        if use_wall_coeffs:
            print(f"  - (C&C Warning) Roof angle exceeds {angle_limit}°, using Wall GCp coefficients.")
            roof_headers = ["④ 區 (內區)", "⑤ 區 (邊角)"]
            for area_ft in standard_areas_ft2:
                gcp_calcs = [
                    lambda a=area_ft: calculate_gcp_walls_asce7(4, a),
                    lambda a=area_ft: calculate_gcp_walls_asce7(5, a),
                ]
                pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                roof_pos_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                roof_neg_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})
        # END: 核心修改 - 若未超限，則執行原始的屋頂計算邏輯

        else:
            if roof_type != "arched":
                if (roof_type == "flat" or
                        (roof_type == "shed" and 0 <= theta <= 3) or
                        (roof_type == "sawtooth_uniform" and 0 <= theta <= 10) or
                        (roof_type != "shed" and 0 <= theta <= 7)):  ## Figure 30.3-2A
                    if roof_type == 'flat':
                        roof_title = f"平屋頂"
                    elif roof_type == 'shed':
                        roof_title = f"Monoslop Roof (θ={theta:.2f}° <= 3°)"
                    elif roof_type == "sawtooth_uniform":
                        roof_title = f"規則鋸齒狀屋頂 (θ={theta:.2f}° <= 10°)"
                    else:
                        roof_title = f"{roof_type} (θ={theta:.2f}° <= 7°) "
                    if h <= 18.3:
                        roof_headers = ["①' 區", "① 區", "② 區", "③ 區"]
                        for area_ft in standard_areas_ft2:
                            gcp_calcs = [
                                lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, "1'", a, has_overhang),
                                lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, 1, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, 2, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, 3, a, has_overhang),
                            ]
                            pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                            roof_pos_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                            roof_neg_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

                    elif h > 18.3:
                        roof_headers = ["① 區", "② 區", "③ 區"]
                        for area_ft in standard_areas_ft2:
                            gcp_calcs = [
                                lambda a=area_ft: calculate_gcp_walls_flatroof_hover18_asce7(1, a, "flat"),
                                lambda a=area_ft: calculate_gcp_walls_flatroof_hover18_asce7(2, a, "flat"),
                                lambda a=area_ft: calculate_gcp_walls_flatroof_hover18_asce7(3, a, "flat"),
                            ]
                            pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                            roof_pos_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                            roof_neg_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

                elif roof_type == "gable":
                    roof_title = f"山形屋頂 (θ={theta:.2f}°)"
                    roof_headers = ["① 區", "② 區", "③ 區"]
                    for area_ft in standard_areas_ft2:
                        gcp_calcs = [
                            lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, 1, a, has_overhang),
                            lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, 2, a, has_overhang),
                            lambda a=area_ft: calculate_gcp_gable_roof_asce7(theta, 3, a, has_overhang),
                        ]
                        pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                        roof_pos_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                        roof_neg_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

                elif roof_type == "hip":
                    has_overhang = params.get('has_overhang', False)
                    ridge_dir = params.get('ridge_orientation')
                    if ridge_dir == "X":
                        theta = params.get('theta_Y', 0)  # X向風, 迎風屋頂斜角是 theta_Y
                        B = params.get('B_Y', 0)
                    elif ridge_dir == "Y":
                        theta = params.get('theta_X', 0)  # X向風, 迎風屋頂斜角是 theta_Y
                        B = params.get('B_X', 0)
                    h = params.get('h', 0)
                    h_over_b = h / B if B > 0 else 0
                    roof_title = f"四坡水屋頂 (θ={theta:.2f}°, h/B={h_over_b:.2f})"
                    roof_headers = ["① 區", "② 區", "③ 區"]

                    if 7 < theta <= 27 or theta == 45:
                        for area_ft in standard_areas_ft2:
                            gcp_calcs = [
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(theta, h_over_b, 1, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(theta, h_over_b, 2, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(theta, h_over_b, 3, a, has_overhang),
                            ]
                            pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                            roof_pos_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                            roof_neg_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})
                    elif 27 < theta <= 45:
                        for area_ft in standard_areas_ft2:
                            gcp_calcs_27 = [
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(27, h_over_b, 1, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(27, h_over_b, 2, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(27, h_over_b, 3, a, has_overhang),
                            ]
                            pos_p_27, neg_p_27 = process_roof_area(area_ft, gcp_calcs_27)

                            gcp_calcs_45 = [
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(45, h_over_b, 1, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(45, h_over_b, 2, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_hip_roof_asce7(45, h_over_b, 3, a, has_overhang),
                            ]
                            pos_p_45, neg_p_45 = process_roof_area(area_ft, gcp_calcs_45)

                            pos_p = (pos_p_45 - pos_p_27)(theta - 27) / (45 - 27) + pos_p_27
                            neg_p = (neg_p_45 - neg_p_27)(theta - 27) / (45 - 27) + neg_p_27
                            roof_pos_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                            roof_neg_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

                elif roof_type == 'sawtooth_uniform':
                    roof_title = f"規則鋸齒狀屋頂 (θ={theta:.2f}°)"
                    roof_headers = ["① 區", "② 區", "③ 區"]

                    for area_ft in standard_areas_ft2:
                        gcp_calcs = [
                            lambda a=area_ft: calculate_gcp_multispan_gable_roof_asce7(theta, 1, a, has_overhang),
                            lambda a=area_ft: calculate_gcp_multispan_gable_roof_asce7(theta, 2, a, has_overhang),
                            lambda a=area_ft: calculate_gcp_multispan_gable_roof_asce7(theta, 3, a, has_overhang),

                        ]
                        pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                        roof_pos_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                        roof_neg_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})


                elif roof_type == "shed":
                    has_overhang = params.get('has_overhang', False)
                    roof_title = f"Monoslope Roof (θ={theta:.2f}°)"
                    if theta > 3 and theta <= 10:
                        roof_headers = ["① 區", "② 區", "②' 區", "③ 區", "③' 區"]

                        for area_ft in standard_areas_ft2:
                            gcp_calcs = [
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, 1, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, 2, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, "2'", a, has_overhang),
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, 3, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, "3'", a, has_overhang),
                            ]
                            pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                            roof_pos_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                            roof_neg_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

                    elif theta > 10 and theta <= 30:
                        roof_headers = ["① 區", "② 區", "③ 區"]

                        for area_ft in standard_areas_ft2:
                            gcp_calcs = [
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, 1, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, 2, a, has_overhang),
                                lambda a=area_ft: calculate_gcp_shed_roof_asce7(theta, 3, a, has_overhang),
                            ]
                            pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                            roof_pos_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                            roof_neg_rows.append(
                                {'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

            elif roof_type == "arched":
                roof_title = "拱形屋頂"
                roof_headers = ["C-② 區 (周邊)", "C-③ 區 (角落)", "A 區 (內部)", "B 區 (內部)"]
                for area_ft in standard_areas_ft2:
                    gcp_calcs = [
                        lambda a=area_ft: calculate_gcp_arched_roof_asce7(params, "C-2", a, db),
                        lambda a=area_ft: calculate_gcp_arched_roof_asce7(params, "C-3", a, db),
                        lambda a=area_ft: calculate_gcp_arched_roof_asce7(params, "A", a, db),
                        lambda a=area_ft: calculate_gcp_arched_roof_asce7(params, "B", a, db),
                    ]
                    pos_p, neg_p = process_roof_area(area_ft, gcp_calcs)
                    roof_pos_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': pos_p})
                    roof_neg_rows.append({'area_ft': area_ft, 'area_m2': area_ft * M2_PER_FT2, 'pressures': neg_p})

        results['data']['roof_pos_rows'] = roof_pos_rows
        results['data']['roof_neg_rows'] = roof_neg_rows
        results['data']['roof_headers'] = roof_headers
        results['data']['roof_title'] = roof_title

        return results

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": f"局部構材計算過程中發生錯誤: {str(e)}"}


def generate_report_table_data(params: dict, db: dict, wind_dir: str, sign: str, specific_gcpi: float,
                               filter_roof_cp: bool = False):
    """
    為單一風向工況和單一 GCpi 值生成詳細的報告數據，包含壓力表和風力表。
    【核心修正】: 確保 sign 參數被傳遞給 calculate_roof_coeffs。
    """
    pressure_table_rows = []
    force_table_rows = []
    summary_data = {}

    # 1. 參數準備
    case_params = params.copy()
    landform_map_en_to_zh = {'hill': '山丘', 'ridge': '山脊', 'escarpment': '懸崖'}
    if wind_dir == 'X':
        case_params['L'], case_params['B'] = case_params['B_X'], case_params['B_Y']
        # 順風向頻率 fn, 橫風向頻率 fa, 扭轉頻率 ft
        case_params['fn'], case_params['fa'], case_params['ft'] = case_params['fn_X'], case_params['fn_Y'], params.get(
            'ft', 1.0)
    else:  # Y
        case_params['L'], case_params['B'] = case_params['B_Y'], case_params['B_X']
        case_params['fn'], case_params['fa'], case_params['ft'] = case_params['fn_Y'], case_params['fn_X'], params.get(
            'ft', 1.0)

    # 2. 地形參數準備
    topo_type = params.get(f'topo_{wind_dir.lower()}_type')
    is_topo = topo_type != 'not_considered'
    topo_calc_params = {}
    if is_topo:
        x_physical = float(params.get(f'topo_{wind_dir.lower()}_x', 0))
        topo_calc_params = {
            'H': float(params.get(f'topo_{wind_dir.lower()}_h', 0)),
            'Lh': float(params.get(f'topo_{wind_dir.lower()}_lh', 0)),
            'x': x_physical if sign == 'positive' else -x_physical,
            'terrain': case_params['terrain'],
            'landform': landform_map_en_to_zh.get(topo_type)
        }

    # 3. 計算通用參數
    rigidity = '柔性' if case_params.get('fn', 1.0) < 1.0 else '普通'
    common_gust_params = calculate_gust_common_params(case_params, db)
    if rigidity == '普通':
        G_factor = calculate_G_factor(case_params, common_gust_params)['final_value']
    elif rigidity == '柔性':
        G_factor = calculate_Gf_factor(case_params, common_gust_params, db)['final_value']
    k_h = calculate_velocity_pressure_coeff(case_params['h'], case_params['terrain'], db)
    kzt_at_h = calculate_topography_factor(topo_calc_params, case_params['h'], db)[0] if is_topo else 1.0
    q_h = calculate_velocity_pressure(case_params['h'], case_params['I'], case_params['V10_C'], case_params['terrain'],
                                      kzt_at_h, db)

    wall_cp = calculate_wall_coeffs(case_params['L'], case_params['B'], db)

    # ==== ▼▼▼ START: 【核心修正】將 sign 參數傳遞給屋頂係數計算函式 ▼▼▼ ====
    roof_cp_results = calculate_roof_coeffs(case_params, db, wind_dir, sign, filter_by_sign=filter_roof_cp)
    # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

    windward_segments, leeward_segments, side_wall_components = get_wall_segments(case_params, wind_dir)

    transverse_results = calculate_transverse_wind_force(case_params, db)
    torsional_results = calculate_torsional_moment(case_params, db)
    summary_data['B'] = case_params['B']
    summary_data['q_h'] = q_h
    summary_data['transverse_results'] = transverse_results
    summary_data['torsional_results'] = torsional_results

    # 4. 輔助函數 - 生成表格行
    def process_pressure_segment(seg, name, cp):
        p_value = 0.0
        if name.startswith('迎風牆'):
            z_mid = seg['centroid_z']
            k_z = calculate_velocity_pressure_coeff(z_mid, case_params['terrain'], db)
            kzt_z = calculate_topography_factor(topo_calc_params, z_mid, db)[0] if is_topo else 1.0
            q_z = calculate_velocity_pressure(z_mid, case_params['I'], case_params['V10_C'], case_params['terrain'],
                                              kzt_z, db)
            p_value = q_z * G_factor * cp - q_h * specific_gcpi
            pressure_table_rows.append({
                'surface': name, 'elevation': f"{seg['z_start']:.2f}-{seg['z_end']:.2f}",
                'z_bar': z_mid, 'k_z': k_z, 'kzt': kzt_z, 'q_z': q_z, 'g_factor': G_factor,
                'cp': cp, 'p': p_value
            })
        else:
            p_value = q_h * G_factor * cp - q_h * specific_gcpi
            pressure_table_rows.append({
                'surface': name, 'elevation': f"{seg['z_start']:.2f}-{seg['z_end']:.2f}",
                'z_bar': seg['centroid_z'], 'k_z': None, 'kzt': None, 'q_z': None, 'g_factor': G_factor,
                'cp': cp, 'p': p_value
            })

    # 4. 處理迎風牆 (邏輯不變)
    is_shed_perpendicular = (case_params['roof_type'] == 'shed' and wind_dir != case_params.get('ridge_orientation'))
    windward_segments_to_process = windward_segments
    if is_shed_perpendicular:
        windward_segments_to_process = windward_segments[0] if sign == 'positive' else windward_segments[1]

    for seg in windward_segments_to_process:
        z_mid = seg['centroid_z']
        k_z = calculate_velocity_pressure_coeff(z_mid, case_params['terrain'], db)
        kzt_z = calculate_topography_factor(topo_calc_params, z_mid, db)[0] if is_topo else 1.0
        q_z = calculate_velocity_pressure(z_mid, case_params['I'], case_params['V10_C'], case_params['terrain'], kzt_z,
                                          db)
        p_value = q_z * G_factor * wall_cp['windward'] - q_h * specific_gcpi
        pressure_table_rows.append({
            'surface': seg.get('wallname', '迎風牆'), 'elevation': f"{seg['z_start']:.2f}-{seg['z_end']:.2f}",
            'z_bar': z_mid, 'k_z': k_z, 'kzt': kzt_z, 'q_z': q_z, 'g_factor': G_factor,
            'cp': wall_cp['windward'], 'p': p_value
        })

    # 5. 處理背風牆 (邏輯不變)
    p_leeward = q_h * (G_factor * wall_cp['leeward'] - specific_gcpi)
    leeward_segments_to_process = leeward_segments
    if is_shed_perpendicular:
        leeward_segments_to_process = leeward_segments[0] if sign == 'positive' else leeward_segments[1]

    # 合併背風牆分段並生成表格行
    consolidated_leeward = consolidate_wall_segments(leeward_segments_to_process, case_params['eave_height'])
    for cons_seg in consolidated_leeward:
        pressure_table_rows.append({
            'surface': '背風牆', 'elevation': cons_seg['elevation'],
            'z_bar': cons_seg['z_bar'], 'k_z': None, 'kzt': None, 'q_z': None, 'g_factor': G_factor,
            'cp': wall_cp['leeward'], 'p': p_leeward
        })

    p_side = q_h * (G_factor * wall_cp['side'] - specific_gcpi)

    # 情況一：是單斜屋頂且風向平行屋脊，有高低牆之分
    if 'low' in side_wall_components and 'high' in side_wall_components:
        # 處理低側牆
        consolidated_low = consolidate_wall_segments(side_wall_components['low'], case_params['eave_height'])
        for cons_seg in consolidated_low:
            pressure_table_rows.append({
                'surface': '側風牆(低)', 'elevation': cons_seg['elevation'],
                'z_bar': cons_seg['z_bar'], 'k_z': None, 'kzt': None, 'q_z': None, 'g_factor': G_factor,
                'cp': wall_cp['side'], 'p': p_side
            })
        # 處理高側牆
        consolidated_high = consolidate_wall_segments(side_wall_components['high'], case_params['eave_height'])
        for cons_seg in consolidated_high:
            pressure_table_rows.append({
                'surface': '側風牆(高)', 'elevation': cons_seg['elevation'],
                'z_bar': cons_seg['z_bar'], 'k_z': None, 'kzt': None, 'q_z': None, 'g_factor': G_factor,
                'cp': wall_cp['side'], 'p': p_side
            })
    # 情況二：所有其他一般情況
    else:
        consolidated_side = consolidate_wall_segments(side_wall_components.get('main', []), case_params['eave_height'])
        for cons_seg in consolidated_side:
            pressure_table_rows.append({
                'surface': '側風牆', 'elevation': cons_seg['elevation'],
                'z_bar': cons_seg['z_bar'], 'k_z': None, 'kzt': None, 'q_z': None, 'g_factor': G_factor,
                'cp': wall_cp['side'], 'p': p_side
            })
    # ===== END OF MODIFICATION =====

    # ==== ▼▼▼ START: 【核心修正】在這裡篩選屋頂 Cp 值 ▼▼▼ ====
    roof_cp_to_process = roof_cp_results.copy()
    if is_shed_perpendicular:
        if sign == 'positive':  # +X 或 +Y 風，對應吹向低簷
            if '屋頂(風吹向高簷側)' in roof_cp_to_process:
                del roof_cp_to_process['屋頂(風吹向高簷側)']
        else:  # 'negative', -X 或 -Y 風，對應吹向高簷
            if '屋頂(風吹向低簷側)' in roof_cp_to_process:
                del roof_cp_to_process['屋頂(風吹向低簷側)']
    # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

    # 4. 處理屋頂壓力 (現在使用篩選後的 roof_cp_to_process)
    for name, cp in roof_cp_results.items():
        display_name = "屋頂"
        if "windward_Cp" in name:
            display_name = "迎風屋頂"
        elif "leeward_Cp" in name:
            display_name = "背風屋頂"
        elif "迎風斜面" in name:
            display_name = "迎風斜面屋頂"
        elif "背風斜面" in name:
            display_name = "背風斜面屋頂"
        elif "中央頂面" in name:
            display_name = "中央頂面屋頂"
        p_value = q_h * (G_factor * cp - specific_gcpi)
        pressure_table_rows.append(
            {'surface': display_name, 'elevation': f"{case_params['h']:.2f}", 'z_bar': None, 'k_z': None, 'kzt': None,
             'q_z': None, 'g_factor': G_factor, 'cp': cp, 'p': p_value})

    # 7. 獨立生成設計風力表格數據
    segments_for_force_calc = []
    if windward_segments and isinstance(windward_segments[0], list):
        idx = 1 if sign == 'negative' else 0
        segments_for_force_calc = windward_segments[idx]
    else:
        segments_for_force_calc = windward_segments

    for seg in segments_for_force_calc:
        z_mid, area_z = seg['centroid_z'], seg['area']
        kzt_z = calculate_topography_factor(topo_calc_params, z_mid, db)[0] if is_topo else 1.0
        q_z = calculate_velocity_pressure(z_mid, case_params['I'], case_params['V10_C'], case_params['terrain'], kzt_z,
                                          db)
        p_d_windward = q_z * G_factor * wall_cp['windward']
        p_d_leeward = q_h * G_factor * wall_cp['leeward']
        W_Dz = (p_d_windward - p_d_leeward) * area_z
        W_Lz, M_Tz = None, None
        if transverse_results:
            if transverse_results['method'] == 'simplified_2_21':
                W_Lz = transverse_results['factor'] * W_Dz
            elif transverse_results['method'] == 'spectral_2_22':
                W_Lz = (q_h * transverse_results['calculation_factor'] * (z_mid / case_params['h'])) * area_z
        if torsional_results:
            if torsional_results['method'] == 'simplified_2_23':
                M_Tz = torsional_results['factor'] * W_Dz
            elif torsional_results['method'] == 'spectral_2_24':
                M_Tz = (q_h * torsional_results['calculation_factor'] * (z_mid / case_params['h'])) * area_z
        force_table_rows.append(
            {'elevation': f"{seg['z_start']:.2f}-{seg['z_end']:.2f}", 'z_bar': z_mid, 'B': case_params['B'], 'q_z': q_z,
             'area_z': area_z, 'W_Dz': W_Dz, 'W_Lz': W_Lz, 'M_Tz': M_Tz, })

    return {'pressure_table': pressure_table_rows, 'force_table': force_table_rows, 'summary_data': summary_data}


def calculate_solid_sign_cf(params: dict, db: dict) -> dict:
    """
    根據 ASCE 7 Fig 29.3-1 (Case A, B, C) 計算實體標示物的風力係數 Cf。
    此版本已整合 Note 2 (開孔折減) 和 Case C (轉角牆折減) 的邏輯，
    並修正了 Case C 的數據查找方式，優先進行精確匹配。
    """
    try:
        print("\n--- 開始計算實體標示物 風力係數 Cf (依據 ASCE 7 Fig 29.3-1) ---")
        geo_data = params.get('geometry_data', {})
        sign_params = geo_data.get('sign', {})

        b_h = float(sign_params.get('b_h', 0))
        b_v = float(sign_params.get('b_v', 0))
        d = float(sign_params.get('d', 0))

        opening_ratio_percent = float(sign_params.get('opening_ratio', 0))
        has_corner = sign_params.get('has_corner', False)
        lr = float(sign_params.get('lr', 0))

        s = b_v
        B = b_h
        h = d + s

        if s <= 0 or B <= 0:
            print("  - 錯誤: 標示物尺寸 s 或 B 必須大於 0。")
            return None

        s_over_h = s / h if h > 0 else float('inf')
        b_over_s = B / s

        print(f"  - 輸入參數: B(寬)={B:.2f}m, s(高)={s:.2f}m, d={d:.2f}m, 開孔率={opening_ratio_percent}%")
        if has_corner:
            print(f"  - 轉角牆參數: Lr={lr:.2f}m")
        print(f"  - 計算參數: h={h:.2f}m, s/h={s_over_h:.3f}, B/s={b_over_s:.3f}")

        # --- Case A and Case B (邏輯不變) ---
        df_ab = db['SOLID_SIGN_CASE_AB_DF'].sort_index(ascending=True)
        x_points_s_h = df_ab.index.values
        y_points_b_s = df_ab.columns.values.astype(float)

        cf_values_at_target_bs = [np.interp(b_over_s, y_points_b_s, df_ab.loc[s_h_ratio].values) for s_h_ratio in
                                  x_points_s_h]
        cf_case_ab = np.interp(s_over_h, x_points_s_h, cf_values_at_target_bs)

        results = {'case_a_b_cf': cf_case_ab}
        print(f"  - ==> Case A/B (基礎 Cf): {cf_case_ab:.4f}")

        # --- Case C ---
        if b_over_s >= 2:
            print(f"  - 條件滿足 (B/s = {b_over_s:.3f} >= 2)，計算 Case C。")
            df_c = db['SOLID_SIGN_CASE_C_DF']
            reduction_df = db['SOLID_SIGN_REDUCTION_DF']
            case_c_results = {}

            # 轉角牆折減係數 (如果適用)
            corner_reduction_factor = 1.0
            if has_corner and lr > 0:
                lr_over_s = lr / s
                corner_reduction_factor = np.interp(lr_over_s, reduction_df.index.values, reduction_df.values)
                print(f"  - 計算轉角牆折減: Lr/s = {lr_over_s:.3f}, 折減係數 = {corner_reduction_factor:.3f}")

            # ==== START: 核心邏輯修正 ====
            # 步驟 1: 檢查 B/s 是否為表格中的精確索引值
            if b_over_s in df_c.index:
                print(f"  - 偵測到 B/s = {b_over_s} 為精確索引，直接查找該列。")
                # 直接選取該列，移除 NaN 值，並轉換為字典
                case_c_results = df_c.loc[b_over_s].dropna().to_dict()

                # 對查找出的結果應用折減
                for region, cf in case_c_results.items():
                    temp_cf = cf
                    if s_over_h > 0.8:
                        temp_cf *= (1.8 - s_over_h)
                    temp_cf *= corner_reduction_factor
                    case_c_results[region] = temp_cf

            # 步驟 2: 如果不是精確值，才執行原本的內插邏輯
            else:
                print(f"  - B/s = {b_over_s} 非精確索引，執行內插計算。")
                for region in df_c.columns:
                    valid_mask = ~np.isnan(df_c[region].values)
                    if not np.any(valid_mask): continue

                    x_points_bs_c_valid = df_c.index.values[valid_mask].astype(float)
                    y_points_cf_valid = df_c[region].values[valid_mask]

                    # 只有當 B/s 落在有效範圍內時才計算
                    if x_points_bs_c_valid.min() <= b_over_s <= x_points_bs_c_valid.max():
                        interp_cf_c = np.interp(b_over_s, x_points_bs_c_valid, y_points_cf_valid)

                        if s_over_h > 0.8:
                            interp_cf_c *= (1.8 - s_over_h)

                        interp_cf_c *= corner_reduction_factor

                        case_c_results[region] = interp_cf_c
            # ==== END: 核心邏輯修正 ====

            results['case_c_cfs'] = case_c_results
            print(f"  - ==> Case C (折減後各區域 Cf): {case_c_results}")

        # --- 開孔折減 (邏輯不變) ---
        opening_reduction_factor = 1.0
        if 0 < opening_ratio_percent < 30:
            solidity_ratio = 1.0 - (opening_ratio_percent / 100.0)
            opening_reduction_factor = 1 - (1 - solidity_ratio) ** 1.5
            print(f"  - 應用開孔折減: 實體率 ε={solidity_ratio:.2f}, 折減係數 = {opening_reduction_factor:.3f}")

            results['case_a_b_cf'] *= opening_reduction_factor
            if 'case_c_cfs' in results:
                for region in results['case_c_cfs']:
                    results['case_c_cfs'][region] *= opening_reduction_factor

            print(f"  - ==> 最終 Case A/B Cf (含開孔折減): {results['case_a_b_cf']:.4f}")
            if 'case_c_cfs' in results:
                print(f"  - ==> 最終 Case C Cf (含開孔折減): {results['case_c_cfs']}")

        print("--- 實體標示物 風力係數 Cf 計算結束 ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_solid_sign_force_and_cf(params: dict, db: dict) -> dict:
    """
    計算實體標示物的風力係數 Cf 和最終設計風力 F。
    【核心修正】: 在 support_force_details 中補上 gust_factor。
    """
    try:
        print("\n--- 開始計算實體標示物總風力 F ---")
        geo_data = params.get('geometry_data', {})
        sign_params = geo_data.get('sign', {})
        support_params = geo_data.get('support', {})
        general_params = params

        # 1. 獲取幾何參數
        b_h = float(sign_params.get('b_h', 0))
        b_v = float(sign_params.get('b_v', 0))
        d = float(sign_params.get('d', 0))
        As = b_h * b_v
        if As <= 0: return None

        # 2. 計算風力係數 Cf
        cf_results = calculate_solid_sign_cf(params, db)
        if not cf_results or 'case_a_b_cf' not in cf_results: return None
        cf_for_force = cf_results['case_a_b_cf']

        # 3. 計算通用參數 (G 因子 和 q(h))
        h_top = d + b_v
        params_for_g = {
            'h': h_top, 'B': b_h, 'L': 0.1, 'terrain': general_params['terrain'],
            'fn': general_params.get('fnX', 1.0),  # 標示物通常為剛性
            'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        common_gust_params = calculate_gust_common_params(params_for_g, db)
        # ==== ▼▼▼ START: 【核心修正】▼▼▼ ====
        gust_factor_details = calculate_G_factor(params_for_g, common_gust_params)
        gust_factor_value = gust_factor_details['final_value']  # 從字典中提取數值
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

        is_topo = params.get('is_topo_site', False)
        topo_params = params.get('topo_params', {})
        kzt_at_h_top = calculate_topography_factor(topo_params, h_top, db)[0] if is_topo else 1.0
        q_h_for_sign = calculate_velocity_pressure(h_top, general_params['I'], general_params['V10_C'],
                                                   general_params['terrain'], kzt_at_h_top, db)

        # print(gust_factor_value)
        # 4. 計算標示物本體風力
        # G = gust_factor['final_value']  # 陣風反應因子
        force_case_ab = q_h_for_sign * gust_factor_value * cf_for_force * As

        # 5. 計算 Case C 風力
        case_c_force_details = []
        if 'case_c_cfs' in cf_results and cf_results['case_c_cfs']:
            s = b_v
            region_map = {
                '0-s': (0, s), 's-2s': (s, 2 * s), '2s-3s': (2 * s, 3 * s),
                '3s-4s': (3 * s, 4 * s), '4s-5s': (4 * s, 5 * s), '5s-10s': (5 * s, 10 * s),
                '3s-10s': (3 * s, 10 * s), '>10s': (10 * s, b_h)
            }
            for region, cf in cf_results['case_c_cfs'].items():
                if region not in region_map: continue
                start_dist, end_dist = region_map[region]
                region_width = min(end_dist, b_h) - start_dist
                if region_width <= 0: continue
                region_area = region_width * b_v
                # G = gust_factor['final_value']  # 陣風反應因子
                G = gust_factor_value
                region_force = q_h_for_sign * G * cf * region_area
                case_c_force_details.append({'region': region, 'cf': cf, 'area': region_area, 'force': region_force})

        # 6. 計算支撐結構風力
        support_force_details = {}
        if d > 0 and support_params:
            support_cf_results = calculate_support_column_cf(params, db)
            support_h = d
            support_z_centroid = d / 2

            kzt_at_support_z = calculate_topography_factor(topo_params, support_z_centroid, db)[0] if is_topo else 1.0
            q_z_support = calculate_velocity_pressure(support_z_centroid, general_params['I'], general_params['V10_C'],
                                                      general_params['terrain'], kzt_at_support_z, db)

            if 'cf_x_wind' in support_cf_results:
                cf_x_data = support_cf_results['cf_x_wind']
                cf_x = cf_x_data['cf']
                area_x = float(support_params.get('bc_y', 0)) * support_h
                # G = gust_factor['final_value']  # 陣風反應因子
                force_x = q_z_support * G * cf_x * area_x
                # 【核心修正】: 在回傳的字典中加入 'g_factor' 和 'q_z'
                support_force_details['x_wind'] = {'cf': cf_x, 'area': area_x, 'force': force_x,
                                                   'g_factor': G, 'q_z': q_z_support}

            if 'cf_y_wind' in support_cf_results:
                cf_y_data = support_cf_results['cf_y_wind']
                cf_y = cf_y_data['cf']
                area_y = float(support_params.get('bc_x', 0)) * support_h
                # G = gust_factor['final_value']  # 陣風反應因子
                force_y = q_z_support * G * cf_y * area_y
                # 【核心修正】: 在回傳的字典中加入 'g_factor' 和 'q_z'
                support_force_details['y_wind'] = {'cf': cf_y, 'area': area_y, 'force': force_y,
                                                   'g_factor': G, 'q_z': q_z_support}

        return {
            'case_ab_force': force_case_ab, 'case_c_forces': case_c_force_details,
            'support_forces': support_force_details, 'q_h_for_sign': q_h_for_sign,
            'h_top': h_top, 'gust_factor': G,
            'area_main': As, 'cf_details': cf_results
        }
    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_chimney_cf(h, D, shape_en, roughness_en, general_params, db, h_over_d_override=None) -> float:
    """
    【核心修正】: 增加 h_over_d_override 參數以接受外部傳入的保守 h/D 值。
    """
    try:
        df = db['CHIMNEY_CF_DF']

        if D <= 0:
            return 0.0

        # ==== ▼▼▼ START: 【核心修正】優先使用 override 的 h/D ▼▼▼ ====
        h_over_d = h_over_d_override if h_over_d_override is not None else (h / D)
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

        shape_map = {'square-normal': '方形', 'square-diagonal': '方形', 'hexagonal': '六邊形或八邊形',
                     'circular': '圓形'}
        condition_map = {'square-normal': '垂直', 'square-diagonal': '對角'}
        roughness_map = {'moderate-smooth': '中度光滑', 'rough': '粗糙', 'very-rough': '極粗糙'}

        shape_zh = shape_map.get(shape_en)
        condition_zh = condition_map.get(shape_en, 'N/A')
        roughness_zh = roughness_map.get(roughness_en, '所有')

        if shape_en != 'circular':
            roughness_zh = '所有'

        if shape_en == 'circular':
            q_h = calculate_velocity_pressure(h, general_params['I'], general_params['V10_C'],
                                              general_params['terrain'], 1.0, db)
            d_sqrt_q = D * np.sqrt(q_h)
            condition_zh = '>1.70' if d_sqrt_q > 1.70 else '<=1.70'
            if condition_zh == '<=1.70':
                roughness_zh = '所有'

        selected_row = df.loc[(shape_zh, condition_zh, roughness_zh)]
        x_points = selected_row.index.astype(float)
        y_points = selected_row.values
        cf_value = np.interp(h_over_d, x_points, y_points)

        return cf_value

    except KeyError:
        print(f"  - (Cf Calc) 錯誤: 查表索引 ({shape_zh}, {condition_zh}, {roughness_zh}) 無法找到。")
        return None
    except Exception as e:
        print(f"  - (Cf Calc) 發生未知錯誤: {e}")
        return None


def calculate_chimney_force(params: dict, db: dict) -> dict:
    """
    計算煙囪的總風力，整合了自動分層計算邏輯。
    此版本已修正分層邏輯，以符合 5m 以下風壓為定值的規範。
    """
    try:
        print("\n--- 開始計算煙囪總風力 F (修正分層邏輯) ---")
        geo_data = params.get('geometry_data', {})
        general_params = params

        # 1. 獲取幾何參數
        total_h = float(geo_data.get('h', 0))
        shape_en = geo_data.get('shape')
        roughness_en = geo_data.get('roughness')
        layer_height = float(geo_data.get('layer_height', 2.0))
        d_top = float(geo_data.get('D_top', 0))
        d_bot = float(geo_data.get('D_bot', 0))
        d_sq = float(geo_data.get('D', 0))

        if total_h <= 0:
            print("  - 錯誤: 煙囪總高度為 0。")
            return None

        # 2. 進行分層計算
        total_force = 0.0
        calculation_details = []

        # ==== START: 核心修正 - 優化分層切割點 ====
        print(f"  - 煙囪自動分層 (每層約 {layer_height:.2f} m, 遵循 5m 規範):")
        cut_points = [0.0]  # 起始點永遠是 0

        # 如果總高度超過 5m，強制在 5m 處增加一個切割點
        if total_h > 5.0:
            cut_points.append(5.0)
            start_h_for_arange = 5.0
        else:
            start_h_for_arange = 0.0

        # 從 5m (或 0m) 開始，以 layer_height 為間距產生後續的切割點
        if total_h > start_h_for_arange:
            additional_cuts = np.arange(start_h_for_arange + layer_height, total_h, layer_height)
            cut_points.extend(additional_cuts.tolist())

        cut_points.append(total_h)  # 終點永遠是總高度
        cut_points = np.unique(np.array(cut_points))  # 排序並移除重複項
        # ==== END: 核心修正 ====

        for i in range(len(cut_points) - 1):
            z1, z2 = cut_points[i], cut_points[i + 1]
            h_layer = z2 - z1

            if h_layer < 1e-6: continue  # 避免因浮點數精度問題產生零高度層

            # 2a. 計算該分層的平均直徑 D 和投影面積 Af
            if shape_en == 'circular':
                d1 = np.interp(z1, [0, total_h], [d_bot, d_top])
                d2 = np.interp(z2, [0, total_h], [d_bot, d_top])
                layer_avg_d = (d1 + d2) / 2
            else:
                layer_avg_d = d_sq
                d1 = d2 = d_sq

            layer_area = layer_avg_d * h_layer

            # 2b. 計算該分層的 q(z)
            zc = (h_layer / 3) * (d1 + 2 * d2) / (d1 + d2) if (d1 + d2) > 0 else h_layer / 2
            z_eff = z1 + zc
            # 我們的 calculate_velocity_pressure 內部已經處理了 z<=5 的情況，所以直接傳入 z_eff 即可
            q_z_eff = calculate_velocity_pressure(z_eff, general_params['I'], general_params['V10_C'],
                                                  general_params['terrain'], 1.0, db)

            # 2c. 計算該分層的 Cf
            cf_layer = calculate_chimney_cf(total_h, layer_avg_d, shape_en, roughness_en, general_params, db)
            if cf_layer is None:
                raise ValueError("Cf 計算失敗，中止執行。")

            # 2d. 計算該分層的風力並加總
            layer_force = q_z_eff * cf_layer * layer_area
            total_force += layer_force

            calculation_details.append({
                'z_range': f"{z1:.2f}-{z2:.2f}", 'z_eff': z_eff,
                'q_z': q_z_eff, 'cf': cf_layer, 'area': layer_area, 'force': layer_force
            })
            print(
                f"    - 分層 {i + 1} (z={z1:.2f}-{z2:.2f}m): Cf={cf_layer:.3f}, q({z_eff:.2f}m)={q_z_eff:.2f}, Force={layer_force:.2f} kgf")

        print(f"  - ==> 加總後總風力 F = {total_force:.2f} kgf")
        print("--- 煙囪總風力 F 計算結束 ---\n")

        return {
            'total_force': total_force,
            'details': calculation_details
        }

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_shed_roof_cf(params: dict, db: dict) -> dict:
    """
    根據 表 2.9 (ASCE Shed Roof) 計算單斜式屋頂的淨壓力係數 CN。
    此函式已整合 θ < 7.5° 的規則。
    返回一個包含 gamma_0 和 gamma_180 兩種風向結果的字典。
    """
    try:
        print("\n--- 開始計算單斜式屋頂 淨壓力係數 CN (風向垂直屋脊) ---")
        df = db['SHED_ROOF_CN_DF']
        roof_params = params.get('geometry_data', {}).get('roof', {})

        theta = float(roof_params.get('theta', 0))
        blockage = roof_params.get('blockage')
        flow_condition = 'obstructed' if blockage == 'obstructed' else 'clear'

        target_theta = theta
        if theta < 7.5:
            print(f"  - 角度 θ={theta:.2f}° < 7.5°，根據規範，採用 Shed Roof θ=0° 的數據。")
            df = db['SHED_ROOF_CN_DF']
            target_theta = 0

        print(f"  - 輸入參數: θ={theta:.2f}°, 氣流條件='{flow_condition}'")
        print(f"  - 最終用於內插的角度: {target_theta:.2f}°")

        thetas = df.index.get_level_values('theta').unique().values
        theta2_idx = np.searchsorted(thetas, target_theta)
        theta1_idx = max(0, theta2_idx - 1)
        if target_theta >= thetas[-1]: theta1_idx = theta2_idx = len(thetas) - 1

        theta1, theta2 = thetas[theta1_idx], thetas[theta2_idx]

        results = {}
        for wind_dir in ['gamma_0', 'gamma_180']:
            result_key = wind_dir
            results[result_key] = {}
            for case in ['A', 'B']:
                for coeff_type in ['C_NW', 'C_NL']:
                    col_key = (wind_dir, flow_condition, coeff_type)
                    val1 = df.loc[(theta1, case), col_key]
                    val2 = df.loc[(theta2, case), col_key]
                    interp_val = np.interp(target_theta, [theta1, theta2], [val1, val2]) if theta1 != theta2 else val1
                    result_subkey = f"{coeff_type.replace('_', '').lower()}_{case.lower()}"
                    results[result_key][result_subkey] = interp_val

        print(f"  - ==> 計算結果: {results}")
        print("--- 單斜式屋頂 CN 計算結束 ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


# ===== START OF MODIFICATION: 新增缺失的函式 =====
def calculate_pitched_roof_cf(params: dict, db: dict) -> dict:
    """
    根據 ASCE Fig 27.4-5 (Pitched Roof) 計算淨壓力係數 CN。
    此函式已整合 θ < 7.5° 的規則。
    """
    try:
        print("\n--- 開始計算 Pitched Roof 淨壓力係數 CN (風向垂直屋脊) ---")
        roof_params = params.get('geometry_data', {}).get('roof', {})
        theta = float(roof_params.get('theta', 0))
        blockage = roof_params.get('blockage')
        flow_condition = 'obstructed' if blockage == 'obstructed' else 'clear'

        df = db['PITCHED_ROOF_CN_DF']
        print(f"  - 輸入參數: θ={theta:.2f}°, 氣流條件='{flow_condition}'")
        thetas = df.index.get_level_values('theta').unique().values
        target_theta = theta
        theta2_idx = np.searchsorted(thetas, target_theta)
        theta1_idx = max(0, theta2_idx - 1)
        if target_theta >= thetas[-1]: theta1_idx = theta2_idx = len(thetas) - 1
        theta1, theta2 = thetas[theta1_idx], thetas[theta2_idx]

        results = {'gamma_na': {}}
        for case in ['A', 'B']:
            for coeff_type in ['C_NW', 'C_NL']:
                col_key = (flow_condition, coeff_type)
                val1 = df.loc[(theta1, case), col_key]
                val2 = df.loc[(theta2, case), col_key]
                interp_val = np.interp(target_theta, [theta1, theta2], [val1, val2]) if theta1 != theta2 else val1
                result_subkey = f"{coeff_type.replace('_', '').lower()}_{case.lower()}"
                results['gamma_na'][result_subkey] = interp_val

        print(f"  - ==> 計算結果: {results}")
        print("--- Pitched Roof CN 計算結束 ---\n")
        return results
    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_troughed_roof_cf(params: dict, db: dict) -> dict:
    """
    根據 ASCE Fig 27.4-6 (Troughed Roof) 計算淨壓力係數 CN。
    此函式已整合 θ < 7.5° 的規則。
    """
    try:
        print("\n--- 開始計算 Troughed Roof 淨壓力係數 CN (風向垂直屋脊) ---")
        roof_params = params.get('geometry_data', {}).get('roof', {})

        theta = float(roof_params.get('theta', 0))
        blockage = roof_params.get('blockage')
        flow_condition = 'obstructed' if blockage == 'obstructed' else 'clear'

        df = db['THROUGHED_ROOF_CN_DF']
        print(f"  - 輸入參數: θ={theta:.2f}°, 氣流條件='{flow_condition}'")

        thetas = df.index.get_level_values('theta').unique().values

        target_theta = theta
        theta2_idx = np.searchsorted(thetas, target_theta)
        theta1_idx = max(0, theta2_idx - 1)
        if target_theta >= thetas[-1]: theta1_idx = theta2_idx = len(thetas) - 1

        theta1, theta2 = thetas[theta1_idx], thetas[theta2_idx]

        results = {}
        result_key = 'gamma_na'
        results[result_key] = {}

        for case in ['A', 'B']:
            for coeff_type in ['C_NW', 'C_NL']:
                col_key = (flow_condition, coeff_type)

                val1 = df.loc[(theta1, case), col_key]
                val2 = df.loc[(theta2, case), col_key]

                interp_val = np.interp(target_theta, [theta1, theta2], [val1, val2]) if theta1 != theta2 else val1

                result_subkey = f"{coeff_type.replace('_', '').lower()}_{case.lower()}"
                results[result_key][result_subkey] = interp_val

        print(f"  - ==> 計算結果: {results}")
        print("--- Troughed Roof CN 計算結束 ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


# wind_calculations.py

def calculate_support_column_cf(params: dict, db: dict) -> dict:
    """
    【已重構】根據煙囪規範 (ASCE Fig 29.4-1)，計算支撐結構的風力係數 Cf。
    【核心修正】: 返回更多計算細節，包括 h/D, D_conservative, R_conservative 等。
    """
    try:
        print("\n--- 開始計算支撐構材 風力係數 Cf (依據煙囪規範) ---")
        support_params = params.get('geometry_data', {}).get('support', {})
        general_params = params

        h = float(support_params.get('h', 0))
        shape_ui = support_params.get('shape')

        params_for_cf_calc = {
            'I': general_params['I'],
            'V10_C': general_params['V10_C'],
            'terrain': general_params['terrain']
        }

        shape_en_for_lookup = 'square-normal'
        roughness_en_for_lookup = 'moderate-smooth'
        if shape_ui == 'rectangular-column':
            shape_en_for_lookup = 'square-normal'
            roughness_en_for_lookup = 'All'
        elif shape_ui == 'circular':
            shape_en_for_lookup = 'circular'
        elif shape_ui == 'hexagonal':
            shape_en_for_lookup = 'hexagonal'
            roughness_en_for_lookup = 'All'

        d_top_x = float(support_params.get('dtop_x', 0));
        d_bot_x = float(support_params.get('dbot_x', 0))
        d_top_y = float(support_params.get('dtop_y', 0));
        d_bot_y = float(support_params.get('dbot_y', 0))
        avg_dx = (d_top_x + d_bot_x) / 2
        avg_dy = (d_top_y + d_bot_y) / 2

        # ==== ▼▼▼ START: 【核心修正】準備更多要返回的詳細參數 ▼▼▼ ====
        D_conservative = min(avg_dx, avg_dy) if min(avg_dx, avg_dy) > 0 else max(avg_dx, avg_dy)
        h_over_d_conservative = h / D_conservative if D_conservative > 0 else float('inf')

        # 煙囪的 R 因子不存在，這裡的 h/D 是為了查表，不是為了 R 因子
        # 為了避免混淆，我們不再計算和返回 R_conservative

        cf_y = 0
        if avg_dx > 0:
            # 傳遞 h_over_d 給底層函式，讓它使用這個保守值（雖然煙囪 Cf 是直接內插）
            cf_y = calculate_chimney_cf(h, avg_dx, shape_en_for_lookup, roughness_en_for_lookup, params_for_cf_calc, db,
                                        h_over_d_override=h_over_d_conservative)

        cf_x = 0
        if avg_dy > 0:
            cf_x = calculate_chimney_cf(h, avg_dy, shape_en_for_lookup, roughness_en_for_lookup, params_for_cf_calc, db,
                                        h_over_d_override=h_over_d_conservative)

        cf_x = cf_x or 0
        cf_y = cf_y or 0
        cf_conservative = max(cf_x, cf_y)

        print(f"    - Cf (X向風, 作用於 Y-Z 平面, D={avg_dy:.2f}m): {cf_x:.4f}")
        print(f"    - Cf (Y向風, 作用於 X-Z 平面, D={avg_dx:.2f}m): {cf_y:.4f}")
        print(f"    - ==> 保守 Cf_support: {cf_conservative:.4f} (使用 h/D = {h_over_d_conservative:.3f})")

        return {
            'cf_x': cf_x,
            'cf_y': cf_y,
            'cf_conservative': cf_conservative,
            'B_x': avg_dx,
            'B_y': avg_dy,
            'D_conservative': D_conservative,
            'h_over_d_conservative': h_over_d_conservative,
            'h_support': h
        }
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return {}


def calculate_support_force_generic(params: dict, db: dict) -> dict:
    """
    一個通用的函式，用於計算各種開放式結構的【支撐結構】風力。
    """
    support_force_results = {}
    general_params = params
    support_params = params.get('geometry_data', {}).get('support', {})

    fn_X = float(general_params.get('fnX', 1.0))
    fn_Y = float(general_params.get('fnY', 1.0))

    support_h = float(support_params.get('h', 0))
    if support_h <= 0:
        return None  # 如果沒有支撐高度，直接返回

    support_cf_data = calculate_support_column_cf(params, db)

    support_z_centroid = support_h / 2
    q_z_support = calculate_velocity_pressure(
        support_z_centroid, general_params['I'], general_params['V10_C'],
        general_params['terrain'], 1.0, db
    )

    for wind_dir_key, cf_info in support_cf_data.items():
        fn_support = fn_X if 'x_wind' in wind_dir_key else fn_Y
        rigidity_support = '柔性' if fn_support < 1.0 else '普通'

        params_for_support_g = {
            'h': support_h, 'B': cf_info['B'], 'L': cf_info['L'],
            'terrain': general_params['terrain'], 'fn': fn_support,
            'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        support_common_gust = calculate_gust_common_params(params_for_support_g, db)

        support_g = calculate_Gf_factor(params_for_support_g, support_common_gust,
                                        db) if rigidity_support == '柔性' else calculate_G_factor(params_for_support_g,
                                                                                                  support_common_gust)

        area = cf_info['B'] * support_h
        G = support_g['final_value']
        force = q_z_support * G * cf_info['cf'] * area

        support_force_results[wind_dir_key] = {
            'cf': cf_info['cf'], 'g_factor': G, 'q_z': q_z_support,
            'area': area, 'force': force, 'rigidity': rigidity_support
        }

    return support_force_results


def run_shed_roof_analysis(params: dict, db: dict):
    """
    專門處理單斜式屋頂建築物的計算，包含屋頂淨風壓 p 和支撐結構風力 F。
    【核心修正】: 1. 新增角度 > 45° 的處理邏輯。 2. 修正 support_force_results 的回傳。
    """
    try:
        results = {}
        general_params = params
        roof_params = params.get('geometry_data', {}).get('roof', {})
        support_params = params.get('geometry_data', {}).get('support', {})
        theta = float(roof_params.get('theta', 0))
        wind_dir = params.get('wind_direction')  # 接收指定的風向

        # =======================================================
        # START: 核心修正 ① - 角度超限處理
        # =======================================================
        if theta > 45:
            print(f"  - 警告: 屋頂角度 θ={theta:.2f}° > 45°，將採用實體招牌模型計算總風力。")

            # 1. 參數轉換
            b_x = float(roof_params.get('b_x', 0))
            b_y = float(roof_params.get('b_y', 0))
            h_eave = float(roof_params.get('h_eave', 0))
            ridge_dir = roof_params.get('ridge_direction')

            sign_params_for_calc = params.copy()
            sign_params_for_calc['geometry_data'] = {
                'sign': {
                    'b_h': b_x if ridge_dir == 'X' else b_y,  # 招牌寬度 = 屋頂長度
                    'b_v': (b_y if ridge_dir == 'X' else b_x) * np.sin(np.deg2rad(theta)),  # 招牌高度 = 投影高
                    'd': h_eave,
                    'opening_ratio': 0,
                    'has_corner': False,
                    'lr': 0
                },
                'support': {}  # 主結構計算時，暫不考慮支撐
            }

            # 2. 呼叫實體招牌計算函式 (假設X向風)
            # 注意：這裡只為了得到一個主風力，風向主要影響G因子，對Cf影響不大，故簡化
            sign_params_for_calc['is_topo_site'] = params.get('is_topo_site_X', False)
            sign_params_for_calc['topo_params'] = params.get('topo_params', {}) if params.get('is_topo_site_X') else {}

            force_results = calculate_solid_sign_force_and_cf(sign_params_for_calc, db)

            if force_results:
                results['solid_sign_method_results'] = {
                    'is_solid_sign_method': True,
                    'message': f"屋頂角度 {theta:.1f}° > 45°，採用實體招牌模型計算。",
                    'cf': force_results.get('cf_details', {}).get('case_a_b_cf', 0),
                    'total_force': force_results.get('case_ab_force', 0),
                    'gust_factor': force_results.get('gust_factor', 0),
                    'q_h_for_sign': force_results.get('q_h_for_sign', 0)
                }

            # 3. 支撐結構計算 (保持不變)
            support_h = float(support_params.get('h', 0))
            if support_h > 0:
                results['support_force_results'] = calculate_support_force_generic(params, db)

            return results
        # =======================================================
        # END: 核心修正 ①
        # =======================================================

        # --- 如果角度未超限，執行 CN 計算邏輯 ---
        ridge_dir = roof_params.get('ridge_direction')
        b_x = float(roof_params.get('b_x', 0))
        b_y = float(roof_params.get('b_y', 0))
        is_parallel_wind = (wind_dir == ridge_dir)

        if wind_dir == 'X':
            L = b_x
            B = b_y
            fn = params.get('fnX')
        else:  # wind_dir == 'Y'
            L = b_y
            B = b_x
            fn = params.get('fnY')

        rigidity = '柔性' if fn < 1.0 else '普通'

        params_for_g = {'h': params['h'], 'B': B, 'L': L, 'terrain': general_params['terrain'], 'fn': fn,
                        'beta': float(general_params.get('dampingRatio', 0.01)), 'V10_C': general_params['V10_C'],
                        'I': general_params['I']}

        common_gust = calculate_gust_common_params(params_for_g, db)

        # ==== ▼▼▼ START: 核心修正 - 正確處理 G/Gf 字典 ▼▼▼ ====
        g_factor_details = calculate_Gf_factor(params_for_g, common_gust,
                                               db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                                 common_gust)
        gust_factor = g_factor_details['final_value']

        # 將詳細的 G/Gf 字典直接放入 results 中，供附錄使用
        results['g_factor_details'] = g_factor_details
        # ==== ▲▲▲ END: 核心修正 ▲▲▲ ====

        # 地形參數應由上層 run_open_building_analysis 傳入
        is_topo = params.get('is_topo_site', False)
        topo_params = params.get('topo_params', {})
        kzt_at_h = calculate_topography_factor(topo_params, params['h'], db)[0] if is_topo else 1.0
        q_h = calculate_velocity_pressure(params['h'], general_params['I'], general_params['V10_C'],
                                          general_params['terrain'], kzt_at_h, db)
        results['main_params'] = {'q_h': q_h, 'gust_factor': gust_factor, 'rigidity': rigidity, 'B': B, 'L': L}

        cn_results = {}
        if is_parallel_wind:
            cn_results = calculate_parallel_wind_cn(params, db)
            results['wind_case'] = 'parallel'
        else:
            h_over_l = params['h'] / L if L > 0 else 0
            if 0.05 <= h_over_l < 0.25 and theta < 5:
                cn_results = calculate_parallel_wind_cn(params, db)
                results['wind_case'] = 'perpendicular_note4'
            else:
                cn_results = calculate_shed_roof_cf(params, db)
                results['wind_case'] = 'perpendicular'
        results['cn_results'] = cn_results

        # ==== ▼▼▼ START: 新增設計風壓 p 的後處理計算 ▼▼▼ ====
        pressures = {}
        if results['wind_case'] in ['parallel', 'perpendicular_note4']:
            pressures['zones'] = {}
            for key, val in cn_results.items():
                pressures['zones'][key] = {
                    'p_a': val['cn_a'] * q_h * gust_factor,
                    'p_b': val['cn_b'] * q_h * gust_factor,
                }
        elif results['wind_case'] == 'perpendicular':
            if cn_results.get('gamma_0'):
                pressures['gamma_0'] = {'pnw_a': cn_results['gamma_0']['cnw_a'] * q_h * gust_factor,
                                        'pnw_b': cn_results['gamma_0']['cnw_b'] * q_h * gust_factor,
                                        'pnl_a': cn_results['gamma_0']['cnl_a'] * q_h * gust_factor,
                                        'pnl_b': cn_results['gamma_0']['cnl_b'] * q_h * gust_factor}
                pressures['gamma_180'] = {'pnw_a': cn_results['gamma_180']['cnw_a'] * q_h * gust_factor,
                                          'pnw_b': cn_results['gamma_180']['cnw_b'] * q_h * gust_factor,
                                          'pnl_a': cn_results['gamma_180']['cnl_a'] * q_h * gust_factor,
                                          'pnl_b': cn_results['gamma_180']['cnl_b'] * q_h * gust_factor}
            elif cn_results.get('gamma_na'):
                pressures['gamma_na'] = {'pnw_a': cn_results['gamma_na']['cnw_a'] * q_h * gust_factor,
                                         'pnw_b': cn_results['gamma_na']['cnw_b'] * q_h * gust_factor,
                                         'pnl_a': cn_results['gamma_na']['cnl_a'] * q_h * gust_factor,
                                         'pnl_b': cn_results['gamma_na']['cnl_b'] * q_h * gust_factor}
        results['pressures'] = pressures
        # ==== ▲▲▲ END: 新增設計風壓 p 的後處理計算 ▲▲▲ ====

        support_h = float(support_params.get('h', 0))
        if support_h > 0:
            results['support_force_results'] = calculate_support_force_generic(params, db)

        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def run_pitched_roof_analysis(params: dict, db: dict):
    """
    專門處理 Pitched Free Roofs 的計算，包含屋頂淨風壓 p 和支撐結構風力 F。
    【核心修正】: 1. 新增角度 > 45° 的處理邏輯。 2. 修正 support_force_results 的回傳。
    """
    try:
        results = {}
        general_params = params
        roof_params = params.get('geometry_data', {}).get('roof', {})
        support_params = params.get('geometry_data', {}).get('support', {})
        theta = float(roof_params.get('theta', 0))
        wind_dir = params.get('wind_direction')

        # =======================================================
        # START: 核心修正 ① - 角度超限處理
        # =======================================================
        if theta > 45:
            print(f"  - 警告: 屋頂角度 θ={theta:.2f}° > 45°，將採用實體招牌模型計算總風力。")

            b_x = float(roof_params.get('b_x', 0))
            b_y = float(roof_params.get('b_y', 0))
            h_eave = float(roof_params.get('h_eave', 0))
            ridge_dir = roof_params.get('ridge_direction')

            sign_params_for_calc = params.copy()
            sign_params_for_calc['geometry_data'] = {
                'sign': {
                    'b_h': b_x if ridge_dir == 'X' else b_y,
                    'b_v': (b_y if ridge_dir == 'X' else b_x) * np.sin(np.deg2rad(theta)),
                    'd': h_eave, 'opening_ratio': 0, 'has_corner': False, 'lr': 0
                }, 'support': {}
            }

            sign_params_for_calc['is_topo_site'] = params.get('is_topo_site_X', False)
            sign_params_for_calc['topo_params'] = params.get('topo_params', {}) if params.get('is_topo_site_X') else {}

            force_results = calculate_solid_sign_force_and_cf(sign_params_for_calc, db)

            if force_results:
                results['solid_sign_method_results'] = {
                    'is_solid_sign_method': True,
                    'message': f"屋頂角度 {theta:.1f}° > 45°，採用實體招牌模型計算。",
                    'cf': force_results.get('cf_details', {}).get('case_a_b_cf', 0),
                    'total_force': force_results.get('case_ab_force', 0),
                    'gust_factor': force_results.get('gust_factor', 0),
                    'q_h_for_sign': force_results.get('q_h_for_sign', 0)
                }

            support_h = float(support_params.get('h', 0))
            if support_h > 0:
                results['support_force_results'] = calculate_support_force_generic(params, db)

            return results
        # =======================================================
        # END: 核心修正 ①
        # =======================================================
        # --- 如果角度未超限，執行 CN 計算邏輯 ---
        ridge_dir = roof_params.get('ridge_direction')
        b_x = float(roof_params.get('b_x', 0));
        b_y = float(roof_params.get('b_y', 0))
        is_parallel_wind = (wind_dir == ridge_dir)

        if wind_dir == 'X':
            L = b_x
            B = b_y
            fn = params.get('fnX')
        else:  # wind_dir == 'Y'
            L = b_y
            B = b_x
            fn = params.get('fnY')

        rigidity = '柔性' if fn < 1.0 else '普通'

        params_for_g = {'h': params['h'], 'B': B, 'L': L, 'terrain': general_params['terrain'], 'fn': fn,
                        'beta': float(general_params.get('dampingRatio', 0.01)), 'V10_C': general_params['V10_C'],
                        'I': general_params['I']}

        common_gust = calculate_gust_common_params(params_for_g, db)

        # ==== ▼▼▼ START: 核心修正 - 正確處理 G/Gf 字典 ▼▼▼ ====
        g_factor_details = calculate_Gf_factor(params_for_g, common_gust,
                                               db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                                 common_gust)
        gust_factor = g_factor_details['final_value']

        # 將詳細的 G/Gf 字典直接放入 results 中，供附錄使用
        results['g_factor_details'] = g_factor_details
        # ==== ▲▲▲ END: 核心修正 ▲▲▲ ====

        is_topo = params.get('is_topo_site', False)
        topo_params = params.get('topo_params', {})
        kzt_at_h = calculate_topography_factor(topo_params, params['h'], db)[0] if is_topo else 1.0
        q_h = calculate_velocity_pressure(params['h'], general_params['I'], general_params['V10_C'],
                                          general_params['terrain'], kzt_at_h, db)

        results['main_params'] = {'q_h': q_h, 'gust_factor': gust_factor, 'rigidity': rigidity, 'B': B, 'L': L}

        cn_results = {}
        if is_parallel_wind:
            cn_results = calculate_parallel_wind_cn(params, db)
            results['wind_case'] = 'parallel'
        else:  # 垂直風
            # ▼▼▼ START: 修正此區塊 ▼▼▼
            cn_results = calculate_pitched_roof_cf(params, db)
            results['wind_case'] = 'perpendicular'
        results['cn_results'] = cn_results

        # ==== ▼▼▼ START: 新增設計風壓 p 的後處理計算 ▼▼▼ ====
        pressures = {}
        if results['wind_case'] in ['parallel', 'perpendicular_note4']:
            pressures['zones'] = {}
            for key, val in cn_results.items():
                pressures['zones'][key] = {
                    'p_a': val['cn_a'] * q_h * gust_factor,
                    'p_b': val['cn_b'] * q_h * gust_factor,
                }
        elif results['wind_case'] == 'perpendicular':
            if cn_results.get('gamma_0'):
                pressures['gamma_0'] = {'pnw_a': cn_results['gamma_0']['cnw_a'] * q_h * gust_factor,
                                        'pnw_b': cn_results['gamma_0']['cnw_b'] * q_h * gust_factor,
                                        'pnl_a': cn_results['gamma_0']['cnl_a'] * q_h * gust_factor,
                                        'pnl_b': cn_results['gamma_0']['cnl_b'] * q_h * gust_factor}
                pressures['gamma_180'] = {'pnw_a': cn_results['gamma_180']['cnw_a'] * q_h * gust_factor,
                                          'pnw_b': cn_results['gamma_180']['cnw_b'] * q_h * gust_factor,
                                          'pnl_a': cn_results['gamma_180']['cnl_a'] * q_h * gust_factor,
                                          'pnl_b': cn_results['gamma_180']['cnl_b'] * q_h * gust_factor}
            elif cn_results.get('gamma_na'):
                pressures['gamma_na'] = {'pnw_a': cn_results['gamma_na']['cnw_a'] * q_h * gust_factor,
                                         'pnw_b': cn_results['gamma_na']['cnw_b'] * q_h * gust_factor,
                                         'pnl_a': cn_results['gamma_na']['cnl_a'] * q_h * gust_factor,
                                         'pnl_b': cn_results['gamma_na']['cnl_b'] * q_h * gust_factor}
        results['pressures'] = pressures
        # ==== ▲▲▲ END: 新增設計風壓 p 的後處理計算 ▲▲▲ ====

        support_h = float(support_params.get('h', 0))
        if support_h > 0:
            results['support_force_results'] = calculate_support_force_generic(params, db)

        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def run_troughed_roof_analysis(params: dict, db: dict):
    """
    專門處理 Troughed Free Roofs 的計算。
    【核心修正】: 1. 新增角度 > 45° 的處理邏輯。 2. 修正 support_force_results 的回傳。
    """
    try:
        results = {}
        general_params = params
        roof_params = params.get('geometry_data', {}).get('roof', {})
        support_params = params.get('geometry_data', {}).get('support', {})
        theta = float(roof_params.get('theta', 0))
        wind_dir = params.get('wind_direction')

        # =======================================================
        # START: 核心修正 ① - 角度超限處理
        # =======================================================
        if theta > 45:
            print(f"  - 警告: 屋頂角度 θ={theta:.2f}° > 45°，將採用實體招牌模型計算總風力。")

            b_x = float(roof_params.get('b_x', 0))
            b_y = float(roof_params.get('b_y', 0))
            h_eave = float(roof_params.get('h_eave', 0))
            ridge_dir = roof_params.get('ridge_direction')

            sign_params_for_calc = params.copy()
            sign_params_for_calc['geometry_data'] = {
                'sign': {
                    'b_h': b_x if ridge_dir == 'X' else b_y,
                    'b_v': (b_y if ridge_dir == 'X' else b_x) * np.sin(np.deg2rad(theta)),
                    'd': h_eave, 'opening_ratio': 0, 'has_corner': False, 'lr': 0
                }, 'support': {}
            }

            sign_params_for_calc['is_topo_site'] = params.get('is_topo_site_X', False)
            sign_params_for_calc['topo_params'] = params.get('topo_params', {}) if params.get('is_topo_site_X') else {}

            force_results = calculate_solid_sign_force_and_cf(sign_params_for_calc, db)

            if force_results:
                results['solid_sign_method_results'] = {
                    'is_solid_sign_method': True,
                    'message': f"屋頂角度 {theta:.1f}° > 45°，採用實體招牌模型計算。",
                    'cf': force_results.get('cf_details', {}).get('case_a_b_cf', 0),
                    'total_force': force_results.get('case_ab_force', 0),
                    'gust_factor': force_results.get('gust_factor', 0),
                    'q_h_for_sign': force_results.get('q_h_for_sign', 0)
                }

            support_h = float(support_params.get('h', 0))
            if support_h > 0:
                results['support_force_results'] = calculate_support_force_generic(params, db)

            return results
        # =======================================================
        # END: 核心修正 ①
        # =======================================================

        # --- 如果角度未超限，執行 CN 計算邏輯 ---
        ridge_dir = roof_params.get('ridge_direction')
        b_x = float(roof_params.get('b_x', 0));
        b_y = float(roof_params.get('b_y', 0))
        is_parallel_wind = (wind_dir == ridge_dir)

        if wind_dir == 'X':
            L = b_x
            B = b_y
            fn = params.get('fnX')
        else:  # wind_dir == 'Y'
            L = b_y
            B = b_x
            fn = params.get('fnY')

        rigidity = '柔性' if fn < 1.0 else '普通'

        params_for_g = {'h': params['h'], 'B': B, 'L': L, 'terrain': general_params['terrain'], 'fn': fn,
                        'beta': float(general_params.get('dampingRatio', 0.01)), 'V10_C': general_params['V10_C'],
                        'I': general_params['I']}

        common_gust = calculate_gust_common_params(params_for_g, db)

        # ==== ▼▼▼ START: 核心修正 - 正確處理 G/Gf 字典 ▼▼▼ ====
        g_factor_details = calculate_Gf_factor(params_for_g, common_gust,
                                               db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                                 common_gust)
        gust_factor = g_factor_details['final_value']

        # 將詳細的 G/Gf 字典直接放入 results 中，供附錄使用
        results['g_factor_details'] = g_factor_details
        # ==== ▲▲▲ END: 核心修正 ▲▲▲ ====

        is_topo = params.get('is_topo_site', False)
        topo_params = params.get('topo_params', {})
        kzt_at_h = calculate_topography_factor(topo_params, params['h'], db)[0] if is_topo else 1.0
        q_h = calculate_velocity_pressure(params['h'], general_params['I'], general_params['V10_C'],
                                          general_params['terrain'], kzt_at_h, db)

        results['main_params'] = {'q_h': q_h, 'gust_factor': gust_factor, 'rigidity': rigidity, 'B': B, 'L': L}

        cn_results = {}
        if is_parallel_wind:
            cn_results = calculate_parallel_wind_cn(params, db)
            results['wind_case'] = 'parallel'
        else:  # 垂直風
            # ▼▼▼ START: 修正此區塊 ▼▼▼
            cn_results = calculate_troughed_roof_cf(params, db)
            results['wind_case'] = 'perpendicular'
        results['cn_results'] = cn_results

        # ==== ▼▼▼ START: 新增設計風壓 p 的後處理計算 ▼▼▼ ====
        pressures = {}
        if results['wind_case'] in ['parallel', 'perpendicular_note4']:
            pressures['zones'] = {}
            for key, val in cn_results.items():
                pressures['zones'][key] = {
                    'p_a': val['cn_a'] * q_h * gust_factor,
                    'p_b': val['cn_b'] * q_h * gust_factor,
                }
        elif results['wind_case'] == 'perpendicular':
            print("我可以幹秋梅100次")
            if cn_results.get('gamma_0'):
                pressures['gamma_0'] = {'pnw_a': cn_results['gamma_0']['cnw_a'] * q_h * gust_factor,
                                        'pnw_b': cn_results['gamma_0']['cnw_b'] * q_h * gust_factor,
                                        'pnl_a': cn_results['gamma_0']['cnl_a'] * q_h * gust_factor,
                                        'pnl_b': cn_results['gamma_0']['cnl_b'] * q_h * gust_factor}
                pressures['gamma_180'] = {'pnw_a': cn_results['gamma_180']['cnw_a'] * q_h * gust_factor,
                                          'pnw_b': cn_results['gamma_180']['cnw_b'] * q_h * gust_factor,
                                          'pnl_a': cn_results['gamma_180']['cnl_a'] * q_h * gust_factor,
                                          'pnl_b': cn_results['gamma_180']['cnl_b'] * q_h * gust_factor}
            elif cn_results.get('gamma_na'):
                pressures['gamma_na'] = {'pnw_a': cn_results['gamma_na']['cnw_a'] * q_h * gust_factor,
                                         'pnw_b': cn_results['gamma_na']['cnw_b'] * q_h * gust_factor,
                                         'pnl_a': cn_results['gamma_na']['cnl_a'] * q_h * gust_factor,
                                         'pnl_b': cn_results['gamma_na']['cnl_b'] * q_h * gust_factor}
        results['pressures'] = pressures
        # ==== ▲▲▲ END: 新增設計風壓 p 的後處理計算 ▲▲▲ ====

        support_h = float(support_params.get('h', 0))
        if support_h > 0:
            results['support_force_results'] = calculate_support_force_generic(params, db)

        return results


    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


# ==============================================================================
# ==== 【新增】: C&C 計算專用函式
# ==============================================================================
def calculate_parameter_a_for_cc(h: float, b_x: float, b_y: float):
    """
    依據 ASCE 7-16 FIGURE 30.7-1 的註記，計算 C&C 區域劃分寬度 'a'。
    """
    least_horizontal_dim = min(b_x, b_y)

    val1 = 0.1 * least_horizontal_dim
    val2 = 0.4 * h
    a_intermediate = min(val1, val2)

    lower_bound = max(0.04 * least_horizontal_dim, 0.9)  # 0.9m ~= 3ft

    a_final = max(a_intermediate, lower_bound)
    return a_final


def calculate_monoslope_cc_cn(theta, effective_area_A, a, flow_condition, zone, db):
    """
    從資料庫中查找並內插 Monoslope Roof 的 C&C 淨壓力係數 CN。
    """
    df = db['MONOSLOPE_CC_CN_DF']

    # 1. 確定面積條件
    if effective_area_A <= a ** 2:
        area_cond = '<=a^2'
    elif a ** 2 < effective_area_A <= 4 * a ** 2:
        area_cond = '>a^2, <=4a^2'
    else:  # > 4 * a**2
        area_cond = '>4a^2'

    # 2. 準備內插
    thetas = df.index.get_level_values('theta').unique().sort_values()

    # 找到夾住目標 theta 的兩個角度
    theta_upper_idx = np.searchsorted(thetas, theta)
    theta_lower_idx = max(0, theta_upper_idx - 1)
    # 處理邊界情況
    if theta_upper_idx >= len(thetas):
        theta_upper_idx = theta_lower_idx = len(thetas) - 1

    theta1, theta2 = thetas[theta_lower_idx], thetas[theta_upper_idx]

    # 3. 提取對應的 CN 值
    cn_pos_col, cn_neg_col = f'Z{zone}+', f'Z{zone}-'

    val1_pos = df.loc[(flow_condition, theta1, area_cond), cn_pos_col]
    val1_neg = df.loc[(flow_condition, theta1, area_cond), cn_neg_col]

    if theta1 == theta2:
        return val1_pos, val1_neg

    val2_pos = df.loc[(flow_condition, theta2, area_cond), cn_pos_col]
    val2_neg = df.loc[(flow_condition, theta2, area_cond), cn_neg_col]

    # 4. 進行線性內插
    cn_pos = np.interp(theta, [theta1, theta2], [val1_pos, val2_pos])
    cn_neg = np.interp(theta, [theta1, theta2], [val1_neg, val2_neg])

    return cn_pos, cn_neg


def calculate_pitched_roof_cc_cn(theta, effective_area_A, a, flow_condition, zone, db):
    """
    從資料庫中查找並內插 Pitched Free Roof 的 C&C 淨壓力係數 CN。
    """
    df = db['PITCHED_CC_CN_DF']  # 【核心差異】

    if effective_area_A <= a ** 2:
        area_cond = '<=a^2'
    elif a ** 2 < effective_area_A <= 4 * a ** 2:
        area_cond = '>a^2, <=4a^2'
    else:
        area_cond = '>4a^2'

    thetas = df.index.get_level_values('theta').unique().sort_values()

    theta_upper_idx = np.searchsorted(thetas, theta)
    theta_lower_idx = max(0, theta_upper_idx - 1)
    if theta_upper_idx >= len(thetas):
        theta_upper_idx = theta_lower_idx = len(thetas) - 1

    theta1, theta2 = thetas[theta_lower_idx], thetas[theta_upper_idx]

    cn_pos_col, cn_neg_col = f'Z{zone}+', f'Z{zone}-'

    val1_pos = df.loc[(flow_condition, theta1, area_cond), cn_pos_col]
    val1_neg = df.loc[(flow_condition, theta1, area_cond), cn_neg_col]

    if theta1 == theta2:
        return val1_pos, val1_neg

    val2_pos = df.loc[(flow_condition, theta2, area_cond), cn_pos_col]
    val2_neg = df.loc[(flow_condition, theta2, area_cond), cn_neg_col]

    cn_pos = np.interp(theta, [theta1, theta2], [val1_pos, val2_pos])
    cn_neg = np.interp(theta, [theta1, theta2], [val1_neg, val2_neg])

    return cn_pos, cn_neg


def run_monoslope_cc_analysis(params: dict, db: dict):
    """
    執行單斜式屋頂的局部披覆構材 (C&C) 風壓力計算。
    """
    try:
        print("\n--- 開始計算單斜式屋頂 C&C 風壓力 ---")
        results = {}

        # 1. 提取參數
        general_params = params
        roof_params = params.get('geometry_data', {}).get('roof', {})
        h = params['h']  # 使用主函式統一計算的 h
        b_x = float(roof_params.get('b_x', 0))
        b_y = float(roof_params.get('b_y', 0))
        theta = float(roof_params.get('theta', 0))
        flow_condition = 'Obstructed' if roof_params.get('blockage') == 'obstructed' else 'Clear'

        # 2. 計算 C&C 通用參數
        a = calculate_parameter_a_for_cc(h, b_x, b_y)
        q_h = calculate_velocity_pressure(h, general_params['I'], general_params['V10_C'], general_params['terrain'],
                                          1.0, db)

        # 陣風反應因子 G/Gf (C&C 使用與主結構相同的 G)
        # 為了計算 G，我們需要假設一個風向來確定 B 和 L
        params_for_g = {
            'h': h, 'B': b_y, 'L': b_x, 'terrain': general_params['terrain'],
            'fn': general_params.get('fnX', 1.0),
            'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        common_gust_params = calculate_gust_common_params(params_for_g, db)
        rigidity = '柔性' if params_for_g['fn'] < 1.0 else '普通'
        gust_factor = calculate_Gf_factor(params_for_g, common_gust_params,
                                          db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                            common_gust_params)

        results['calc_params'] = {'a': a, 'q_h': q_h, 'G': gust_factor}

        # 3. 迭代計算不同區域和面積下的風壓
        # 有效受風面積 (單位: m^2)，對應規範的 10, 20, 50, 100 ft^2
        standard_areas_m2 = [0.93, 1.86, 4.65, 9.29]
        results_by_zone = {'Zone 1': [], 'Zone 2': [], 'Zone 3': []}

        for area_m2 in standard_areas_m2:
            for zone_num in [1, 2, 3]:
                cn_pos, cn_neg = calculate_monoslope_cc_cn(theta, area_m2, a, flow_condition, zone_num, db)
                G = gust_factor['final_value']
                p_pos = q_h * G * cn_pos
                p_neg = q_h * G * cn_neg
                results_by_zone[f'Zone {zone_num}'].append({
                    'area': area_m2,
                    'cn_pos': cn_pos,
                    'cn_neg': cn_neg,
                    'p_pos': p_pos,
                    'p_neg': p_neg
                })

        results['results_by_zone'] = results_by_zone
        print("--- C&C 風壓力計算完成 ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_troughed_roof_cc_cn(theta, effective_area_A, a, flow_condition, zone, db):
    """
    從資料庫中查找並內插 Troughed Free Roof 的 C&C 淨壓力係數 CN。
    """
    df = db['THROUGHED_CC_CN_DF']  # 【核心差異】

    if effective_area_A <= a ** 2:
        area_cond = '<=a^2'
    elif a ** 2 < effective_area_A <= 4 * a ** 2:
        area_cond = '>a^2, <=4a^2'
    else:
        area_cond = '>4a^2'

    thetas = df.index.get_level_values('theta').unique().sort_values()

    theta_upper_idx = np.searchsorted(thetas, theta)
    theta_lower_idx = max(0, theta_upper_idx - 1)
    if theta_upper_idx >= len(thetas):
        theta_upper_idx = theta_lower_idx = len(thetas) - 1

    theta1, theta2 = thetas[theta_lower_idx], thetas[theta_upper_idx]

    cn_pos_col, cn_neg_col = f'Z{zone}+', f'Z{zone}-'

    val1_pos = df.loc[(flow_condition, theta1, area_cond), cn_pos_col]
    val1_neg = df.loc[(flow_condition, theta1, area_cond), cn_neg_col]

    if theta1 == theta2:
        return val1_pos, val1_neg

    val2_pos = df.loc[(flow_condition, theta2, area_cond), cn_pos_col]
    val2_neg = df.loc[(flow_condition, theta2, area_cond), cn_neg_col]

    cn_pos = np.interp(theta, [theta1, theta2], [val1_pos, val2_pos])
    cn_neg = np.interp(theta, [theta1, theta2], [val1_neg, val2_neg])

    return cn_pos, cn_neg


def run_pitched_roof_cc_analysis(params: dict, db: dict):
    """
    執行 Pitched Free Roof 的局部披覆構材 (C&C) 風壓力計算。
    """
    try:
        print("\n--- 開始計算 Pitched Free Roof C&C 風壓力 ---")
        results = {}

        general_params = params
        roof_params = params.get('geometry_data', {}).get('roof', {})
        h = params['h']
        b_x = float(roof_params.get('b_x', 0))
        b_y = float(roof_params.get('b_y', 0))
        theta = float(roof_params.get('theta', 0))
        flow_condition = 'Obstructed' if roof_params.get('blockage') == 'obstructed' else 'Clear'

        a = calculate_parameter_a_for_cc(h, b_x, b_y)
        q_h = calculate_velocity_pressure(h, general_params['I'], general_params['V10_C'], general_params['terrain'],
                                          1.0, db)

        params_for_g = {
            'h': h, 'B': b_y, 'L': b_x, 'terrain': general_params['terrain'],
            'fn': general_params.get('fnX', 1.0),
            'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        common_gust_params = calculate_gust_common_params(params_for_g, db)
        rigidity = '柔性' if params_for_g['fn'] < 1.0 else '普通'
        gust_factor = calculate_Gf_factor(params_for_g, common_gust_params,
                                          db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                            common_gust_params)
        G = gust_factor['final_value']

        results['calc_params'] = {'a': a, 'q_h': q_h, 'G': gust_factor}

        standard_areas_m2 = [0.93, 1.86, 4.65, 9.29]
        results_by_zone = {'Zone 1': [], 'Zone 2': [], 'Zone 3': []}

        for area_m2 in standard_areas_m2:
            for zone_num in [1, 2, 3]:
                # 【核心差異】
                cn_pos, cn_neg = calculate_pitched_roof_cc_cn(theta, area_m2, a, flow_condition, zone_num, db)
                p_pos = q_h * G * cn_pos
                p_neg = q_h * G * cn_neg
                results_by_zone[f'Zone {zone_num}'].append({
                    'area': area_m2,
                    'cn_pos': cn_pos,
                    'cn_neg': cn_neg,
                    'p_pos': p_pos,
                    'p_neg': p_neg
                })

        results['results_by_zone'] = results_by_zone
        print("--- C&C 風壓力計算完成 (Pitched Roof) ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def run_troughed_roof_cc_analysis(params: dict, db: dict):
    """
    執行 Troughed Free Roof 的局部披覆構材 (C&C) 風壓力計算。
    """
    try:
        print("\n--- 開始計算 Troughed Free Roof C&C 風壓力 ---")
        results = {}

        general_params = params
        roof_params = params.get('geometry_data', {}).get('roof', {})
        h = params['h']
        b_x = float(roof_params.get('b_x', 0))
        b_y = float(roof_params.get('b_y', 0))
        theta = float(roof_params.get('theta', 0))
        flow_condition = 'Obstructed' if roof_params.get('blockage') == 'obstructed' else 'Clear'

        a = calculate_parameter_a_for_cc(h, b_x, b_y)
        q_h = calculate_velocity_pressure(h, general_params['I'], general_params['V10_C'], general_params['terrain'],
                                          1.0, db)

        params_for_g = {
            'h': h, 'B': b_y, 'L': b_x, 'terrain': general_params['terrain'],
            'fn': general_params.get('fnX', 1.0),
            'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        common_gust_params = calculate_gust_common_params(params_for_g, db)
        rigidity = '柔性' if params_for_g['fn'] < 1.0 else '普通'
        gust_factor = calculate_Gf_factor(params_for_g, common_gust_params,
                                          db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                            common_gust_params)

        results['calc_params'] = {'a': a, 'q_h': q_h, 'G': gust_factor}

        standard_areas_m2 = [0.93, 1.86, 4.65, 9.29]
        results_by_zone = {'Zone 1': [], 'Zone 2': [], 'Zone 3': []}

        for area_m2 in standard_areas_m2:
            for zone_num in [1, 2, 3]:
                # 【核心差異】
                cn_pos, cn_neg = calculate_troughed_roof_cc_cn(theta, area_m2, a, flow_condition, zone_num, db)
                p_pos = q_h * gust_factor * cn_pos
                p_neg = q_h * gust_factor * cn_neg
                results_by_zone[f'Zone {zone_num}'].append({
                    'area': area_m2,
                    'cn_pos': cn_pos,
                    'cn_neg': cn_neg,
                    'p_pos': p_pos,
                    'p_neg': p_neg
                })

        results['results_by_zone'] = results_by_zone
        print("--- C&C 風壓力計算完成 (Troughed Roof) ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def run_open_building_analysis(params: dict):
    """
    開放式建築物風力計算的主進入點 (調度中心)。
    【核心修正】: 此函式現在只處理單一工況。
    """
    try:
        db = setup_databases()
        results = {}
        building_type = params.get('enclosure_status')

        # 根據建築類型呼叫對應的單一工況計算函式
        if building_type == 'chimney':
            results['chimney_results'] = calculate_chimney_force(params, db)
        elif building_type == 'shed-roof':
            shed_results = run_shed_roof_analysis(params, db)
            if shed_results:
                if 'support_force_results' in shed_results:
                    results['support_force_results'] = shed_results.pop('support_force_results')
                results['shed_roof_results'] = shed_results
            monoslope_cc_results = run_monoslope_cc_analysis(params, db)
            if monoslope_cc_results:
                results['monoslope_cc_results'] = monoslope_cc_results
        elif building_type == 'pitched-free-roof':
            pitched_results = run_pitched_roof_analysis(params, db)
            if pitched_results:
                if 'support_force_results' in pitched_results:
                    results['support_force_results'] = pitched_results.pop('support_force_results')
                results['pitched_roof_results'] = pitched_results
            pitched_cc_results = run_pitched_roof_cc_analysis(params, db)
            if pitched_cc_results:
                results['pitched_cc_results'] = pitched_cc_results
        elif building_type == 'troughed-free-roof':
            troughed_results = run_troughed_roof_analysis(params, db)
            if troughed_results:
                if 'support_force_results' in troughed_results:
                    results['support_force_results'] = troughed_results.pop('support_force_results')
                results['troughed_roof_results'] = troughed_results
            troughed_cc_results = run_troughed_roof_cc_analysis(params, db)
            if troughed_cc_results:
                results['troughed_cc_results'] = troughed_cc_results
        elif building_type == 'solid-sign':
            solid_sign_full_results = calculate_solid_sign_force_and_cf(params, db)
            if solid_sign_full_results:
                if 'support_forces' in solid_sign_full_results and solid_sign_full_results['support_forces']:
                    results['support_force_results'] = solid_sign_full_results.pop('support_forces')
                results['solid_sign_results'] = solid_sign_full_results
        elif building_type == 'hollow-sign':
            hollow_sign_results = calculate_hollow_sign_force(params, db)
            if hollow_sign_results:
                results['hollow_sign_results'] = hollow_sign_results
            support_height = hollow_sign_results.get('support_height', 0) if hollow_sign_results else 0
            if support_height > 0:
                results['support_force_results'] = calculate_support_force_generic(params, db)
        elif building_type == 'truss-tower':
            # 直接呼叫，因為它現在也能處理單一工況
            results['truss_tower_results'] = calculate_truss_tower_force(params, db)
        elif building_type == 'water-tower':
            results['water_tower_results'] = calculate_water_tower_force(params, db)
        elif building_type == 'street-light':
            return run_street_light_analysis(params, db)
        else:
            return {"status": "error", "message": f"尚未支援的開放式建築類型: {building_type}"}

        if any(v is None for v in results.values()):
            return {"status": "error", "message": "後端計算時發生錯誤，請檢查終端機日誌。"}

        return {"status": "success", "analysis_type": "open_building", "data": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"開放式建築計算過程中發生錯誤: {str(e)}"}


def run_street_light_analysis(params: dict, db: dict):
    """
    計算路燈或紅綠燈結構的風力。
    第一階段：先處理主桿部分，並在後端打印結果。
    """
    try:
        print("\n" + "=" * 25 + " 開始路燈結構分析 " + "=" * 25)
        results = {}
        geo_data = params.get('geometry_data', {})
        main_pole_data = geo_data.get('main_pole', {})

        if not main_pole_data:
            return {"status": "error", "message": "後端錯誤：找不到路燈主桿的幾何數據。"}

        # --- 1. 計算主桿 (Main Pole) 風力 ---
        # 我們將主桿數據轉換為 calculate_chimney_force 函式所需的格式
        print("\n--- 1. 正在計算主桿風力 (使用煙囪模型)... ---")

        # 為了呼叫 calculate_chimney_force，我們需要模擬一個完整的 params 字典
        params_for_pole = params.copy()
        params_for_pole['geometry_data'] = {
            'h': float(main_pole_data.get('h_m', 0)),
            'shape': 'circular',  # 路燈主桿通常是圓形
            'D_top': float(main_pole_data.get('d_top', 0)),
            'D_bot': float(main_pole_data.get('d_bot', 0)),
            'D': 0,  # 對圓形非必須，設為0即可
            'roughness': main_pole_data.get('roughness'),
            'layer_height': params.get('layer_height', 2.0)  # 也可以從前端接收或設為固定值
        }

        # 呼叫現有的煙囪計算函式
        pole_force_results = calculate_chimney_force(params_for_pole, db)

        if pole_force_results:
            results['main_pole_results'] = pole_force_results
            print("\n--- 主桿計算結果 (後端終端機預覽) ---")
            print(f"  - 總風力: {pole_force_results.get('total_force', 0):.2f} kgf")
            print("  - 計算細節:")
            for detail in pole_force_results.get('details', []):
                print(
                    f"    - {detail['z_range']} m: Cf={detail['cf']:.3f}, q(z)={detail['q_z']:.2f}, Force={detail['force']:.2f} kgf")
            print("----------------------------------------")
        else:
            print("\n--- 主桿計算失敗 ---")
            results['main_pole_results'] = None

        # --- 2. 橫向支撐桿 (待辦) ---
        print("\n--- 2. 橫向支撐桿計算 (尚未實現) ---")
        results['support_arm_results'] = "TODO"

        # --- 3. 燈具 (待辦) ---
        print("\n--- 3. 燈具計算 (尚未實現) ---")
        results['luminaire_results'] = "TODO"

        print("\n" + "=" * 25 + " 路燈結構分析結束 " + "=" * 25)
        return {"status": "success", "data": results}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"路燈計算過程中發生錯誤: {str(e)}"}


# ==================================================================
# ==== START: 新增平行風向計算函式 (ASCE Fig 27.4-7) ====
# ==================================================================
def calculate_parallel_wind_cn(params: dict, db: dict) -> dict:
    """
    根據 ASCE Fig 27.4-7 計算所有屋頂類型在平行風向時的淨壓力係數 CN。
    此函式會根據屋頂的實際尺寸 (L) 和高度 (h)，只返回實際存在的區域的係數。
    """
    try:
        print("\n--- 開始計算開放式屋頂 淨壓力係數 CN (風向平行屋脊) ---")
        df = db['FREE_ROOF_PARALLEL_WIND_CN_DF']
        roof_params = params.get('geometry_data', {}).get('roof', {})

        blockage = roof_params.get('blockage')
        flow_condition = 'obstructed' if blockage == 'obstructed' else 'clear'

        # 獲取計算 h 和 L 所需的參數
        h_ridge = float(roof_params.get('h_ridge', 0))
        h_eave = float(roof_params.get('h_eave', 0))
        theta = float(roof_params.get('theta', 0))
        b_x = float(roof_params.get('b_x', 0))
        b_y = float(roof_params.get('b_y', 0))
        ridge_dir = roof_params.get('ridge_direction')

        # 根據規則計算平均屋頂高度 h
        h = (h_ridge + h_eave) / 2 if theta >= 10 else h_eave

        # 風向平行於屋脊，所以 L 是屋脊的長度
        L = b_x if ridge_dir == 'X' else b_y

        print(f"  - 輸入參數: 氣流條件='{flow_condition}', 屋頂長度 L={L:.2f}m, 平均高度 h={h:.2f}m")

        if theta >= 45:
            print(f"  - 警告: 平行風向計算僅適用於 θ < 45°。當前角度為 {theta:.2f}°，不計算此項。")
            return None

        results = {}

        # ===== START OF MODIFICATION: 根據 L 和 h 判斷存在的區域 =====
        # 區域 1: < h
        if L > 0:
            dist_cond = '<h'
            cn_a = df.loc[(dist_cond, 'A'), flow_condition]
            cn_b = df.loc[(dist_cond, 'B'), flow_condition]
            zone_key = 'lt_h'
            results[zone_key] = {'cn_a': cn_a, 'cn_b': cn_b}
            print(f"  - 區域 (< h) 存在。")

        # 區域 2: >h, <2h
        if L > h:
            dist_cond = '>h, <2h'
            cn_a = df.loc[(dist_cond, 'A'), flow_condition]
            cn_b = df.loc[(dist_cond, 'B'), flow_condition]
            zone_key = 'gt_h_lt_2h'
            results[zone_key] = {'cn_a': cn_a, 'cn_b': cn_b}
            print(f"  - 區域 (> h, < 2h) 存在，因為 L ({L:.2f}) > h ({h:.2f})。")

        # 區域 3: >2h
        if L > 2 * h:
            dist_cond = '>2h'
            cn_a = df.loc[(dist_cond, 'A'), flow_condition]
            cn_b = df.loc[(dist_cond, 'B'), flow_condition]
            zone_key = 'gt_2h'
            results[zone_key] = {'cn_a': cn_a, 'cn_b': cn_b}
            print(f"  - 區域 (> 2h) 存在，因為 L ({L:.2f}) > 2*h ({2 * h:.2f})。")
        # ===== END OF MODIFICATION =====

        print(f"  - ==> 最終返回的區域結果: {results}")
        print("--- 平行風向 CN 計算結束 ---\n")
        return results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_chimney_force_conservative(params: dict, db: dict):
    """
    計算煙囪的總風力，此版本會比較 X 和 Y 方向的地形影響，並取較大的 Kzt 進行保守計算。
    """
    try:
        print("\n--- 開始計算煙囪總風力 (保守法, 取 max(Kzt_x, Kzt_y)) ---")
        geo_data = params.get('geometry_data', {})
        general_params = params

        # 獲取兩組地形參數
        topo_params_x = params.get('topo_params_x', {})
        topo_params_y = params.get('topo_params_y', {})
        is_topo_x = topo_params_x.get('is_topo', False)
        is_topo_y = topo_params_y.get('is_topo', False)

        # 1. 獲取幾何參數 (與原函式相同)
        total_h = float(geo_data.get('h', 0))
        shape_en = geo_data.get('shape');
        roughness_en = geo_data.get('roughness')
        layer_height = float(geo_data.get('layer_height', 2.0))
        d_top = float(geo_data.get('D_top', 0));
        d_bot = float(geo_data.get('D_bot', 0));
        d_sq = float(geo_data.get('D', 0))
        if total_h <= 0: return None

        # ==== 陣風反應因子 G/Gf 的計算 (因為煙囪對稱，任選一方向計算即可) ====
        # 我們假設使用 X 方向的 fn 進行計算
        fn_for_g = general_params.get('fnX', 1.0)
        rigidity = '柔性' if fn_for_g < 1.0 else '普通'
        avg_d = (d_top + d_bot) / 2 if shape_en == 'circular' else d_sq
        params_for_g = {'h': total_h, 'B': avg_d, 'L': avg_d, 'terrain': general_params['terrain'], 'fn': fn_for_g,
                        'beta': float(general_params.get('dampingRatio', 0.01)), 'V10_C': general_params['V10_C'],
                        'I': general_params['I']}
        common_gust = calculate_gust_common_params(params_for_g, db)
        g_factor_details = calculate_Gf_factor(params_for_g, common_gust,
                                               db) if rigidity == '柔性' else calculate_G_factor(params_for_g,
                                                                                                 common_gust)
        gust_factor = g_factor_details['final_value']
        print(f"  - ==> 陣風反應因子 G/Gf = {gust_factor:.3f} ({rigidity}建築)")

        # 2. 進行分層計算
        total_force = 0.0
        calculation_details = []
        cut_points = [0.0]
        if total_h > 5.0:
            cut_points.append(5.0);
            start_h_for_arange = 5.0
        else:
            start_h_for_arange = 0.0
        if total_h > start_h_for_arange: cut_points.extend(
            np.arange(start_h_for_arange + layer_height, total_h, layer_height).tolist())
        cut_points.append(total_h)
        cut_points = np.unique(np.array(cut_points))

        for i in range(len(cut_points) - 1):
            z1, z2 = cut_points[i], cut_points[i + 1]
            h_layer = z2 - z1
            if h_layer < 1e-6: continue

            if shape_en == 'circular':
                d1 = np.interp(z1, [0, total_h], [d_bot, d_top]);
                d2 = np.interp(z2, [0, total_h], [d_bot, d_top])
                layer_avg_d = (d1 + d2) / 2
            else:
                layer_avg_d = d_sq;
                d1 = d2 = d_sq
            layer_area = layer_avg_d * h_layer

            # ==== 【核心修正點】====
            zc = (h_layer / 3) * (d1 + 2 * d2) / (d1 + d2) if (d1 + d2) > 0 else h_layer / 2
            z_eff = z1 + zc

            # 分別計算 X 和 Y 方向的地形因子
            kzt_x = calculate_topography_factor(topo_params_x['params'], z_eff, db)[0] if is_topo_x else 1.0
            kzt_y = calculate_topography_factor(topo_params_y['params'], z_eff, db)[0] if is_topo_y else 1.0

            # 選用較大的 Kzt 進行計算
            kzt_conservative = max(kzt_x, kzt_y)

            q_z_eff = calculate_velocity_pressure(z_eff, general_params['I'], general_params['V10_C'],
                                                  general_params['terrain'], kzt_conservative, db)

            cf_layer = calculate_chimney_cf(total_h, layer_avg_d, shape_en, roughness_en, general_params, db)
            if cf_layer is None: raise ValueError("Cf 計算失敗")

            # 計算風力時使用 gust_factor
            layer_force = q_z_eff * gust_factor * cf_layer * layer_area
            total_force += layer_force

            calculation_details.append(
                {'z_range': f"{z1:.2f}-{z2:.2f}", 'z_eff': z_eff, 'q_z': q_z_eff, 'kzt': kzt_conservative,
                 'cf': cf_layer, 'g_factor': gust_factor, 'area': layer_area, 'force': layer_force})
            print(
                f"    - 分段 {z1:.2f}-{z2:.2f}m: Kzt_x={kzt_x:.3f}, Kzt_y={kzt_y:.3f} -> Kzt_use={kzt_conservative:.3f}, q(z)={q_z_eff:.2f}, F={layer_force:.2f}")

        print(f"  - ==> 加總後總設計風力 F = {total_force:.2f} kgf")
        return {'total_force': total_force, 'details': calculation_details, 'g_factor_details': g_factor_details,
                'main_params': {'rigidity': rigidity, 'gust_factor': gust_factor}}

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


# wind_calculations.py

def calculate_solid_sign_force_conservative(params: dict, db: dict):
    """
    計算實體標示物的總風力，此版本會比較 X 和 Y 方向的地形影響，並取較大的 Kzt 進行保守計算。
    【核心修正】: 徹底重構此函式，將所有計算邏輯（G因子、Cf、風力）整合在此，確保返回一個包含所有必需數據的完整字典。
    """
    try:
        print("\n--- 開始計算實體標示物完整結構風力 (保守法, 含支撐G因子) ---")
        geo_data = params.get('geometry_data', {})
        sign_params = geo_data.get('sign', {})
        support_params = geo_data.get('support', {})
        general_params = params

        # --- 1. 獲取幾何參數 ---
        b_h = float(sign_params.get('b_h', 0))
        b_v = float(sign_params.get('b_v', 0))
        d = float(sign_params.get('d', 0))
        h_top = d + b_v
        As = b_h * b_v
        if As <= 0: return None

        # --- 2. 計算主體 G/Gf 因子 ---
        normal_direction = sign_params.get('normal_direction', 'X')
        fn_for_g_sign = general_params.get('fnX') if normal_direction == 'X' else general_params.get('fnY')
        rigidity_sign = '柔性' if fn_for_g_sign < 1.0 else '普通'
        params_for_g_sign = {
            'h': h_top, 'B': b_h, 'L': 0.1, 'terrain': general_params['terrain'],
            'fn': fn_for_g_sign, 'beta': float(general_params.get('dampingRatio', 0.01)),
            'V10_C': general_params['V10_C'], 'I': general_params['I']
        }
        common_gust_sign = calculate_gust_common_params(params_for_g_sign, db)
        g_factor_details = calculate_Gf_factor(params_for_g_sign, common_gust_sign,
                                               db) if rigidity_sign == '柔性' else calculate_G_factor(params_for_g_sign,
                                                                                                      common_gust_sign)
        gust_factor_sign = g_factor_details['final_value']

        # --- 3. 計算支撐結構 G/Gf 因子 ---
        support_g_factor_details = None
        support_main_params = {}
        support_cf_details = {} # 初始化為空字典
        support_force_details = {} # 初始化為空字典
        support_height = float(support_params.get('h', 0))

        if support_height > 0:
            # 首先計算 Cf 細節，因為 G 因子計算需要用到裡面的 B
            support_cf_details = calculate_support_column_cf(params, db)

            # 然後計算 G 因子
            fn_for_g_support = fn_for_g_sign
            rigidity_support = rigidity_sign
            support_B_for_g = support_cf_details.get('B_y') if normal_direction == 'X' else support_cf_details.get(
                'B_x')
            params_for_support_g = {'h': support_height, 'B': support_B_for_g, 'L': 0.1,
                                    'terrain': general_params['terrain'], 'fn': fn_for_g_support,
                                    'beta': float(general_params.get('dampingRatio', 0.01)),
                                    'V10_C': general_params['V10_C'], 'I': general_params['I']}
            common_gust_support = calculate_gust_common_params(params_for_support_g, db)
            support_g_factor_details = calculate_Gf_factor(params_for_support_g, common_gust_support,
                                                           db) if rigidity_support == '柔性' else calculate_G_factor(
                params_for_support_g, common_gust_support)
            support_main_params = {'rigidity': rigidity_support, 'B': support_B_for_g, 'L': 0.1}

            # 最後呼叫函式計算最終風力
            params_for_support_force = params.copy()
            params_for_support_force['support_g_factor_details'] = support_g_factor_details
            support_force_details = calculate_support_force_like_chimney(params_for_support_force, support_cf_details,
                                                                         db)

        # --- 4. 計算保守風速壓 q(h) ---
        topo_params_x = params.get('topo_params_x', {})
        topo_params_y = params.get('topo_params_y', {})
        is_topo_x = topo_params_x.get('is_topo', False)
        is_topo_y = topo_params_y.get('is_topo', False)
        kzt_x_h = calculate_topography_factor(topo_params_x.get('params', {}), h_top, db)[0] if is_topo_x else 1.0
        kzt_y_h = calculate_topography_factor(topo_params_y.get('params', {}), h_top, db)[0] if is_topo_y else 1.0
        kzt_conservative_h = max(kzt_x_h, kzt_y_h)
        q_h_conservative = calculate_velocity_pressure(h_top, general_params['I'], general_params['V10_C'],
                                                       general_params['terrain'], kzt_conservative_h, db)

        # --- 5. 計算風力係數 Cf ---
        cf_results = calculate_solid_sign_cf(params, db)
        if not cf_results or 'case_a_b_cf' not in cf_results: return None

        # --- 6. 計算 Case A/B 風力 ---
        force_case_ab = q_h_conservative * gust_factor_sign * cf_results['case_a_b_cf'] * As

        # --- 7. 計算 Case C 風力 ---
        case_c_force_details = []
        if 'case_c_cfs' in cf_results and cf_results['case_c_cfs']:
            # ==== ▼▼▼ START: 【核心修正】補上遺漏的 Case C 區域面積計算邏輯 ▼▼▼ ====
            s = b_v
            region_map = {
                '0-s': (0, s), 's-2s': (s, 2 * s), '2s-3s': (2 * s, 3 * s),
                '3s-4s': (3 * s, 4 * s), '4s-5s': (4 * s, 5 * s), '5s-10s': (5 * s, 10 * s),
                '3s-10s': (3 * s, 10 * s), '>10s': (10 * s, b_h)
            }
            for region, cf in cf_results['case_c_cfs'].items():
                if region not in region_map: continue
                start_dist, end_dist = region_map[region]
                region_width = min(end_dist, b_h) - start_dist
                if region_width <= 0: continue
                region_area = region_width * b_v
                # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====
                region_force = q_h_conservative * gust_factor_sign * cf * region_area
                case_c_force_details.append({'region': region, 'cf': cf, 'area': region_area, 'force': region_force})

        # --- 8. 計算支撐結構風力 ---
        # ==== ▼▼▼ START: 【核心修正】用新的函式替換舊的計算邏輯 ▼▼▼ ====
        support_force_details = {}
        if support_height > 0:
            cf_data = calculate_support_column_cf(params, db)

            # ==== ▼▼▼ START: 【核心修正】將 cf_x, cf_y 加入 support_g_factor_details ▼▼▼ ====
            if support_g_factor_details:  # 確保字典存在
                support_g_factor_details['cf_x'] = cf_data.get('cf_x', 0)
                support_g_factor_details['cf_y'] = cf_data.get('cf_y', 0)
            # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

            # 建立一個傳遞給新函式的參數字典
            params_for_support_force = params.copy()
            params_for_support_force['support_g_factor_details'] = support_g_factor_details
            support_force_details = calculate_support_force_like_chimney(params_for_support_force, support_cf_details, db)
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

        # --- 9. 組合最終的完整字典返回 ---
        final_results = {
            'total_force': force_case_ab,
            'cf_value': cf_results['case_a_b_cf'],
            'gust_factor': gust_factor_sign,
            'q_h': q_h_conservative,
            'g_factor_details': g_factor_details,
            'kzt_conservative_h': kzt_conservative_h,
            'main_params': {'rigidity': rigidity_sign, 'B': b_h, 'L': b_v},
            'support_g_factor_details': support_g_factor_details,
            'support_main_params': support_main_params,
            'case_c_forces': case_c_force_details,
            'area_main': As,
            'support_cf_details': support_cf_details,  # <--- 傳遞 Cf 細節
            'support_forces': support_force_details  # <--- 現在這個鍵將包含新函式返回的完整字典
        }
        print(f"  - ==> (Conservative) Case A/B 總設計風力 F = {final_results['total_force']:.2f} kgf")
        return final_results

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


def calculate_hollow_sign_force_conservative(params: dict, db: dict):
    """
    計算中空標示物的總風力，此版本會比較 X 和 Y 方向的地形影響，並取較大的 Kzt 進行保守計算。
    """
    try:
        print("\n--- 開始計算中空標示物總風力 (保守法, 取 max(Kzt_x, Kzt_y)) ---")
        geo_data = params.get('geometry_data', {}).get('sign', {})
        general_params = params
        df_cf = db['HOLLOW_SIGN_CF_DF']

        topo_params_x = params.get('topo_params_x', {})
        topo_params_y = params.get('topo_params_y', {})
        is_topo_x = topo_params_x.get('is_topo', False)
        is_topo_y = topo_params_y.get('is_topo', False)

        opening_ratio_percent = float(geo_data.get('opening_ratio', 0))
        solidity_ratio = 1.0 - (opening_ratio_percent / 100.0)

        lookup_key = ('平邊構材', 'N/A');
        phi_column = ''
        if solidity_ratio < 0.1:
            phi_column = '<0.1'
        elif 0.1 <= solidity_ratio <= 0.29:
            phi_column = '0.1-0.29'
        else:
            phi_column = '0.3-0.7'
        cf_value = df_cf.loc[lookup_key, phi_column]

        total_force = 0.0
        calculation_details = []
        qz_mode = geo_data.get('qz_mode', 'auto')

        if qz_mode == 'manual':
            for item in geo_data.get('manual_inputs', []):
                name, z_eff, area = item.get('name'), item.get('height'), item.get('area')
                k_z = calculate_velocity_pressure_coeff(z_eff, general_params['terrain'], db)
                kzt_x = calculate_topography_factor(topo_params_x.get('params', {}), z_eff, db)[0] if is_topo_x else 1.0
                kzt_y = calculate_topography_factor(topo_params_y.get('params', {}), z_eff, db)[0] if is_topo_y else 1.0
                kzt_conservative = max(kzt_x, kzt_y)
                q_z = calculate_velocity_pressure(z_eff, general_params['I'], general_params['V10_C'],
                                                  general_params['terrain'], kzt_conservative, db)
                force = q_z * area * cf_value
                total_force += force
                calculation_details.append(
                    {'layer': name, 'z_range': f"在 {z_eff:.2f}", 'z_eff': z_eff, 'q_z': q_z, 'kzt': kzt_conservative,
                     'area': area, 'force': force})
        else:
            b_h = float(geo_data.get('b_h', 0))
            b_v = float(geo_data.get('b_v', 0))
            d = float(geo_data.get('d', 0))
            layer_height = float(geo_data.get('layer_height', 2.0))
            z_bottom, z_top = d, d + b_v
            cut_points = np.unique(np.append(np.arange(z_bottom, z_top, layer_height), z_top))
            for i in range(len(cut_points) - 1):
                z1, z2 = cut_points[i], cut_points[i + 1]
                z_mid = (z1 + z2) / 2;
                layer_area = b_h * (z2 - z1)
                kzt_x = calculate_topography_factor(topo_params_x.get('params', {}), z_mid, db)[0] if is_topo_x else 1.0
                kzt_y = calculate_topography_factor(topo_params_y.get('params', {}), z_mid, db)[0] if is_topo_y else 1.0
                kzt_conservative = max(kzt_x, kzt_y)
                q_z_mid = calculate_velocity_pressure(z_mid, general_params['I'], general_params['V10_C'],
                                                      general_params['terrain'], kzt_conservative, db)
                layer_force = q_z_mid * layer_area * cf_value
                total_force += layer_force
                calculation_details.append(
                    {'layer': f'分層 {i + 1}', 'z_range': f"{z1:.2f} - {z2:.2f}", 'z_eff': z_mid, 'q_z': q_z_mid,
                     'kzt': kzt_conservative, 'area': layer_area, 'force': layer_force})

        print(f"  - ==> 加總後總風力 F = {total_force:.2f} kgf")

        # ==== ▼▼▼ START: 【核心修正】確保函式在結尾處返回一個完整的字典 ▼▼▼ ====
        return {
            'total_force': total_force,
            'cf_value': cf_value,
            'solidity_ratio': solidity_ratio,
            'details': calculation_details,
            'main_params': {},  # 中空標示物沒有 G 因子，給一個空字典
            'g_factor_details': None  # 明確表示沒有 G 因子細節
        }
        # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None


# wind_calculations.py

def calculate_support_force_like_chimney(params: dict, cf_data: dict, db: dict):
    """
    採用類似煙囪的分層法，計算實體標示物的支撐結構風力。
    【核心修正】: 1. 使用從 calculate_support_column_cf 傳來的保守 Cf。
                  2. 根據主體風向，使用正確的投影寬度計算面積。
    """
    try:
        print("\n--- 開始計算支撐結構風力 (類煙囪保守法) ---")
        geo_data = params.get('geometry_data', {})
        sign_params = geo_data.get('sign', {})
        support_params = geo_data.get('support', {})
        general_params = params

        support_h = float(support_params.get('h', 0))
        if support_h <= 0: return None

        layer_height = float(support_params.get('layer_height', 2.0))
        normal_direction = sign_params.get('normal_direction', 'X')

        # --- 1. 獲取保守風力係數 Cf ---
        cf_data = calculate_support_column_cf(params, db)
        cf_conservative = cf_data.get('cf_conservative', 0)
        if cf_conservative == 0:
            print("  - 警告: 支撐結構的保守 Cf 為 0，風力將為 0。")

        # --- 2. 獲取 G 因子 ---
        support_g_details = params.get('support_g_factor_details', {})
        gust_factor = support_g_details.get('final_value', 1.0)
        rigidity_support = support_g_details.get('type', 'G')

        # --- 3. 進行分層計算 ---
        total_force = 0.0
        calculation_details = []
        cut_points = [0.0]
        if support_h > 5.0:
            cut_points.append(5.0);
            start_h_for_arange = 5.0
        else:
            start_h_for_arange = 0.0
        if support_h > start_h_for_arange:
            cut_points.extend(np.arange(start_h_for_arange + layer_height, support_h, layer_height).tolist())
        cut_points.append(support_h)
        cut_points = np.unique(np.array(cut_points))

        topo_params_x = params.get('topo_params_x', {});
        topo_params_y = params.get('topo_params_y', {})
        is_topo_x = topo_params_x.get('is_topo', False);
        is_topo_y = topo_params_y.get('is_topo', False)

        d_top_x = float(support_params.get('dtop_x', 0));
        d_bot_x = float(support_params.get('dbot_x', 0))
        d_top_y = float(support_params.get('dtop_y', 0));
        d_bot_y = float(support_params.get('dbot_y', 0))

        for i in range(len(cut_points) - 1):
            z1, z2 = cut_points[i], cut_points[i + 1]
            h_layer = z2 - z1
            if h_layer < 1e-6: continue

            # 【核心邏輯】根據主體法向量方向，決定支撐的迎風面寬度
            if normal_direction == 'X':  # 主體迎 Y 風，故支撐結構迎風寬度為 X 方向尺寸
                d1 = np.interp(z1, [0, support_h], [d_bot_x, d_top_x])
                d2 = np.interp(z2, [0, support_h], [d_bot_x, d_top_x])
            else:  # 主體迎 X 風，故支撐結構迎風寬度為 Y 方向尺寸
                d1 = np.interp(z1, [0, support_h], [d_bot_y, d_top_y])
                d2 = np.interp(z2, [0, support_h], [d_bot_y, d_top_y])

            layer_avg_d = (d1 + d2) / 2
            layer_area = layer_avg_d * h_layer

            z_eff = z1 + (h_layer / 2)
            k_z = calculate_velocity_pressure_coeff(z_eff, general_params['terrain'], db)
            kzt_x = calculate_topography_factor(topo_params_x.get('params', {}), z_eff, db)[0] if is_topo_x else 1.0
            kzt_y = calculate_topography_factor(topo_params_y.get('params', {}), z_eff, db)[0] if is_topo_y else 1.0
            kzt_conservative = max(kzt_x, kzt_y)

            q_z_eff = calculate_velocity_pressure(z_eff, general_params['I'], general_params['V10_C'],
                                                  general_params['terrain'], kzt_conservative, db)

            layer_force = q_z_eff * gust_factor * cf_conservative * layer_area
            total_force += layer_force

            calculation_details.append(
                {'z_range': f"{z1:.2f}-{z2:.2f}", 'z_eff': z_eff, 'k_z': k_z, 'q_z': q_z_eff, 'kzt': kzt_conservative,
                 'cf': cf_conservative, 'g_factor': gust_factor, 'area': layer_area, 'force': layer_force})

        print(f"  - ==> 支撐結構總風力 F = {total_force:.2f} kgf")

        return {
            'total_force': total_force,
            'details': calculation_details,
            'cf_conservative': cf_conservative,
            'g_factor_details': support_g_details,
            'main_params': {'rigidity': rigidity_support, 'gust_factor': gust_factor}
        }

    except Exception as e:
        import traceback;
        traceback.print_exc()
        return None

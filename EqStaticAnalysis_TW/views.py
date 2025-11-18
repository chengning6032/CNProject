# EqStaticAnalysis_TW/views.py

import pandas as pd
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
import os
from django.conf import settings
import traceback
import json

# --- 全域設定與輔助函式 (保持不變) ---
DISTANCE_COLUMNS = ['r<=1', 'r=3', 'r=5', 'r=7', 'r=9', 'r=11', 'r=13', 'r>=14']
DISTANCE_POINTS = [1, 3, 5, 7, 9, 11, 13, 14]


def interpolate(x_points, y_points, x_target):
    if x_target <= x_points[0]: return y_points[0]
    if x_target >= x_points[-1]: return y_points[-1]
    return np.interp(x_target, x_points, y_points)


def get_site_amplification_factors(Ss, S1, ground_type):
    ss_points = [0.5, 0.6, 0.7, 0.8, 0.9]
    fa_values = {1: [1.0, 1.0, 1.0, 1.0, 1.0], 2: [1.1, 1.1, 1.0, 1.0, 1.0], 3: [1.2, 1.2, 1.1, 1.0, 1.0]}
    s1_points = [0.30, 0.35, 0.40, 0.45, 0.50]
    fv_values = {1: [1.0, 1.0, 1.0, 1.0, 1.0], 2: [1.5, 1.4, 1.3, 1.2, 1.1], 3: [1.8, 1.7, 1.6, 1.5, 1.4]}
    if ground_type not in [1, 2, 3]: raise ValueError("地盤種類必須為 1, 2, 或 3")
    Fa = interpolate(ss_points, fa_values[ground_type], Ss)
    Fv = interpolate(s1_points, fv_values[ground_type], S1)
    return Fa, Fv


def calculate_empirical_period(hn, structure_type):
    if structure_type == '1':
        return 0.085 * hn ** 0.75
    elif structure_type == '2':
        return 0.070 * hn ** 0.75
    elif structure_type == '3':
        return 0.050 * hn ** 0.75
    return 0.070 * hn ** 0.75


def calculate_Sa_general(S_short, S_one, T_period, T0_boundary):
    if not all(isinstance(i, (int, float)) for i in [S_short, S_one, T_period, T0_boundary]): return 0
    if T_period <= 0.2 * T0_boundary:
        return S_short * (0.4 + 3 * T_period / T0_boundary)
    elif 0.2 * T0_boundary < T_period <= T0_boundary:
        return S_short
    elif T0_boundary < T_period <= 2.5 * T0_boundary:
        return S_one / T_period
    else:
        return 0.4 * S_short


def calculate_Sa_taipei(S_short, T_period, T0_boundary):
    if not all(isinstance(i, (int, float)) for i in [S_short, T_period, T0_boundary]): return 0
    if T_period <= 0.2 * T0_boundary:
        return S_short * (0.4 + 3 * T_period / T0_boundary)
    elif 0.2 * T0_boundary < T_period <= T0_boundary:
        return S_short
    elif T0_boundary < T_period <= 2.5 * T0_boundary:
        return S_short * T0_boundary / T_period
    else:
        return 0.4 * S_short


def calculate_Fu(R, T, T0D, is_taipei_basin, mode=1):
    if not all(isinstance(i, (int, float)) for i in [R, T, T0D]): return 0, 0
    if is_taipei_basin:
        Ra = 1 + (R - 1) / 2.0
    else:
        Ra = 1 + (R - 1) / 1.5
    current_Ra = R if mode == 2 else Ra
    if (2 * current_Ra - 1) < 0: return 0, 0
    sqrt_2Ra_minus_1 = (2 * current_Ra - 1) ** 0.5
    if T >= T0D:
        Fu = current_Ra
    elif 0.6 * T0D <= T < T0D:
        Fu = sqrt_2Ra_minus_1 + (current_Ra - sqrt_2Ra_minus_1) * (T - 0.6 * T0D) / (0.4 * T0D)
    elif 0.2 * T0D <= T < 0.6 * T0D:
        Fu = sqrt_2Ra_minus_1
    else:
        Fu = 1 + (sqrt_2Ra_minus_1 - 1) * T / (0.2 * T0D)
    return Fu, Ra


def calculate_Sa_over_Fu_m(Sa, Fu):
    ratio = Sa / Fu if Fu != 0 else 0
    if ratio <= 0.3:
        return ratio
    elif 0.3 < ratio < 0.8:
        return 0.52 * ratio + 0.144
    else:
        return 0.70 * ratio


def calculate_SaDV_over_Fuv_m(SaV, Fuv, is_near_fault):
    ratio = SaV / Fuv if Fuv != 0 else 0
    if is_near_fault:
        if ratio <= 0.2:
            return ratio
        elif 0.2 < ratio < 0.53:
            return 0.52 * ratio + 0.096
        else:
            return 0.70 * ratio
    else:
        if ratio <= 0.15:
            return ratio
        elif 0.15 < ratio < 0.4:
            return 0.52 * ratio + 0.072
        else:
            return 0.70 * ratio


# --- 主视图函式 ---
def calculator_view(request):
    # ... (前面的程式碼保持不變) ...
    DATA_DIR = os.path.join(settings.BASE_DIR, 'EqStaticAnalysis_TW', 'data')
    GENERAL_CSV = os.path.join(DATA_DIR, 'seismic_data_general.csv')
    TAIPEI_CSV = os.path.join(DATA_DIR, 'seismic_data_taipei_special.csv')
    FAULTS_CSV = os.path.join(DATA_DIR, 'seismic_data_faults.csv')

    context = {}

    try:
        df_general = pd.read_csv(GENERAL_CSV)
        df_taipei = pd.read_csv(TAIPEI_CSV)
        df_faults = pd.read_csv(FAULTS_CSV)

        counties_general = df_general['County'].unique()
        counties_taipei = df_taipei['County'].unique()
        all_counties = sorted(list(set(list(counties_general) + list(counties_taipei))))
        context['counties'] = all_counties
    except FileNotFoundError as e:
        context[
            'error'] = f"錯誤：找不到資料檔案 '{e.filename}'。請確認檔案已放置於 'EqStaticAnalysis_TW/data/' 資料夾中。"
        return render(request, 'EqStaticAnalysis_TW/calculator.html', context)

    if request.method == 'POST':
        try:
            form_data = request.POST.copy()
            # ... (前面的資料處理保持不變) ...
            submitted_faults = {}
            faults_list_for_report = []
            for key, value in form_data.items():
                if key.startswith('fault_distance_'):
                    fault_name = key.replace('fault_distance_', '')
                    submitted_faults[fault_name] = value
                    faults_list_for_report.append({'name': fault_name.replace('_', ' '), 'distance': value})

            county = form_data.get('county')
            township = form_data.get('township')
            if not county or not township:
                raise ValueError("縣市及鄉鎮市區為必填選項。")

            location_data, is_taipei_special = None, False
            if county in ["新北市", "臺北市"]:
                taipei_township_data = df_taipei[(df_taipei['County'] == county) & (df_taipei['Township'] == township)]
                if not taipei_township_data.empty:
                    is_taipei_special = True
                    unique_villages = taipei_township_data['Village'].unique()
                    if len(unique_villages) == 1 and unique_villages[0] == "全區所有里":
                        location_data = taipei_township_data.iloc[0]
                        form_data['village'] = "全區所有里"
                    else:
                        village = form_data.get('village')
                        if not village: raise ValueError(f"請選擇'{township}'的里。")
                        result = taipei_township_data[taipei_township_data['Village'] == village]
                        if not result.empty: location_data = result.iloc[0]

            if location_data is None:
                result = df_general[(df_general['County'] == county) & (df_general['Township'] == township)]
                if not result.empty: location_data = result.iloc[0]

            if location_data is None: raise ValueError("查無此地點資料")

            final_Ss_params, ss_params_no_fault = {}, {}
            FaD, FvD, FaM, FvM, FaD_no_fault, FvD_no_fault = (None,) * 6
            SDS, SMS, T0D, T0M, SD1, SM1 = 0, 0, 0, 0, None, None
            SDS_no_fault, SD1_no_fault, T0D_no_fault = 0, 0, 0

            is_taipei_basin = is_taipei_special and location_data.get('Zone_Type') == "Basin"

            if is_taipei_basin:
                SDS = location_data['SDS']
                SMS = location_data['SMS']
                T0D = T0M = location_data['T0_sec']
                SDS_no_fault, T0D_no_fault = SDS, T0D
                is_near_fault = False
                SD1, SM1, SD1_no_fault = None, None, None
                ss_params_no_fault = {}
                ground_type = 0 # 台北盆地不適用地盤分類
            else:
                final_Ss_params = {'SsD': location_data['SsD'], 'S1D': location_data['S1D'],
                                   'SsM': location_data['SsM'], 'S1M': location_data['S1M']}

                ss_params_no_fault = {'SsD': location_data['SsD'], 'S1D': location_data['S1D'],
                                      'SsM': location_data['SsM'], 'S1M': location_data['S1M']}

                faults_str = location_data.get('Nearby_Faults')
                is_near_fault = pd.notna(faults_str)

                if is_near_fault:
                    faults_list = [f.strip() for f in faults_str.replace('、', ',').split(',')]
                    for fault in faults_list:
                        r_str = form_data.get(f'fault_distance_{fault}')
                        if not r_str: raise ValueError(f"請輸入至【{fault}】的距離。")
                        r = float(r_str)
                        fault_rules = df_faults[df_faults['Fault_Name'] == fault]
                        if fault_rules.empty: continue

                        matched_rule_group = None
                        township_rules = fault_rules[fault_rules['Region_Type'] == 'Township']
                        for _, rule in township_rules.iterrows():
                            if township in rule['Affected_Regions']:
                                region_key = rule['Affected_Regions']
                                matched_rule_group = township_rules[township_rules['Affected_Regions'] == region_key]
                                break

                        if matched_rule_group is None:
                            county_rules = fault_rules[fault_rules['Region_Type'] == 'County']
                            for _, rule in county_rules.iterrows():
                                if county in rule['Affected_Regions']:
                                    region_key = rule['Affected_Regions']
                                    matched_rule_group = county_rules[county_rules['Affected_Regions'] == region_key]
                                    break

                        if matched_rule_group is not None:
                            for param in ['SsD', 'S1D', 'SsM', 'S1M']:
                                param_row = matched_rule_group[matched_rule_group['Parameter'] == param]
                                if not param_row.empty:
                                    y_points = param_row[DISTANCE_COLUMNS].iloc[0].values.astype(float)
                                    adjusted_val = interpolate(DISTANCE_POINTS, y_points, r)
                                    final_Ss_params[param] = max(final_Ss_params[param], adjusted_val)

                ground_type = int(form_data.get('ground_type', 2))

                FaD, FvD = get_site_amplification_factors(final_Ss_params['SsD'], final_Ss_params['S1D'], ground_type)
                SDS, SD1 = FaD * final_Ss_params['SsD'], FvD * final_Ss_params['S1D']
                FaM, FvM = get_site_amplification_factors(final_Ss_params['SsM'], final_Ss_params['S1M'], ground_type)
                SMS, SM1 = FaM * final_Ss_params['SsM'], FvM * final_Ss_params['S1M']
                FaD_no_fault, FvD_no_fault = get_site_amplification_factors(ss_params_no_fault['SsD'],
                                                                            ss_params_no_fault['S1D'], ground_type)
                SDS_no_fault, SD1_no_fault = FaD_no_fault * ss_params_no_fault['SsD'], FvD_no_fault * \
                                             ss_params_no_fault['S1D']
                T0D, T0M, T0D_no_fault = (SD1 / SDS if SDS > 0 else 0), (SM1 / SMS if SMS > 0 else 0), (
                    SD1_no_fault / SDS_no_fault if SDS_no_fault > 0 else 0)

            hn = float(form_data.get('hn'))
            structure_type_str = form_data.get('structure_type')
            T_empirical = calculate_empirical_period(hn, structure_type_str)
            T_limit = 1.4 * T_empirical
            Tx = float(form_data.get('Tx') or T_empirical)
            if Tx > T_limit: Tx = T_limit
            Ty = float(form_data.get('Ty') or T_empirical)
            if Ty > T_limit: Ty = T_limit

            if is_taipei_basin:
                SaDX, SaDY = calculate_Sa_taipei(SDS, Tx, T0D), calculate_Sa_taipei(SDS, Ty, T0D)
                SaDX_no_fault, SaDY_no_fault = SaDX, SaDY
                SaMX, SaMY = calculate_Sa_taipei(SMS, Tx, T0M), calculate_Sa_taipei(SMS, Ty, T0M)
            else:
                SaDX, SaDY = calculate_Sa_general(SDS, SD1, Tx, T0D), calculate_Sa_general(SDS, SD1, Ty, T0D)
                SaDX_no_fault, SaDY_no_fault = calculate_Sa_general(SDS_no_fault, SD1_no_fault, Tx,
                                                                    T0D_no_fault), calculate_Sa_general(SDS_no_fault,
                                                                                                        SD1_no_fault,
                                                                                                        Ty,
                                                                                                        T0D_no_fault)
                SaMX, SaMY = calculate_Sa_general(SMS, SM1, Tx, T0M), calculate_Sa_general(SMS, SM1, Ty, T0M)

            I = float(form_data.get('usage_factor'))
            Rx, Ry = float(form_data.get('Rx')), float(form_data.get('Ry'))
            alpha_y_choice = form_data.get('alpha_y_choice')
            alpha_y = 0.0
            if structure_type_str == '1':
                if alpha_y_choice == 'asd':
                    alpha_y = 1.2
                else:
                    alpha_y = 1.0
            elif structure_type_str == '2':
                if alpha_y_choice == 'general':
                    alpha_y = 1.5
                else:
                    alpha_y = 1.0
            elif structure_type_str == '3':
                alpha_y = float(form_data.get('alpha_y_manual'))

            FuDX, RaX = calculate_Fu(Rx, Tx, T0D, is_taipei_basin, 1)
            FuDY, RaY = calculate_Fu(Ry, Ty, T0D, is_taipei_basin, 1)
            FuMX, _ = calculate_Fu(Rx, Tx, T0M, is_taipei_basin, 2)
            FuMY, _ = calculate_Fu(Ry, Ty, T0M, is_taipei_basin, 2)
            FuDX_no_fault, _ = calculate_Fu(Rx, Tx, T0D_no_fault, is_taipei_basin, 1)
            FuDY_no_fault, _ = calculate_Fu(Ry, Ty, T0D_no_fault, is_taipei_basin, 1)

            SaD_over_FuD_m_X = calculate_Sa_over_Fu_m(SaDX, FuDX)
            SaD_over_FuD_m_Y = calculate_Sa_over_Fu_m(SaDY, FuDY)
            SaD_over_FuD_m_X_no_fault = calculate_Sa_over_Fu_m(SaDX_no_fault, FuDX_no_fault)
            SaD_over_FuD_m_Y_no_fault = calculate_Sa_over_Fu_m(SaDY_no_fault, FuDY_no_fault)
            SaM_over_FuM_m_X = calculate_Sa_over_Fu_m(SaMX, FuMX)
            SaM_over_FuM_m_Y = calculate_Sa_over_Fu_m(SaMY, FuMY)

            ratio_SaDX_FuDX = SaDX / FuDX if FuDX != 0 else 0
            ratio_SaDY_FuDY = SaDY / FuDY if FuDY != 0 else 0
            ratio_SaDX_no_fault_FuDX_no_fault = SaDX_no_fault / FuDX_no_fault if FuDX_no_fault != 0 else 0
            ratio_SaDY_no_fault_FuDY_no_fault = SaDY_no_fault / FuDY_no_fault if FuDY_no_fault != 0 else 0
            ratio_SaMX_FuMX = SaMX / FuMX if FuMX != 0 else 0
            ratio_SaMY_FuMY = SaMY / FuMY if FuMY != 0 else 0

            vertical_ratio = 2 / 3 if is_near_fault else 1 / 2
            C_VX, C_VY = (I / (1.4 * alpha_y)) * SaD_over_FuD_m_X, (I / (1.4 * alpha_y)) * SaD_over_FuD_m_Y
            V_star_divisor = 3.5 if is_taipei_basin else 4.2
            C_V_star_X = (I * FuDX_no_fault / (V_star_divisor * alpha_y)) * SaD_over_FuD_m_X_no_fault
            C_V_star_Y = (I * FuDY_no_fault / (V_star_divisor * alpha_y)) * SaD_over_FuD_m_Y_no_fault
            C_VMX, C_VMY = (I / (1.4 * alpha_y)) * SaM_over_FuM_m_X, (I / (1.4 * alpha_y)) * SaM_over_FuM_m_Y

            v_mode = form_data.get('vertical_mode')
            Rv = 3.0

            SaDVX, SaDVY, FuvX, FuvY = 0, 0, 0, 0
            RavX, RavY = 0, 0

            FuDVX, _ = calculate_Fu(Rv, Tx, T0D, is_taipei_basin, 1)
            FuDVY, _ = calculate_Fu(Rv, Ty, T0D, is_taipei_basin, 1)

            # --- 【核心修改】移除 v_mode 判斷，永遠採標準模式 ---
            Rv = 3.0
            SaDVX, SaDVY = SaDX * vertical_ratio, SaDY * vertical_ratio

            FuvX, RavX = calculate_Fu(Rv, Tx, T0D, is_taipei_basin, 1)
            FuvY, RavY = calculate_Fu(Rv, Ty, T0D, is_taipei_basin, 1)

            SaDV_over_Fuv_m_X = calculate_SaDV_over_Fuv_m(SaDVX, FuvX, is_near_fault)
            SaDV_over_Fuv_m_Y = calculate_SaDV_over_Fuv_m(SaDVY, FuvY, is_near_fault)
            C_VZX_D = (I / (1.4 * alpha_y)) * SaDV_over_Fuv_m_X
            C_VZY_D = (I / (1.4 * alpha_y)) * SaDV_over_Fuv_m_Y

            ratio_SaDVX_FuDVX = SaDVX / FuvX if FuvX != 0 else 0
            ratio_SaDVY_FuDVY = SaDVY / FuvY if FuvY != 0 else 0

            SaDVX_no_fault, SaDVY_no_fault = SaDX_no_fault * (1 / 2), SaDY_no_fault * (1 / 2)
            FuvX_no_fault, _ = calculate_Fu(Rv, Tx, T0D_no_fault, is_taipei_basin, 1)
            FuvY_no_fault, _ = calculate_Fu(Rv, Ty, T0D_no_fault, is_taipei_basin, 1)
            SaDV_over_Fuv_m_X_no_fault = calculate_SaDV_over_Fuv_m(SaDVX_no_fault, FuvX_no_fault, False)
            SaDV_over_Fuv_m_Y_no_fault = calculate_SaDV_over_Fuv_m(SaDVY_no_fault, FuvY_no_fault, False)

            ratio_SaDVX_no_fault_FuDVX_no_fault = SaDVX_no_fault / FuvX_no_fault if FuvX_no_fault != 0 else 0
            ratio_SaDVY_no_fault_FuDVY_no_fault = SaDVY_no_fault / FuvY_no_fault if FuvY_no_fault != 0 else 0

            C_V_star_ZX = (I * FuvX_no_fault / (V_star_divisor * alpha_y)) * SaDV_over_Fuv_m_X_no_fault
            C_V_star_ZY = (I * FuvY_no_fault / (V_star_divisor * alpha_y)) * SaDV_over_Fuv_m_Y_no_fault

            SaMVX, SaMVY = SaMX * vertical_ratio, SaMY * vertical_ratio

            # --- 【核心修正】將 FuMVX 和 FuMVY 的變數名統一 ---
            FuMVX, _ = calculate_Fu(Rv, Tx, T0M, is_taipei_basin, 2)
            FuMVY, _ = calculate_Fu(Rv, Ty, T0M, is_taipei_basin, 2)

            # --- 【核心修正】使用統一後的變數名計算後續值 ---
            SaMV_over_FuvM_m_X = calculate_SaDV_over_Fuv_m(SaMVX, FuMVX, is_near_fault)
            SaMV_over_FuvM_m_Y = calculate_SaDV_over_Fuv_m(SaMVY, FuMVY, is_near_fault)

            ratio_SaMVX_FuMVX = SaMVX / FuMVX if FuMVX != 0 else 0
            ratio_SaMVY_FuMVY = SaMVY / FuMVY if FuMVY != 0 else 0

            C_VMZX, C_VMZY = (I / (1.4 * alpha_y)) * SaMV_over_FuvM_m_X, (I / (1.4 * alpha_y)) * SaMV_over_FuvM_m_Y

            # --- 【核心修改】將 C_design 的計算邏輯擴充 ---
            final_CzD = max(C_VZX_D, C_VZY_D)
            final_Cz_star = max(C_V_star_ZX, C_V_star_ZY)
            final_CzM = max(C_VMZX, C_VMZY)

            if is_near_fault:
                C_column = (0.80 * SDS * I) / (3 * alpha_y)
            else:
                C_column = (0.40 * SDS * I) / (2 * alpha_y)

            C_design_X = max(C_VX, C_V_star_X, C_VMX)
            C_design_Y = max(C_VY, C_V_star_Y, C_VMY)
            C_design_Z = max(final_CzD, final_Cz_star, final_CzM)

            context['results'] = {
                'county': county, 'township': township, 'village': form_data.get('village', ''), 'hn': hn,
                'structure_type': structure_type_str,
                'T_empirical': T_empirical,
                'T_limit': T_limit,
                'Tx': Tx, 'Ty': Ty, 'I': I, 'Rx': Rx, 'Ry': Ry, 'alpha_y': alpha_y,
                'alpha_y_choice': form_data.get('alpha_y_choice'), 'vertical_mode': v_mode,
                'is_taipei_basin': is_taipei_basin, 'is_near_fault': is_near_fault,
                'zone_name': location_data.get('Zone_Name', '一般震區'),
                'ground_type': ground_type,
                'faults_data_for_report': faults_list_for_report,
                'ss_params_no_fault_SsD': ss_params_no_fault.get('SsD'),
                'ss_params_no_fault_S1D': ss_params_no_fault.get('S1D'),
                'ss_params_no_fault_SsM': ss_params_no_fault.get('SsM'),
                'ss_params_no_fault_S1M': ss_params_no_fault.get('S1M'),
                'final_Ss_params_SsD': final_Ss_params.get('SsD'), 'final_Ss_params_S1D': final_Ss_params.get('S1D'),
                'final_Ss_params_SsM': final_Ss_params.get('SsM'), 'final_Ss_params_S1M': final_Ss_params.get('S1M'),
                'FaD': FaD, 'FvD': FvD, 'FaM': FaM, 'FvM': FvM, 'FaD_no_fault': FaD_no_fault,
                'FvD_no_fault': FvD_no_fault,
                'SDS': SDS, 'SD1': SD1, 'SMS': SMS, 'SM1': SM1, 'SDS_no_fault': SDS_no_fault,
                'SD1_no_fault': SD1_no_fault,
                'T0D': T0D, 'T0M': T0M, 'T0D_no_fault': T0D_no_fault, 'SaDX': SaDX, 'SaDY': SaDY, 'SaMX': SaMX,
                'SaMY': SaMY,
                'SaDX_no_fault': SaDX_no_fault, 'SaDY_no_fault': SaDY_no_fault,
                'ratio_SaDX_FuDX': ratio_SaDX_FuDX, 'ratio_SaDY_FuDY': ratio_SaDY_FuDY,
                'ratio_SaDX_no_fault_FuDX_no_fault': ratio_SaDX_no_fault_FuDX_no_fault,
                'ratio_SaDY_no_fault_FuDY_no_fault': ratio_SaDY_no_fault_FuDY_no_fault,
                'ratio_SaMX_FuMX': ratio_SaMX_FuMX, 'ratio_SaMY_FuMY': ratio_SaMY_FuMY,
                'RaX': RaX, 'RaY': RaY, 'FuDX': FuDX, 'FuDY': FuDY, 'FuMX': FuMX, 'FuMY': FuMY,
                'FuDX_no_fault': FuDX_no_fault, 'FuDY_no_fault': FuDY_no_fault,
                'SaD_over_FuD_m_X': SaD_over_FuD_m_X, 'SaD_over_FuD_m_Y': SaD_over_FuD_m_Y,
                'SaD_over_FuD_m_X_no_fault': SaD_over_FuD_m_X_no_fault,
                'SaD_over_FuD_m_Y_no_fault': SaD_over_FuD_m_Y_no_fault,
                'SaM_over_FuM_m_X': SaM_over_FuM_m_X, 'SaM_over_FuM_m_Y': SaM_over_FuM_m_Y,
                'C_VX': C_VX, 'C_VY': C_VY, 'C_V_star_X': C_V_star_X, 'C_V_star_Y': C_V_star_Y, 'C_VMX': C_VMX,
                'C_VMY': C_VMY,
                'C_VZX_D': C_VZX_D, 'C_VZY_D': C_VZY_D, 'C_V_star_ZX': C_V_star_ZX, 'C_V_star_ZY': C_V_star_ZY,
                'C_VMZX': C_VMZX, 'C_VMZY': C_VMZY, 'C_column': C_column, 'C_design_X': C_design_X,
                'C_design_Y': C_design_Y,
                # --- 【核心新增】將新的 Z 向變數加入 context ---
                'final_CzD': final_CzD,
                'final_Cz_star': final_Cz_star,
                'C_design_Z': C_design_Z,
                'final_CzM': final_CzM,
                'vertical_ratio': vertical_ratio, 'SaDVX': SaDVX, 'SaDVY': SaDVY, 'SaMVX': SaMVX, 'SaMVY': SaMVY,
                'SaDVX_no_fault': SaDVX_no_fault, 'SaDVY_no_fault': SaDVY_no_fault,
                'Rv': Rv, 'RavX': RavX, 'RavY': RavY,
                'FuDVX': FuDVX, 'FuDVY': FuDVY,
                'FuMVX': FuMVX, 'FuMVY': FuMVY,
                'FuvX': FuvX, 'FuvY': FuvY,
                'FuvX_no_fault': FuvX_no_fault, 'FuvY_no_fault': FuvY_no_fault,
                'SaDV_over_Fuv_m_X': SaDV_over_Fuv_m_X, 'SaDV_over_Fuv_m_Y': SaDV_over_Fuv_m_Y,
                'ratio_SaDVX_FuDVX': ratio_SaDVX_FuDVX,
                'ratio_SaDVY_FuDVY': ratio_SaDVY_FuDVY,
                'ratio_SaDVX_no_fault_FuDVX_no_fault': ratio_SaDVX_no_fault_FuDVX_no_fault,
                'ratio_SaDVY_no_fault_FuDVY_no_fault': ratio_SaDVY_no_fault_FuDVY_no_fault,
                'ratio_SaMVX_FuMVX': ratio_SaMVX_FuMVX,
                'ratio_SaMVY_FuMVY': ratio_SaMVY_FuMVY,
                'SaDV_over_Fuv_m_X_no_fault': SaDV_over_Fuv_m_X_no_fault,
                'SaDV_over_Fuv_m_Y_no_fault': SaDV_over_Fuv_m_Y_no_fault,
                'SaMV_over_FuvM_m_X': SaMV_over_FuvM_m_X, 'SaMV_over_FuvM_m_Y': SaMV_over_FuvM_m_Y,
            }
            context['submitted_data'] = form_data
            context['submitted_faults'] = submitted_faults

        except Exception as e:
            traceback.print_exc()
            context['error'] = f"計算過程中發生錯誤: {e}。請檢查所有必填欄位是否已正確填寫。"
            context['submitted_data'] = request.POST

    return render(request, 'EqStaticAnalysis_TW/calculator.html', context)


# ... (report_view, get_townships, check_faults, get_villages 保持不變) ...
def report_view(request):
    context = {'results': None, 'report_type': 'general'}

    if request.method == 'POST':
        def _clean_value(value):
            if value is None or value == '':
                return None
            val_lower = value.lower()
            if val_lower == 'true':
                return True
            if val_lower == 'false':
                return False
            try:
                return float(value)
            except (ValueError, TypeError):
                return value

        results_dict = {key: _clean_value(value) for key, value in request.POST.items()}

        village_value = results_dict.get('village')
        if not village_value or village_value == '全区所有里':
            results_dict['village'] = ''

        faults_data_for_report = []
        i = 0
        while True:
            name_key = f'fault_{i}_name'
            dist_key = f'fault_{i}_distance'
            if name_key in results_dict and dist_key in results_dict:
                faults_data_for_report.append({
                    'name': results_dict[name_key],
                    'distance': results_dict[dist_key]
                })
                i += 1
            else:
                break
        results_dict['faults_data_for_report'] = faults_data_for_report

        is_taipei = results_dict.get('is_taipei_basin', False)
        is_near = results_dict.get('is_near_fault', False)

        report_type = 'general'
        if is_taipei:
            report_type = 'taipei'
        elif is_near:
            report_type = 'near_fault'

        context = {
            'results': results_dict,
            'report_type': report_type,
            'request': request  # 【重要】將 request 物件本身傳遞給模板
        }

    return render(request, 'EqStaticAnalysis_TW/eqTW_report.html', context)


def get_townships(request, county):
    DATA_DIR = os.path.join(settings.BASE_DIR, 'EqStaticAnalysis_TW', 'data')
    GENERAL_CSV, TAIPEI_CSV = os.path.join(DATA_DIR, 'seismic_data_general.csv'), os.path.join(DATA_DIR,
                                                                                               'seismic_data_taipei_special.csv')
    df_general, df_taipei = pd.read_csv(GENERAL_CSV), pd.read_csv(TAIPEI_CSV)
    townships = set()
    if county in df_general['County'].unique(): townships.update(
        df_general[df_general['County'] == county]['Township'].unique())
    if county in df_taipei['County'].unique(): townships.update(
        df_taipei[df_taipei['County'] == county]['Township'].unique())
    return JsonResponse({'townships': sorted(list(townships))})


def check_faults(request, county, township):
    DATA_DIR = os.path.join(settings.BASE_DIR, 'EqStaticAnalysis_TW', 'data')
    GENERAL_CSV = os.path.join(DATA_DIR, 'seismic_data_general.csv')
    df_general = pd.read_csv(GENERAL_CSV)
    result = df_general[(df_general['County'] == county) & (df_general['Township'] == township)]
    if not result.empty:
        faults_str = result.iloc[0]['Nearby_Faults']
        if pd.notna(faults_str):
            faults_list = [f.strip() for f in faults_str.replace('、', ',').split(',')]
            return JsonResponse({'faults': faults_list})
    return JsonResponse({'faults': []})


def get_villages(request, county, township):
    DATA_DIR = os.path.join(settings.BASE_DIR, 'EqStaticAnalysis_TW', 'data')
    TAIPEI_CSV = os.path.join(DATA_DIR, 'seismic_data_taipei_special.csv')
    df_taipei = pd.read_csv(TAIPEI_CSV)

    villages = []
    is_all_villages = False

    data = df_taipei[(df_taipei['County'] == county) & (df_taipei['Township'] == township)]
    if not data.empty:
        unique_villages = data['Village'].unique()
        if len(unique_villages) == 1 and unique_villages[0] == "全區所有里":
            is_all_villages = True
        else:
            villages = sorted(list(unique_villages))

    return JsonResponse({'villages': villages, 'is_all_villages': is_all_villages})

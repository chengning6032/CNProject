# Wind_TW/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import pandas as pd
import numpy as np
import os
import json
import math  # 確保引入 math 模組
from . import wind_calculations
from . import services


def wind_calculation_close_view(request):
    # ... (此函式內容完全不變，用於顯示頁面) ...
    csv_path = os.path.join(settings.BASE_DIR, 'Wind_TW/data/', 'BASIC_WIND_SPEEDS.csv')
    context = {'counties': [], 'wind_speeds_json': '[]', 'error_message': None}
    try:
        df = pd.read_csv(csv_path, header=None, names=['county', 'town', 'speed'], encoding='utf-8-sig')
        df['county'] = df['county'].str.strip()
        df['town'] = df['town'].str.strip()
        counties = sorted(df['county'].unique())
        wind_speeds_json = df.to_json(orient='records', force_ascii=False)
        context.update({'counties': counties, 'wind_speeds_json': wind_speeds_json})
    except Exception as e:
        context['error_message'] = f"讀取風速資料時發生錯誤: {e}"
    return render(request, 'Wind_TW/wind_calculation_close.html', context)


def wind_calculation_open_view(request):
    # ... (此函式內容完全不變，用於顯示頁面) ...
    csv_path = os.path.join(settings.BASE_DIR, 'Wind_TW/data/', 'BASIC_WIND_SPEEDS.csv')
    context = {'counties': [], 'wind_speeds_json': '[]', 'error_message': None}
    try:
        df = pd.read_csv(csv_path, header=None, names=['county', 'town', 'speed'], encoding='utf-8-sig')
        df['county'] = df['county'].str.strip()
        df['town'] = df['town'].str.strip()
        counties = sorted(df['county'].unique())
        wind_speeds_json = df.to_json(orient='records', force_ascii=False)
        context.update({'counties': counties, 'wind_speeds_json': wind_speeds_json})
    except Exception as e:
        context['error_message'] = f"讀取風速資料時發生錯誤: {e}"
    return render(request, 'Wind_TW/wind_calculation_open.html', context)


def calculate_api_view(request):
    """
    封閉式建築計算 API (重構後)
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '僅接受 POST 請求'}, status=405)

    try:
        data = json.loads(request.body)

        # 使用與開放式建築相同的 Service 入口！
        # 因為 process_calculation_request 已經能夠處理所有類型
        result = services.process_calculation_request(data)

        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc() # 務必確保這行有執行
        print(f"API Error: {e}") # 加上這行以便除錯
        return JsonResponse({'status': 'error', 'message': f'後端處理錯誤: {str(e)}'}, status=500)


# def wind_report_view(request):
#     """
#     接收 GET 请求中的参数，渲染獨立的報告書頁面。
#     【核心修正】: 精修 Shed 屋頂在第五章的示意圖判斷邏輯。
#     """
#     get_params = request.GET
#     db = wind_calculations.setup_databases()
# 
#     # --- 參數準備 (此部分不變) ---
#     site_location = f"{get_params.get('county', '未知')} {get_params.get('town', '')}".strip()
# 
#     b_x = float(get_params.get('dim_x', 0))
#     b_y = float(get_params.get('dim_y', 0))
#     h_eave = float(get_params.get('eave_height', 0))
#     h_ridge = float(get_params.get('ridge_height', 0))
#     roof_shape = get_params.get('roof_shape')
#     ridge_dir = get_params.get('ridge_direction', 'X')  # 預設 X
# 
#     calculated_theta = 0.0
#     calculated_theta_x = 0.0
#     calculated_theta_y = 0.0
# 
#     delta_h = h_ridge - h_eave
#     print(delta_h, "眉")
# 
#     # 只有當屋脊高 > 屋簷高時才計算角度，否則為 0 (平屋頂)
#     if delta_h > 0.01:
#         # Case A: 四坡水 (Hip) - 需分別計算 X 與 Y 向角度
#         if roof_shape == 'hip':
#             # 依據 hip_roof_options 邏輯 (簡化版：假設對稱)
#             # X向角度: 對應 Y 邊長的一半 (tan = h / (By/2)) ??
#             # 不，幾何上:
#             # X向視圖看到的斜面，其底邊長度是 By 沒錯，但計算角度的底邊是 (By - Top_By)/2
#             # 這裡我們採用簡化假設：屋頂頂點在中心
# 
#             if b_y > 0:
#                 calculated_theta_x = math.degrees(math.atan(delta_h / (b_y / 2)))
#             if b_x > 0:
#                 calculated_theta_y = math.degrees(math.atan(delta_h / (b_x / 2)))
# 
#             # 為了通用參數顯示，取兩者較大值作為代表 θ
#             calculated_theta = max(calculated_theta_x, calculated_theta_y)
# 
#         # Case B: 單斜 (Shed) - 底邊為全長
#         elif roof_shape == 'shed':
#             # 判斷跨度方向
#             span = b_y if ridge_dir == 'X' else b_x
#             if span > 0:
#                 calculated_theta = math.degrees(math.atan(delta_h / span))
# 
#         # Case C: 山形 (Gable) / 拱形 (Arched) / 鋸齒 (Sawtooth) - 底邊為半長
#         # 注意: Sawtooth 若為多跨，應除以跨數，這裡暫以單跨或總寬計算，
#         # 若前端傳來的是單跨寬度則正確，若傳總寬需除以 num_spans
#         else:
#             span = b_y if ridge_dir == 'X' else b_x
# 
#             # 若為鋸齒且有多跨，需修正 span
#             if roof_shape == 'sawtooth_uniform':
#                 num_spans = int(get_params.get('num_spans', 1))
#                 if num_spans > 0:
#                     span = span / num_spans
# 
#             if span > 0:
#                 calculated_theta = math.degrees(math.atan(delta_h / (span / 2)))
# 
#     # ==== ▲▲▲ END: 角度重算結束 ▲▲▲ ====
#     calculated_h = float(get_params.get('calculated_h', 0))
# 
#     terrain_category = get_params.get('terrain', 'C')
#     terrain_params = wind_calculations.get_terrain_parameters(terrain_category, db)
#     roof_shape_en = get_params.get('roof_shape')
#     roof_shape_map = {'flat': '平屋頂', 'gable': '雙邊單斜式(山形)屋頂', 'shed': '單邊單斜式屋頂',
#                       'hip': '雙斜(四坡水)屋頂', 'arched': '拱形屋頂', 'sawtooth_uniform': '鋸齒型屋頂 (一致)',
#                       'sawtooth_irregular': '不規則鋸齒型屋頂'}
#     ridge_dir_en = get_params.get('ridge_direction', 'null')
#     ridge_dir_zh = f"{ridge_dir_en}向" if ridge_dir_en in ['X', 'Y'] else '不適用'
#     ridge_len_str = get_params.get('ridge_length', 'N/A')
#     ridge_len_display = f"{ridge_len_str} m" if ridge_len_str != 'N/A' else '不適用'
#     calculated_h = float(get_params.get('calculated_h', 0))
# 
#     full_params = {
#         'B_X': b_x,
#         'B_Y': b_y,
#         'eave_height': h_eave,
#         'ridge_height': h_ridge,
#         'h': calculated_h,
#         'roof_type': roof_shape_en,
#         'terrain': terrain_category,
#         'I': float(get_params.get('importance_factor', 0)),
#         'V10_C': float(get_params.get('v10c', 0)),
#         'beta': float(get_params.get('damping_ratio', 0)),
# 
#         'theta': calculated_theta,
#         'theta_X': calculated_theta_x,
#         'theta_Y': calculated_theta_y,
# 
#         'ridge_orientation': ridge_dir_en if ridge_dir_en in ['X', 'Y'] else None,
# 
#         'hip_roof_options': {'topType': 'ridge'}, 'fn_X': float(get_params.get('fn_x', 0)),
#         'fn_Y': float(get_params.get('fn_y', 0)), 'ft': float(get_params.get('ft', 0)),
#         'enclosure_status': get_params.get('enclosure_status', '部分封閉式建築'),
#         'topo_x_type': get_params.get('topo_x_type'), 'topo_x_h': get_params.get('topo_x_h', 0),
#         'topo_x_lh': get_params.get('topo_x_lh', 0), 'topo_x_x': get_params.get('topo_x_x', 0),
#         'topo_y_type': get_params.get('topo_y_type'), 'topo_y_h': get_params.get('topo_y_h', 0),
#         'topo_y_lh': get_params.get('topo_y_lh', 0), 'topo_y_x': get_params.get('topo_y_x', 0),
#         'has_overhang': get_params.get('has_overhang', 'false').lower() == 'true',
#         'num_spans': int(get_params.get('num_spans', 1)),
#         'use_asce7_c_and_c': get_params.get('use_asce7_c_and_c', 'false').lower() == 'true',
#         'segmentHeight': float(get_params.get('segment_height', 2.0)),
#         'simplify_gable': get_params.get('simplify_gable', 'true').lower() == 'true',
#     }
# 
#     geometry_params = {'dim_x': full_params['B_X'], 'dim_y': full_params['B_Y'], 'roof_shape_en': roof_shape_en,
#                        'roof_shape_zh': roof_shape_map.get(roof_shape_en, '未知'),
#                        'eave_height': full_params['eave_height'], 'ridge_height': full_params['ridge_height'],
#                        'calculated_h': full_params['h'], 'ridge_direction': ridge_dir_zh,
#                        'ridge_length': ridge_len_display, 'theta': full_params['theta'],
#                        'theta_x': full_params['theta_X'], 'theta_y': full_params['theta_Y'], }
#     basic_params = {'enclosure_status': full_params['enclosure_status'], 'importance_factor': full_params['I'],
#                     'damping_ratio': full_params['beta'], 'fn_x': full_params['fn_X'], 'fn_y': full_params['fn_Y'],
#                     'ft': full_params['ft'], }
#     landform_map_en_to_zh = {'hill': '山丘', 'ridge': '山脊', 'escarpment': '懸崖'}
# 
#     def process_topo_data(axis: str):
#         # ... (此內部函式不變) ...
#         topo_type = get_params.get(f'topo_{axis}_type')
#         if topo_type == 'not_considered': return {'type_display': '未考量特殊地形', 'H': 0, 'Lh': 0, 'x': 0,
#                                                   'H_Lh': 'N/A', 'x_Lh_pair': 'N/A', 'z_Lh_max': 'N/A', 'K1': 0,
#                                                   'K2_pair': "0.000 / 0.000", 'K3_max': 0, 'Kzt_pair': "1.000 / 1.000"}
#         H = float(get_params.get(f'topo_{axis}_h', 0));
#         Lh = float(get_params.get(f'topo_{axis}_lh', 0));
#         x_physical = float(get_params.get(f'topo_{axis}_x', 0));
#         landform = landform_map_en_to_zh.get(topo_type)
#         if Lh == 0: return {'type_display': landform, 'H': H, 'Lh': Lh, 'x': x_physical,
#                             'H_Lh': '∞' if H > 0 else '0.00', 'x_Lh_pair': 'N/A', 'z_Lh_max': 'N/A', 'K1': 0,
#                             'K2_pair': "N/A", 'K3_max': 0, 'Kzt_pair': "1.000 / 1.000"}
#         x_calc_pos = x_physical;
#         x_calc_neg = -x_physical
#         params_pos = {'H': H, 'Lh': Lh, 'x': x_calc_pos, 'terrain': terrain_category, 'landform': landform}
#         kzt_pos, k1, k2_pos, k3_max = wind_calculations.calculate_topography_factor(params_pos, calculated_h, db)
#         params_neg = {'H': H, 'Lh': Lh, 'x': x_calc_neg, 'terrain': terrain_category, 'landform': landform}
#         kzt_neg, _, k2_neg, _ = wind_calculations.calculate_topography_factor(params_neg, calculated_h, db)
#         return {'type_display': landform, 'H': H, 'Lh': Lh, 'x': x_physical, 'H_Lh': f"{H / Lh:.3f}",
#                 'x_Lh_pair': f"{x_calc_pos / Lh:.3f} / {x_calc_neg / Lh:.3f}", 'z_Lh_max': f"{calculated_h / Lh:.3f}",
#                 'K1': k1, 'K2_pair': f"{k2_pos:.3f} / {k2_neg:.3f}", 'K3_max': k3_max,
#                 'Kzt_pair': f"{kzt_pos:.3f} / {kzt_neg:.3f}"}
# 
#     topo_x_data_ch2 = process_topo_data('x');
#     topo_y_data_ch2 = process_topo_data('y')
#     building_image_path = None;
#     has_overhang = full_params['has_overhang']
#     if roof_shape_en == 'flat':
#         building_image_path = 'img/Flat_roof_building.png'
#     elif roof_shape_en in ['gable', 'hip']:
#         overhang_suffix = '_overhang' if has_overhang else ''
#         if ridge_dir_en in ['X',
#                             'Y']: building_image_path = f'img/{roof_shape_en.capitalize()}_roof_{ridge_dir_en}_ridge{overhang_suffix}_building.png'
#     elif roof_shape_en == 'arched':
#         if ridge_dir_en in ['X', 'Y']: building_image_path = f'img/Arched_roof_{ridge_dir_en}_ridge_building.png'
#     elif roof_shape_en == 'shed':
#         if ridge_dir_en in ['X', 'Y']: building_image_path = f'img/Shed_roof_{ridge_dir_en}_ridge_building.png'
#     elif roof_shape_en == 'sawtooth_uniform':
#         if ridge_dir_en in ['X',
#                             'Y']: building_image_path = f'img/Sawtooth_uniform_roof_{ridge_dir_en}_ridge_building.png'
# 
#     topo_images = []
#     topo_image_map = {
#         'hill': 'img/hill.png',
#         'ridge': 'img/ridge.png',
#         'escarpment': 'img/escarpment.png'
#     }
#     landform_zh_map = {'hill': '山丘', 'ridge': '山脊', 'escarpment': '懸崖'}
# 
#     # 檢查 X 向地形
#     topo_x_type = get_params.get('topo_x_type')
#     if topo_x_type in topo_image_map:
#         topo_images.append({
#             'path': topo_image_map[topo_x_type],
#             'caption': f'X向地形示意 ({landform_zh_map.get(topo_x_type)})'
#         })
# 
#     # 檢查 Y 向地形
#     topo_y_type = get_params.get('topo_y_type')
#     if topo_y_type in topo_image_map:
#         topo_images.append({
#             'path': topo_image_map[topo_y_type],
#             'caption': f'Y向地形示意 ({landform_zh_map.get(topo_y_type)})'
#         })
# 
#     chapter_4_data = {'gcpi': wind_calculations.calculate_gcpi_coeff(full_params['enclosure_status'], db)}
# 
#     def get_analysis_params_ch4(wind_dir, sign):
#         case_params = full_params.copy()
#         if wind_dir == 'X':
#             case_params['L'], case_params['B'], case_params['fn'] = case_params['B_X'], case_params['B_Y'], case_params[
#                 'fn_X']
#         else:
#             case_params['L'], case_params['B'], case_params['fn'] = case_params['B_Y'], case_params['B_X'], case_params[
#                 'fn_Y']
#         topo_type = get_params.get(f'topo_{wind_dir.lower()}_type');
#         is_topo = topo_type != 'not_considered';
#         topo_calc_params = {}
#         if is_topo:
#             x_physical = float(get_params.get(f'topo_{wind_dir.lower()}_x', 0));
#             topo_calc_params = {'H': float(get_params.get(f'topo_{wind_dir.lower()}_h', 0)),
#                                 'Lh': float(get_params.get(f'topo_{wind_dir.lower()}_lh', 0)),
#                                 'x': x_physical if sign == 'positive' else -x_physical, 'terrain': terrain_category,
#                                 'landform': landform_map_en_to_zh.get(topo_type)}
#         kzt_at_h = wind_calculations.calculate_topography_factor(topo_calc_params, case_params['h'], db)[
#             0] if is_topo else 1.0
#         rigidity = '柔性' if case_params.get('fn', 1.0) < 1.0 else '普通'
#         common_gust_params = wind_calculations.calculate_gust_common_params(case_params, db)
#         g_factor = wind_calculations.calculate_Gf_factor(case_params, common_gust_params,
#                                                          db) if rigidity == '柔性' else wind_calculations.calculate_G_factor(
#             case_params, common_gust_params)
#         wall_cp = wind_calculations.calculate_wall_coeffs(case_params['L'], case_params['B'], db);
#         # ==== ▼▼▼ START: 【核心修正】第四章不進行篩選 ▼▼▼ ====
#         roof_cp = wind_calculations.calculate_roof_coeffs(case_params, db, wind_dir, sign, filter_by_sign=False)
#         # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====
# 
#         # roof_cp_zh = {}
#         # for k, v in dir_result['roof_cp'].items():
#         #     if k == 'Cp_flat':
#         #         k_zh = '平屋頂 C_p'
#         #     elif k == 'Cp_parallel':
#         #         k_zh = '平行屋脊 C_p'
#         #     elif k == 'windward_Cp':
#         #         k_zh = '迎風面 C_p'
#         #     elif k == 'leeward_Cp':
#         #         k_zh = '背風面 C_p'
#         #     elif k == 'windward_Cp_pos':
#         #         k_zh = '迎風面 C_p (+)'
#         #     elif k == 'windward_Cp_neg':
#         #         k_zh = '迎風面 C_p (-)'
#         #     else:
#         #         k_zh = k
#         #     roof_cp_zh[k_zh] = v
# 
#         return {
#             'rigidity': rigidity,
#             'B': case_params['B'],
#             'L': case_params['L'],
#             'G_factor': g_factor,  # 這是一個字典，包含 'final_value'
#             'L_B': case_params['L'] / case_params['B'] if case_params['B'] > 0 else 0,
#             'h_L': case_params['h'] / case_params['L'] if case_params['L'] > 0 else 0,
#             'h_B': case_params['h'] / case_params['B'] if case_params['B'] > 0 else 0,
# 
#             # 確保 wall_cp 字典正確傳遞
#             'Cp_windward': wall_cp.get('windward', 0.8),
#             'Cp_leeward': wall_cp.get('leeward', -0.5),
#             'Cp_side': wall_cp.get('side', -0.7),
# 
#             'roof_cp': roof_cp
#         }
# 
#     has_topo_x = get_params.get('topo_x_type') != 'not_considered';
#     has_topo_y = get_params.get('topo_y_type') != 'not_considered'
#     chapter_4_data['x_wind'] = {'has_neg_case': has_topo_x, 'pos': get_analysis_params_ch4('X', 'positive')}
#     if has_topo_x:
#         chapter_4_data['x_wind']['neg'] = get_analysis_params_ch4('X', 'negative');
#         chapter_4_data['x_wind'][
#             'pos_header'] = '順風向 (+X向)';
#         chapter_4_data['x_wind']['neg_header'] = '順風向 (-X向)'
#     else:
#         chapter_4_data['x_wind']['pos_header'] = '順風向 (±X向)'
#     chapter_4_data['y_wind'] = {'has_neg_case': has_topo_y, 'pos': get_analysis_params_ch4('Y', 'positive')}
#     if has_topo_y:
#         chapter_4_data['y_wind']['neg'] = get_analysis_params_ch4('Y', 'negative');
#         chapter_4_data['y_wind'][
#             'pos_header'] = '順風向 (+Y向)';
#         chapter_4_data['y_wind']['neg_header'] = '順風向 (-Y向)'
#     else:
#         chapter_4_data['y_wind']['pos_header'] = '順風向 (±Y向)'
# 
#     gcpi_values = wind_calculations.calculate_gcpi_coeff(full_params['enclosure_status'], db)
#     chapter_5_data = {}
# 
#     def get_detailed_case_data(wind_dir, sign):
#         tables = []
#         for gcpi in gcpi_values:
#             # ==== ▼▼▼ START: 【核心修正】第五章進行篩選 ▼▼▼ ====
#             # 這裡的 generate_report_table_data 內部會呼叫 calculate_roof_coeffs 並進行篩選
#             table_group_data = wind_calculations.generate_report_table_data(
#                 full_params, db, wind_dir, sign, specific_gcpi=gcpi, filter_roof_cp=True
#             )
#             # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====
#             table_group_data['gcpi'] = gcpi
#             tables.append(table_group_data)
# 
#         # 圖片與角度判斷邏輯 (保持不變)
#         ridge_orientation = full_params.get('ridge_orientation');
#         roof_type = full_params.get('roof_type');
#         is_parallel = (wind_dir == ridge_orientation) if roof_type != 'flat' else False
#         theta = 0.0;
#         theta_name = "θ";
#         image_for_case = None
#         direction_suffix = 'parallel' if is_parallel else 'vertical'
#         if roof_type == 'shed':
#             if is_parallel:
#                 side_suffix = "LH" if sign == 'positive' else "RH";
#                 image_for_case = f'img/Shed_roof_ridge_parallel_wind_{side_suffix}.png'
#             else:
#                 side_suffix = "L" if sign == 'positive' else "H";
#                 image_for_case = f'img/Shed_roof_ridge_vertical_wind_{side_suffix}.png'
#         elif roof_type in ['gable', 'arched', 'hip'] or roof_type.startswith('sawtooth'):
#             shape_name_map = {'gable': 'Gable', 'arched': 'Arched', 'hip': 'Hip', 'sawtooth_uniform': 'Sawtooth',
#                               'sawtooth_irregular': 'Sawtooth'}
#             shape_name = shape_name_map.get(roof_type)
#             if shape_name: image_for_case = f'img/{shape_name}_roof_ridge_{direction_suffix}_wind.png'
#         elif roof_type == 'flat':
#             image_for_case = 'img/Flat_roof_ridge_parallel_wind.png' if wind_dir == 'X' else 'img/Flat_roof_ridge_vertical_wind.png'
#         if roof_type == 'hip':
#             if wind_dir == 'Y':
#                 theta = full_params.get('theta_X', 0.0);
#                 theta_name = "θx"
#             else:
#                 theta = full_params.get('theta_Y', 0.0);
#                 theta_name = "θy"
#         elif roof_type != 'flat':
#             theta = full_params.get('theta', 0.0)
# 
#         # 其他計算 (保持不變)
#         topo_type = full_params.get(f'topo_{wind_dir.lower()}_type');
#         is_topo = topo_type != 'not_considered';
#         topo_calc_params = {}
#         if is_topo:
#             x_physical = float(full_params.get(f'topo_{wind_dir.lower()}_x', 0))
#             topo_calc_params = {'H': float(full_params.get(f'topo_{wind_dir.lower()}_h', 0)),
#                                 'Lh': float(full_params.get(f'topo_{wind_dir.lower()}_lh', 0)),
#                                 'x': x_physical if sign == 'positive' else -x_physical,
#                                 'terrain': full_params['terrain'], 'landform': landform_map_en_to_zh.get(topo_type)}
#         k_h = wind_calculations.calculate_velocity_pressure_coeff(full_params['h'], full_params['terrain'], db)
#         kzt_at_h = wind_calculations.calculate_topography_factor(topo_calc_params, full_params['h'], db)[
#             0] if is_topo else 1.0
#         q_h = wind_calculations.calculate_velocity_pressure(full_params['h'], full_params['I'], full_params['V10_C'],
#                                                             full_params['terrain'], kzt_at_h, db)
# 
#         return {'tables': tables, 'h': full_params['h'], 'theta': theta, 'is_parallel': is_parallel,
#                 'theta_name': theta_name, 'k_h': k_h, 'q_h': q_h, 'image_for_case': image_for_case}
# 
#     # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====
# 
#     chapter_5_data['plus_x'] = get_detailed_case_data('X', 'positive')
#     chapter_5_data['minus_x'] = get_detailed_case_data('X', 'negative')
#     chapter_5_data['plus_y'] = get_detailed_case_data('Y', 'positive')
#     chapter_5_data['minus_y'] = get_detailed_case_data('Y', 'negative')
# 
#     chapter_6_data = {}
#     if full_params['use_asce7_c_and_c']:
#         local_pressure_results = wind_calculations.run_local_pressure_analysis(full_params)
#         chapter_6_data = local_pressure_results.get('data', {}) if local_pressure_results.get(
#             'status') == 'success' else {}
# 
#     chapter_6_roof_image_path = None
#     if full_params['use_asce7_c_and_c']:
#         h = full_params.get('h', 0);
#         roof_type = full_params.get('roof_type');
#         ridge_dir = full_params.get('ridge_orientation');
#         wind_dir_for_cc = 'Y' if ridge_dir == 'X' else 'X';
#         theta_for_cc = 0
#         if roof_type == 'hip':
#             theta_for_cc = full_params.get('theta_X', 0) if wind_dir_for_cc == 'Y' else full_params.get('theta_Y', 0)
#         else:
#             theta_for_cc = full_params.get('theta', 0)
#         if roof_type == 'flat':
#             chapter_6_roof_image_path = 'img/Roof_C&C_h_gt_18_theta_ls_7.png' if h > 18.3 else 'img/Roof_C&C_h_ls_18_theta_ls_7.png'
#         elif roof_type == 'gable':
#             if theta_for_cc <= 7:
#                 chapter_6_roof_image_path = 'img/Roof_C&C_h_gt_18_theta_ls_7.png' if h > 18.3 else 'img/Roof_C&C_h_ls_18_theta_ls_7.png'
#             elif 7 < theta_for_cc <= 27:
#                 chapter_6_roof_image_path = 'img/Gable_roof_C&C_h_ls_18_theta_btween_7_27.png'
#             elif 27 < theta_for_cc <= 45:
#                 chapter_6_roof_image_path = 'img/Gable_roof_C&C_h_ls_18_theta_btween_27_45.png'
#         elif roof_type == 'hip':
#             if theta_for_cc <= 7:
#                 chapter_6_roof_image_path = 'img/Roof_C&C_h_gt_18_theta_ls_7.png' if h > 18.3 else 'img/Roof_C&C_h_ls_18_theta_ls_7.png'
#             elif 7 < theta_for_cc <= 45:
#                 chapter_6_roof_image_path = 'img/Hip_roof_C&C_h_ls_18_theta_btween_7_45.png'
#         elif roof_type == 'shed':
#             if theta_for_cc <= 3:
#                 chapter_6_roof_image_path = 'img/Roof_C&C_h_gt_18_theta_ls_7.png' if h > 18.3 else 'img/Roof_C&C_h_ls_18_theta_ls_7.png'
#             elif 3 < theta_for_cc <= 10:
#                 chapter_6_roof_image_path = 'img/Shed_roof_C&C_h_ls_18_theta_btween_3_10.png'
#             elif 10 < theta_for_cc <= 30:
#                 chapter_6_roof_image_path = 'img/Shed_roof_C&C_h_ls_18_theta_btween_10_30.png'
# 
#     appendix_data = {}
#     if chapter_4_data.get('x_wind'):
#         x_params = chapter_4_data['x_wind']['pos']
#         params_for_g_x = {
#             'h': full_params['h'],
#             'B': full_params['B_Y'],  # 風向 X，迎風寬度 B 為 B_Y
#             'L': full_params['B_X'],  # 風向 X，深長 L 為 B_X
#             'terrain': full_params['terrain'],
#             'fn': full_params['fn_X'],
#             'beta': full_params['beta'],
#             'V10_C': full_params['V10_C'],
#             'I': full_params['I']
#         }
#         common_gust_x = wind_calculations.calculate_gust_common_params(params_for_g_x, db)
# 
#         if full_params['fn_X'] < 1.0:  # 柔性
#             g_details_x = wind_calculations.calculate_Gf_factor(params_for_g_x, common_gust_x, db)
#             g_details_x['rigidity'] = '柔性'
#         else:  # 剛性
#             g_details_x = wind_calculations.calculate_G_factor(params_for_g_x, common_gust_x)
#             g_details_x['rigidity'] = '剛性'
# 
#         appendix_data['x_wind_g_details'] = g_details_x
# 
#     if chapter_4_data.get('y_wind'):
#         y_params = chapter_4_data['y_wind']['pos']
#         params_for_g_y = {
#             'h': full_params['h'],
#             'B': full_params['B_X'],  # 風向 Y，迎風寬度 B 為 B_X
#             'L': full_params['B_Y'],
#             'terrain': full_params['terrain'],
#             'fn': full_params['fn_Y'],
#             'beta': full_params['beta'],
#             'V10_C': full_params['V10_C'],
#             'I': full_params['I']
#         }
#         common_gust_y = wind_calculations.calculate_gust_common_params(params_for_g_y, db)
# 
#         if full_params['fn_Y'] < 1.0:
#             g_details_y = wind_calculations.calculate_Gf_factor(params_for_g_y, common_gust_y, db)
#             g_details_y['rigidity'] = '柔性'
#         else:
#             g_details_y = wind_calculations.calculate_G_factor(params_for_g_y, common_gust_y)
#             g_details_y['rigidity'] = '剛性'
# 
#         appendix_data['y_wind_g_details'] = g_details_y
# 
#     context = {
#         'site_location': site_location,
#         'v10c': get_params.get('v10c', '0'),
#         'terrain_category': terrain_category,
#         'terrain_params': terrain_params,
#         'geometry_params': geometry_params,
#         'basic_params': basic_params,
# 
#         # 確保這裡傳遞的是 topo_x_data_ch2 (這是在前面 process_topo_data 計算出來的)
#         'topo_x_data': topo_x_data_ch2,
#         'topo_y_data': topo_y_data_ch2,
# 
#         'chapter_4_data': chapter_4_data,
#         'chapter_5_data': chapter_5_data,
#         'chapter_6_data': chapter_6_data,
# 
#         # ★★★ 關鍵：必須將 topo_images 列表傳入 context ★★★
#         'topo_images': topo_images,
# 
#         'building_image_path': building_image_path,
#         'show_chapter_6': full_params['use_asce7_c_and_c'],
#         'chapter_6_roof_image_path': chapter_6_roof_image_path,
#         'appendix_data': appendix_data,
#     }
#     return render(request, 'Wind_TW/wind_report_table_version.html', context)


def calculate_open_api_view(request):
    """
    重構後的 API View：僅負責接收 Request 和回傳 Response，
    計算邏輯全權委託給 services.py 處理。
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '僅接受 POST 請求'}, status=405)

    try:
        # 1. 解析 JSON
        data = json.loads(request.body)

        # 2. 呼叫 Service 層進行處理
        # 這裡會自動處理所有工況 (X+, X-, Y+, Y-)
        result = services.process_calculation_request(data)

        # 3. 檢查是否有尚未支援的類型 (Optional)
        # 如果 result['data_by_case'] 是空的，可能是因為該建築類型的 Handler 還沒寫好
        # 在過渡期，您可以保留舊的 wind_calculations.py 邏輯作為 fallback，
        # 但既然目標是重構，建議直接讓前端知道該功能尚未遷移。

        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'後端處理錯誤: {str(e)}'}, status=500)


# Wind_TW/views.py

def wind_report_open_view(request):
    """
    接收 GET 請求中的參數，渲染【開放式結構】的獨立報告書頁面。
    【核心修正】: 1. 傳遞 K(h) 與 保守的 Kzt, q(h) 值到前端模板。
                  2. 修正附錄 G 因子數據的來源邏輯。
    """
    try:
        db = wind_calculations.setup_databases()
        get_params = request.GET

        # --- 參數準備 (不變) ---
        site_location = f"{get_params.get('county', '未知')} {get_params.get('town', '')}".strip()
        v10c = float(get_params.get('v10c', 0))
        terrain_category = get_params.get('terrain', 'C')
        terrain_params = wind_calculations.get_terrain_parameters(terrain_category, db)
        building_type = get_params.get('enclosureStatus')

        base_params = {
            'V10_C': v10c, 'terrain': terrain_category,
            'I': float(get_params.get('importanceFactor', 1.0)),
            'dampingRatio': float(get_params.get('dampingRatio', 0.01)),
            'fnX': float(get_params.get('fnX', 1.0)),
            'fnY': float(get_params.get('fnY', 1.0)),
            'enclosure_status': building_type, 'geometry_data': {}
        }
        basic_params_for_report = {
            'importance_factor': base_params['I'], 'damping_ratio': base_params['dampingRatio'],
            'fn_x': base_params['fnX'], 'fn_y': base_params['fnY'],
        }
        geometry_params_for_report = {}

        # --- 第三章 數據準備 (不變) ---
        building_type_map = {
            'shed-roof': '單斜式屋頂建築物', 'pitched-free-roof': '雙斜式屋頂建築物',
            'troughed-free-roof': '凹谷式屋頂建築物', 'chimney': '煙囪',
            'solid-sign': '實體標示物', 'hollow-sign': '中空標示物',
            'truss-tower': '桁架高塔'
        }
        chapter_3_data = {
            'building_type_zh': building_type_map.get(building_type, '未知類型'),
            'importance_factor': base_params['I'], 'damping_ratio': base_params['dampingRatio'],
            'fn_x': base_params['fnX'], 'fn_y': base_params['fnY'],
        }

        # --- 第四章 & 附錄 ---
        chapter_4_data = {}
        appendix_data = {}

        # (此處的 if/elif 結構填充 chapter_3_data 和 base_params['geometry_data'] 保持不變)
        if building_type in ['shed-roof', 'pitched-free-roof', 'troughed-free-roof']:
            roof_data = {'h_ridge': float(get_params.get('geo_h_ridge', 0)),
                         'h_eave': float(get_params.get('geo_h_eave', 0)),
                         'ridge_direction': get_params.get('geo_ridge_direction'),
                         'b_x': float(get_params.get('geo_b_x', 0)), 'b_y': float(get_params.get('geo_b_y', 0)),
                         'theta': float(get_params.get('geo_theta', 0)), 'blockage': get_params.get('geo_blockage'), }
            base_params['geometry_data']['roof'] = roof_data
            chapter_3_data['free_roof'] = {'roof': roof_data}
            geometry_params_for_report['dim_x'] = roof_data['b_x']
            geometry_params_for_report['dim_y'] = roof_data['b_y']
        elif building_type == 'chimney':
            shape = get_params.get('geo_shape');
            roughness = get_params.get('geo_roughness')
            shape_map = {'circular': '圓形', 'square-normal': '方形(垂直風)', 'square-diagonal': '方形(對角風)',
                         'hexagonal': '六邊形', 'octagonal': '八邊形'}
            roughness_map = {'moderate-smooth': '中度光滑', 'rough': '粗糙', 'very-rough': '極粗糙'}
            chimney_geo_data = {'shape': shape, 'D_top': float(get_params.get('geo_d_top', 0)),
                                'D_bot': float(get_params.get('geo_d_bot', 0)), 'D': float(get_params.get('geo_d', 0)),
                                'roughness': roughness, 'h': float(get_params.get('calculated_h', 0))}
            base_params['geometry_data'] = chimney_geo_data
            chapter_3_data['chimney'] = {'shape_zh': shape_map.get(shape, '未知'), 'd_top': chimney_geo_data['D_top'],
                                         'd_bot': chimney_geo_data['D_bot'],
                                         'roughness_zh': roughness_map.get(roughness, 'N/A')}
        elif building_type in ['solid-sign', 'hollow-sign']:
            sign_data = {
                'b_h': float(get_params.get('geo_b_h', 0)),
                'b_v': float(get_params.get('geo_b_v', 0)),
                'd': float(get_params.get('geo_d', 0)),
                'normal_direction': get_params.get('geo_normal_direction', 'X'),
                'opening_ratio': float(get_params.get('geo_opening_ratio', 0)),
                'has_corner': get_params.get('geo_has_corner', 'no') == 'yes',
                'lr': float(get_params.get('geo_lr', 0)),
            }
            support_shape_en = get_params.get('support_shape')
            support_shape_map = {
                'rectangular-column': '長方柱或(H型鋼)', 'circular': '圓形柱',
                'hexagonal': '六邊形或八邊形柱', None: 'None'
            }
            support_data = {
                'shape_zh': support_shape_map.get(support_shape_en, '未知'),
                'h': float(get_params.get('support_h', 0)),
                'dtop_x': float(get_params.get('support_dtop_x', 0)),
                'dbot_x': float(get_params.get('support_dbot_x', 0)),
                'dtop_y': float(get_params.get('support_dtop_y', 0)),
                'dbot_y': float(get_params.get('support_dbot_y', 0)),
            }
            base_params['geometry_data']['sign'] = sign_data
            base_params['geometry_data']['support'] = support_data
            chapter_3_data['sign'] = sign_data
            chapter_3_data['support'] = support_data

            if building_type == 'hollow-sign':
                sign_data['qz_mode'] = get_params.get('geo_qz_mode', 'auto')
                sign_data['manual_inputs'] = []

            # ==== ▼▼▼ START: 【核心新增】動態生成規範註解 ▼▼▼ ====
            if building_type == 'solid-sign':
                notes_to_display = []
                B = sign_data['b_h']
                s = sign_data['b_v']
                d = sign_data['d']
                opening_ratio_percent = sign_data['opening_ratio']
                h = d + s

                b_over_s = B / s if s > 0 else 0
                s_over_h = s / h if h > 0 else 0

                chapter_4_data['s_over_h'] = s_over_h
                chapter_4_data['b_over_s'] = b_over_s

                if 0 < opening_ratio_percent < 30:
                    solidity_ratio = 1.0 - (opening_ratio_percent / 100.0)
                    reduction_factor = 1 - (1 - solidity_ratio) ** 1.5
                    chapter_4_data['opening_reduction'] = {
                        'solidity_ratio': solidity_ratio,
                        'reduction_factor': reduction_factor
                    }

                # Note 1: 開孔折減
                if 0 < opening_ratio_percent < 30:
                    notes_to_display.append(
                        "開孔率小於 30% 之實體標示物，其風力係數可乘以折減係數 $(1 - (1 - \\epsilon)^{1.5})$，其中 $\\epsilon$ 為實體率。")

                # Note 2: 工況
                note_2_content = []
                # 條件: s/h < 1 (使用 1e-6 作為浮點數比較的容許誤差)
                if abs(s_over_h - 1.0) > 1e-6 and s_over_h < 1.0:
                    case_b_text = ""
                    if b_over_s < 2:
                        case_b_text = "<li>Case B: 合成風力作用於距幾何中心向風側 $0.2B$ 之處。</li>"
                    note_2_content.append(
                        f"<li>For $s/h < 1$:<ul><li>Case A: 合成風力作用於標示物版面之幾何中心。</li>{case_b_text}</ul></li>")

                if b_over_s >= 2:
                    note_2_content.append(
                        "<li>For $B/s \\ge 2$: Case B 可不考慮，但必須考慮 Case C (合成風力分別作用於各區域之幾何中心)。</li>")

                if abs(s_over_h - 1.0) < 1e-6:
                    note_2_content.append(
                        "<li>For $s/h = 1$: 作用力情況同上，但其垂直作用位置為幾何中心上方 $0.05s$ 處。</li>")

                if note_2_content:
                    notes_to_display.append(
                        "為同時考慮正向與斜向風，應考量以下工況：<ul style='margin-top: 5px;'>" + "".join(
                            note_2_content) + "</ul>")

                # Note 3: Case C 折減
                if b_over_s >= 2 and s_over_h > 0.8:
                    notes_to_display.append(
                        "對於 Case C 且 $s/h > 0.8$ 的情況，其風力係數應再乘以折減係數 $(1.8 - s/h)$。")

                # 將產生的註解列表存入 context
                chapter_4_data['notes_to_display'] = notes_to_display

            base_params['geometry_data']['sign'] = sign_data
            chapter_3_data['sign'] = sign_data
        elif building_type == 'truss-tower':
            import json
            manual_inputs_x_str = get_params.get('geo_manual_inputs_x', '[]')
            manual_inputs_y_str = get_params.get('geo_manual_inputs_y', '[]')
            truss_data = {
                'shape': get_params.get('geo_shape'),
                'solidity_ratio': float(get_params.get('geo_solidity_ratio', 0)),
                'member_shape': get_params.get('geo_member_shape'),
                'manual_inputs_x': json.loads(manual_inputs_x_str),
                'manual_inputs_y': json.loads(manual_inputs_y_str)
            }
            base_params['geometry_data'] = truss_data
            chapter_3_data['truss_tower'] = truss_data

        base_params['h'] = wind_calculations.calculate_unified_h(base_params)
        chapter_3_data['calculated_h'] = base_params['h']
        geometry_params_for_report['calculated_h'] = base_params['h']

        # --- 第二章 地形數據準備 ---
        calculated_h_for_topo = base_params['h']
        landform_map_en_to_zh = {'hill': '山丘', 'ridge': '山脊', 'escarpment': '懸崖'}

        def process_topo_data(axis: str):
            topo_type = get_params.get(f'topo_{axis}_type')
            # ==== ▼▼▼ START: 【核心修正 1-1】修改 process_topo_data 返回值 ====
            if topo_type == 'not_considered':
                return {'type_display': '未考量特殊地形', 'H': 0, 'Lh': 0, 'x': 0,
                        'H_Lh': 'N/A', 'x_Lh_pair': 'N/A', 'z_Lh_max': 'N/A', 'K1': 0,
                        'K2_pair': "0.000 / 0.000", 'K3_max': 0,
                        'Kzt_pair': "1.000 / 1.000", 'kzt_pos_raw': 1.0}  # 新增原始值
            # (此處 Lh == 0 的邏輯不變)
            H = float(get_params.get(f'topo_{axis}_h', 0))
            Lh = float(get_params.get(f'topo_{axis}_lh', 0))
            x_physical = float(get_params.get(f'topo_{axis}_x', 0))

            landform_zh = landform_map_en_to_zh.get(topo_type)

            if Lh == 0: return {'type_display': landform_zh, 'H': H, 'Lh': Lh, 'x': x_physical,
                                'H_Lh': '∞' if H > 0 else '0.00', 'x_Lh_pair': 'N/A', 'z_Lh_max': 'N/A', 'K1': 0,
                                'K2_pair': "N/A", 'K3_max': 0, 'Kzt_pair': "1.000 / 1.000", 'kzt_pos_raw': 1.0}

            x_calc_pos = x_physical
            x_calc_neg = -x_physical
            params_pos = {'H': H, 'Lh': Lh, 'x': x_calc_pos, 'terrain': terrain_category, 'landform': landform_zh}
            kzt_pos, k1, k2_pos, k3_max = wind_calculations.calculate_topography_factor(params_pos,
                                                                                        calculated_h_for_topo, db)
            params_neg = {'H': H, 'Lh': Lh, 'x': x_calc_neg, 'terrain': terrain_category, 'landform': landform_zh}
            kzt_neg, _, k2_neg, _ = wind_calculations.calculate_topography_factor(params_neg, calculated_h_for_topo, db)
            z_lh_max_str = f"{calculated_h_for_topo / Lh:.3f}" if Lh > 0 else 'N/A'
            return {'type_display': landform_zh, 'H': H, 'Lh': Lh, 'x': x_physical, 'H_Lh': f"{H / Lh:.3f}",
                    'x_Lh_pair': f"{x_calc_pos / Lh:.3f} / {x_calc_neg / Lh:.3f}", 'z_Lh_max': z_lh_max_str, 'K1': k1,
                    'K2_pair': f"{k2_pos:.3f} / {k2_neg:.3f}", 'K3_max': k3_max,
                    'Kzt_pair': f"{kzt_pos:.3f} / {kzt_neg:.3f}",
                    'kzt_pos_raw': kzt_pos}  # 新增原始值
            # ==== ▲▲▲ END: 【核心修正 1-1】 ▲▲▲ ====

        topo_x_data = process_topo_data('x')
        topo_y_data = process_topo_data('y')

        # ==== ▼▼▼ START: 【核心修正 1-2】計算 K(h), 保守 Kzt 和保守 q(h) 並加入 context ====
        if building_type == 'solid-sign':
            h_for_calc = chapter_3_data.get('calculated_h', 0)

            # 1. 計算 K(h)
            k_h_value = wind_calculations.calculate_velocity_pressure_coeff(h_for_calc, terrain_category, db)
            chapter_3_data['k_h_value'] = k_h_value

            # 2. 取得保守的 Kzt
            kzt_conservative = max(topo_x_data.get('kzt_pos_raw', 1.0), topo_y_data.get('kzt_pos_raw', 1.0))
            chapter_3_data['kzt_conservative'] = kzt_conservative

            # 3. 計算保守的 q(h)
            q_h_conservative = wind_calculations.calculate_velocity_pressure(
                h_for_calc, base_params['I'], v10c, terrain_category, kzt_conservative, db
            )
            chapter_3_data['q_h_conservative'] = q_h_conservative

        # ==== ▲▲▲ END: 【核心修正 1-2】 ▲▲▲ ====

        # (此處 get_open_analysis_params 內部函式以及後續的邏輯保持不變)
        def get_open_analysis_params(wind_dir, topo_params_x=None, topo_params_y=None):
            if building_type == 'chimney':
                params_for_chimney = base_params.copy();
                params_for_chimney['topo_params_x'] = topo_params_x;
                params_for_chimney['topo_params_y'] = topo_params_y;
                params_for_chimney['wind_direction'] = 'X'
                return wind_calculations.calculate_chimney_force_conservative(params_for_chimney, db)
            if building_type in ['solid-sign', 'hollow-sign']:
                params_for_sign = base_params.copy();
                params_for_sign['topo_params_x'] = topo_params_x;
                params_for_sign['topo_params_y'] = topo_params_y
                if building_type == 'solid-sign':
                    return wind_calculations.calculate_solid_sign_force_conservative(params_for_sign, db)
                else:
                    return wind_calculations.calculate_hollow_sign_force_conservative(params_for_sign, db)
            analysis_func_map = {
                'shed-roof': wind_calculations.run_shed_roof_analysis,
                'pitched-free-roof': wind_calculations.run_pitched_roof_analysis,
                'troughed-free-roof': wind_calculations.run_troughed_roof_analysis,
                'truss-tower': wind_calculations.calculate_truss_tower_force
            }
            analysis_func = analysis_func_map.get(building_type)
            if not analysis_func: return {}
            params = base_params.copy()
            params['wind_direction'] = wind_dir
            topo_params_to_use = topo_params_x if wind_dir == 'X' else topo_params_y
            params['is_topo_site'] = topo_params_to_use['is_topo']
            if params['is_topo_site']: params['topo_params'] = topo_params_to_use['params']
            return analysis_func(params, db)

        is_topo_x = get_params.get('topo_x_type') != 'not_considered'
        topo_params_x = {'is_topo': is_topo_x, 'params': {'H': float(get_params.get('topo_x_h', 0)),
                                                          'Lh': float(get_params.get('topo_x_lh', 0)),
                                                          'x': float(get_params.get('topo_x_x', 0)),
                                                          'landform': landform_map_en_to_zh.get(
                                                              get_params.get('topo_x_type')),
                                                          'terrain': terrain_category} if is_topo_x else {}}
        is_topo_y = get_params.get('topo_y_type') != 'not_considered'
        topo_params_y = {'is_topo': is_topo_y, 'params': {'H': float(get_params.get('topo_y_h', 0)),
                                                          'Lh': float(get_params.get('topo_y_lh', 0)),
                                                          'x': float(get_params.get('topo_y_x', 0)),
                                                          'landform': landform_map_en_to_zh.get(
                                                              get_params.get('topo_y_type')),
                                                          'terrain': terrain_category} if is_topo_y else {}}

        if building_type in ['chimney', 'solid-sign', 'hollow-sign']:
            chapter_4_data['main_wind'] = {'pos': get_open_analysis_params(None, topo_params_x, topo_params_y)}
            main_wind_pos_data = chapter_4_data.get('main_wind', {}).get('pos', {})
            if main_wind_pos_data and 'case_c_forces' in main_wind_pos_data and main_wind_pos_data['case_c_forces']:
                # 使用 sum() 搭配列表生成式來加總每個區域的風力
                case_c_total_force = sum(item.get('force', 0) for item in main_wind_pos_data['case_c_forces'])
                # 將計算出的總風力存回字典中，以便前端模板使用
                main_wind_pos_data['case_c_total_force'] = case_c_total_force
            if main_wind_pos_data:
                appendix_data['main_wind_g_details'] = main_wind_pos_data.get('g_factor_details')
                appendix_data['support_g_details'] = main_wind_pos_data.get('support_g_factor_details')
        else:
            chapter_4_data['x_wind'] = {'pos': get_open_analysis_params('X', topo_params_x, topo_params_y)}
            chapter_4_data['y_wind'] = {'pos': get_open_analysis_params('Y', topo_params_x, topo_params_y)}
            x_wind_pos_data = chapter_4_data.get('x_wind', {}).get('pos', {})
            if x_wind_pos_data:
                appendix_data['x_wind_g_details'] = x_wind_pos_data.get('g_factor_details')
            y_wind_pos_data = chapter_4_data.get('y_wind', {}).get('pos', {})
            if y_wind_pos_data:
                appendix_data['y_wind_g_details'] = y_wind_pos_data.get('g_factor_details')

        context = {
            'site_location': site_location, 'v10c': v10c, 'terrain_category': terrain_category,
            'terrain_params': terrain_params, 'topo_x_data': topo_x_data, 'topo_y_data': topo_y_data,
            'topo_images': [],
            'chapter_3_data': chapter_3_data,
            'chapter_4_data': chapter_4_data,
            'appendix_data': appendix_data,
            'building_type': building_type,
            'basic_params': basic_params_for_report,
            'geo': geometry_params_for_report,
        }
        print(chapter_4_data)
        return render(request, 'Wind_TW/wind_report_open.html', context)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render(request, 'Wind_TW/error.html', {'error_message': f'生成報告時發生錯誤: {e}'})


def wind_report_v2_view(request):
    """
    接收 GET 請求中的參數，執行計算並渲染 v2 版報告書。
    """
    try:
        get_params = request.GET
        db = wind_calculations.setup_databases()

        # 1. 基礎參數準備 (從 GET 參數提取)
        # -------------------------------------------------------
        site_location = f"{get_params.get('county', '未知')} {get_params.get('town', '')}".strip()
        v10c = float(get_params.get('v10c', 0))
        terrain_category = get_params.get('terrain', 'C')
        terrain_params = wind_calculations.get_terrain_parameters(terrain_category, db)

        roof_shape_en = get_params.get('roof_shape')
        roof_shape_map = {
            'flat': '平屋頂', 'gable': '雙邊單斜式(山形)屋頂', 'shed': '單邊單斜式屋頂',
            'hip': '雙斜(四坡水)屋頂', 'arched': '拱形屋頂',
            'sawtooth_uniform': '鋸齒型屋頂 (一致)', 'sawtooth_irregular': '不規則鋸齒型屋頂'
        }

        ridge_dir_en = get_params.get('ridge_direction', 'null')
        ridge_len_str = get_params.get('ridge_length', 'N/A')

        # 提取尺寸與高度
        b_x = float(get_params.get('dim_x', 0))
        b_y = float(get_params.get('dim_y', 0))
        h_eave = float(get_params.get('eave_height', 0))
        h_ridge = float(get_params.get('ridge_height', 0))
        roof_shape = get_params.get('roof_shape')
        ridge_dir = get_params.get('ridge_direction', 'X')  # 預設 X

        # ==== ▼▼▼ START: ★★★ 2. 強制在後端重新計算角度 θ ★★★ ▼▼▼ ====
        calculated_theta = 0.0
        calculated_theta_x = 0.0
        calculated_theta_y = 0.0

        delta_h = h_ridge - h_eave

        # 只有當屋脊高 > 屋簷高時才計算角度，否則為 0 (平屋頂)
        if delta_h > 0.01:
            # Case A: 四坡水 (Hip) - 需分別計算 X 與 Y 向角度
            if roof_shape == 'hip':
                if b_y > 0:
                    calculated_theta_x = math.degrees(math.atan(delta_h / (b_y / 2)))
                if b_x > 0:
                    calculated_theta_y = math.degrees(math.atan(delta_h / (b_x / 2)))

                # 為了通用參數顯示，取兩者較大值作為代表 θ
                calculated_theta = max(calculated_theta_x, calculated_theta_y)

            # Case B: 單斜 (Shed) - 底邊為全長
            elif roof_shape == 'shed':
                # 判斷跨度方向
                span = b_y if ridge_dir == 'X' else b_x
                if span > 0:
                    calculated_theta = math.degrees(math.atan(delta_h / span))

            # Case C: 山形 (Gable) / 拱形 (Arched) / 鋸齒 (Sawtooth) - 底邊為半長
            # 注意: Sawtooth 若為多跨，應除以跨數，這裡暫以單跨或總寬計算
            else:
                span = b_y if ridge_dir == 'X' else b_x

                # 若為鋸齒且有多跨，需修正 span
                if roof_shape == 'sawtooth_uniform':
                    num_spans = int(get_params.get('num_spans', 1))
                    if num_spans > 0:
                        span = span / num_spans

                if span > 0:
                    calculated_theta = math.degrees(math.atan(delta_h / (span / 2)))

        # ==== ▲▲▲ END: 角度重算結束 ▲▲▲ ====

        # 依據規範重新計算平均高度 h
        # 規範：屋頂斜角小於 10 度，h = 簷高；否則 h = (簷高 + 脊高) / 2
        if calculated_theta < 10:
            calculated_h = h_eave
        else:
            calculated_h = (h_eave + h_ridge) / 2

        # 若前端傳入 calculated_h 且與後端計算差異不大，可考慮是否覆蓋 (這裡選擇以後端計算為主)
        # calculated_h = float(get_params.get('calculated_h', calculated_h))

        # 2. 建立 full_params (用於計算)
        # -------------------------------------------------------
        full_params = {
            'B_X': b_x,
            'B_Y': b_y,
            'eave_height': h_eave,
            'ridge_height': h_ridge,
            'h': calculated_h,
            'roof_type': roof_shape_en,
            'terrain': terrain_category,

            'I': float(get_params.get('importance_factor', 1.0)),
            'V10_C': v10c,
            'beta': float(get_params.get('damping_ratio', 0.01)),  # 這裡修正了可能的 key error，統一使用 damping_ratio
            'dampingRatio': float(get_params.get('damping_ratio', 0.01)),
            'enclosure_status': get_params.get('enclosure_status', '部分封閉式建築'),

            'theta': calculated_theta,
            'theta_X': calculated_theta_x,
            'theta_Y': calculated_theta_y,

            'ridge_orientation': ridge_dir_en if ridge_dir_en in ['X', 'Y'] else None,

            'fn_X': float(get_params.get('fn_x', 0)),
            'fn_Y': float(get_params.get('fn_y', 0)),
            'ft': float(get_params.get('ft', 0)),
            'has_overhang': get_params.get('has_overhang', 'false').lower() == 'true',
            'num_spans': int(get_params.get('num_spans', 1)),
            'use_asce7_c_and_c': get_params.get('use_asce7_c_and_c', 'false').lower() == 'true',
            'segmentHeight': float(get_params.get('segment_height', 2.0)),
            'simplify_gable': get_params.get('simplify_gable', 'false').lower() == 'true',

            'topo_x_type': get_params.get('topo_x_type', 'not_considered'),
            'topo_x_h': float(get_params.get('topo_x_h') or 0),
            'topo_x_lh': float(get_params.get('topo_x_lh') or 0),
            'topo_x_x': float(get_params.get('topo_x_x') or 0),
            'topo_y_type': get_params.get('topo_y_type', 'not_considered'),
            'topo_y_h': float(get_params.get('topo_y_h') or 0),
            'topo_y_lh': float(get_params.get('topo_y_lh') or 0),
            'topo_y_x': float(get_params.get('topo_y_x') or 0),
        }

        full_params['gcpi'] = wind_calculations.calculate_gcpi_coeff(full_params['enclosure_status'], db)

        # 3. 準備顯示用的參數物件
        # -------------------------------------------------------
        geometry_params = {
            'dim_x': full_params['B_X'], 'dim_y': full_params['B_Y'],
            'roof_shape_en': roof_shape_en,
            'roof_shape_zh': roof_shape_map.get(roof_shape_en, '未知'),
            'eave_height': full_params['eave_height'],
            'ridge_height': full_params['ridge_height'],
            'calculated_h': full_params['h'],
            'ridge_direction': f"{ridge_dir_en}向" if ridge_dir_en in ['X', 'Y'] else '不適用',
            'ridge_length': f"{ridge_len_str} m" if ridge_len_str != 'N/A' else '不適用',
            'theta': full_params['theta'],
            'theta_x': full_params['theta_X'],
            'theta_y': full_params['theta_Y'],
        }

        basic_params = {
            'enclosure_status': full_params['enclosure_status'],
            'importance_factor': full_params['I'],
            'damping_ratio': full_params['dampingRatio'],
            'fn_x': full_params['fn_X'], 'fn_y': full_params['fn_Y'], 'ft': full_params['ft'],
        }

        # 4. 地形參數與圖片處理
        # -------------------------------------------------------
        landform_zh_map = {'hill': '山丘', 'ridge': '山脊', 'escarpment': '懸崖'}

        def process_topo_data(axis: str):
            # 復用原本的邏輯處理顯示用的地形數據
            topo_type = get_params.get(f'topo_{axis}_type')
            # 若未考量特殊地形
            if topo_type == 'not_considered':
                return {
                    'type_display': '未考量特殊地形', 'H': 0, 'Lh': 0, 'x': 0,
                    'H_Lh': 'N/A', 'x_Lh_pair': 'N/A', 'z_Lh_max': 'N/A',
                    'K1': 0, 'K2_pair': "0.000 / 0.000",
                    'K3_max': 1.000,  # K3 預設顯示 1.000
                    'Kzt_pair': "1.000 / 1.000",
                    'kzt_pos_raw': 1.0
                }

            H = float(get_params.get(f'topo_{axis}_h', 0))
            Lh = float(get_params.get(f'topo_{axis}_lh', 0))
            x_physical = float(get_params.get(f'topo_{axis}_x', 0))
            landform = landform_zh_map.get(topo_type)

            # 防呆 Lh=0
            if Lh == 0:
                return {
                    'type_display': landform, 'H': H, 'Lh': Lh, 'x': x_physical,
                    'H_Lh': '∞', 'x_Lh_pair': 'N/A', 'z_Lh_max': 'N/A',
                    'K1': 0, 'K2_pair': "N/A",
                    'K3_max': 1.000,
                    'Kzt_pair': "1.000 / 1.000",
                    'kzt_pos_raw': 1.0
                }

            x_calc_pos, x_calc_neg = x_physical, -x_physical

            # 建立參數
            params_pos = {'H': H, 'Lh': Lh, 'x': x_calc_pos, 'terrain': terrain_category, 'landform': landform}
            params_neg = {'H': H, 'Lh': Lh, 'x': x_calc_neg, 'terrain': terrain_category, 'landform': landform}

            # ==== ▼▼▼ START: 核心修改 ▼▼▼ ====
            # 為了讓表 2.3 顯示最大地形效應，強制將高度 z 設為 0 (地面)，此時 K3 = 1.0
            # 這樣 Kzt 會是該位置 (x) 的最大值

            # 計算 +風向 (使用 z=0)
            kzt_pos, k1, k2_pos, k3_pos = wind_calculations.calculate_topography_factor(params_pos, 0.0, db)

            # 計算 -風向 (使用 z=0)
            kzt_neg, _, k2_neg, _ = wind_calculations.calculate_topography_factor(params_neg, 0.0, db)

            # 雖然 K3 我們強制算 1.0，但 z/Lh 的顯示欄位建議還是顯示「建築物頂部」的比例，供工程師參考幾何關係
            z_lh_display = f"{calculated_h / Lh:.3f}" if Lh > 0 else 'N/A'

            # ==== ▲▲▲ END: 核心修改 ▲▲▲ ====

            return {
                'type_display': landform,
                'H': H,
                'Lh': Lh,
                'x': x_physical,
                'H_Lh': f"{H / Lh:.3f}",
                'x_Lh_pair': f"{x_calc_pos / Lh:.3f} / {x_calc_neg / Lh:.3f}",
                'z_Lh_max': z_lh_display,  # 顯示建築幾何比例
                'K1': k1,
                'K2_pair': f"{k2_pos:.3f} / {k2_neg:.3f}",
                'K3_max': 1.000,  # 強制顯示 1.000 (因為我們是用 z=0 計算的)
                'Kzt_pair': f"{kzt_pos:.3f} / {kzt_neg:.3f}",  # 這是 z=0 時的最大 Kzt
                'kzt_pos_raw': kzt_pos  # 傳遞給後續邏輯使用 (如實體標示物保守計算)
            }

        topo_x_data_ch2 = process_topo_data('x')
        topo_y_data_ch2 = process_topo_data('y')

        # 地形圖片
        topo_images = []
        topo_image_map = {'hill': 'img/hill.png', 'ridge': 'img/ridge.png', 'escarpment': 'img/escarpment.png'}

        if get_params.get('topo_x_type') in topo_image_map:
            topo_images.append({'path': topo_image_map[get_params.get('topo_x_type')],
                                'caption': f'X向地形示意 ({landform_zh_map.get(get_params.get("topo_x_type"))})'})
        if get_params.get('topo_y_type') in topo_image_map:
            topo_images.append({'path': topo_image_map[get_params.get('topo_y_type')],
                                'caption': f'Y向地形示意 ({landform_zh_map.get(get_params.get("topo_y_type"))})'})

        # 5. 第四章：主風力計算 (Chapter 4 Data Calculation)
        # -------------------------------------------------------
        chapter_4_data = {
            'gcpi': wind_calculations.calculate_gcpi_coeff(full_params['enclosure_status'], db),
            'x_wind': {}, 'y_wind': {}
        }

        # 準備地形配置 (用於計算)
        topo_config_calc = {
            'X': {'is_topo': get_params.get('topo_x_type') != 'not_considered',
                  'params': {'landform': landform_zh_map.get(get_params.get('topo_x_type')),
                             'H': float(get_params.get('topo_x_h', 0)), 'Lh': float(get_params.get('topo_x_lh', 0)),
                             'x_base': float(get_params.get('topo_x_x', 0))}},
            'Y': {'is_topo': get_params.get('topo_y_type') != 'not_considered',
                  'params': {'landform': landform_zh_map.get(get_params.get('topo_y_type')),
                             'H': float(get_params.get('topo_y_h', 0)), 'Lh': float(get_params.get('topo_y_lh', 0)),
                             'x_base': float(get_params.get('topo_y_x', 0))}}
        }

        # 執行計算迴圈，填充 chapter_4_data
        for axis in ['X', 'Y']:
            # 決定需要跑哪些工況 (正向/負向)
            cases = ['positive']
            has_neg_case = topo_config_calc[axis]['is_topo']
            if has_neg_case:
                cases.append('negative')

            chapter_4_data[f'{axis.lower()}_wind']['has_neg_case'] = has_neg_case
            chapter_4_data[f'{axis.lower()}_wind']['pos_header'] = f"順風向 (+{axis})"
            chapter_4_data[f'{axis.lower()}_wind']['neg_header'] = f"順風向 (-{axis})"

            for sign in cases:
                # 準備該工況的參數
                case_params = full_params.copy()
                case_params['wind_direction'] = axis

                # 設定對應風向的頻率與尺寸 (Handler 需要)
                if axis == 'X':
                    case_params['fn'] = full_params['fn_X']
                    # EnclosedHandler 會讀取 B_X, B_Y，所以不需要這裡手動 swap B/L，Handler 內部會處理
                else:
                    case_params['fn'] = full_params['fn_Y']

                # 設定地形參數
                current_topo = topo_config_calc[axis]
                case_params['is_topo_site'] = current_topo['is_topo']
                if current_topo['is_topo']:
                    p = current_topo['params'].copy()
                    p['x'] = p['x_base'] if sign == 'positive' else -p['x_base']
                    # **修正**: core.py 的 calculate_topography_factor 依賴 'terrain' 鍵
                    p['terrain'] = terrain_category
                    case_params['topo_params_' + axis] = p  # 傳給 Handler，注意 key 是 topo_params_X 或 Y
                    # 為了相容 BaseWindCalculator 的通用方法，也傳一份到 topo_params
                    case_params['topo_params'] = p
                else:
                    case_params['topo_params'] = {}

                # 呼叫 Handler 計算
                # 這裡使用 services.get_handler_class 確保邏輯一致
                calc_method = 'general'  # 或 get_params.get('calculation_method')
                HandlerClass = services.get_handler_class(full_params['enclosure_status'], calc_method)

                if HandlerClass:
                    handler = HandlerClass(case_params)

                    try:
                        # 使用 _calculate_direction 來獲取單一方向的詳細數據
                        dir_result = handler._calculate_direction(axis)

                        # ★★★ 關鍵：資料映射 (Mapping) ★★★
                        # 將 Handler 的輸出轉換為模板期望的格式
                        mapped_result = {
                            'rigidity': dir_result['rigidity'],
                            'B': dir_result['B'],
                            'L': dir_result['L'],
                            'G_factor': dir_result['g_details'],  # 這裡放詳細資料
                            'L_B': dir_result['L_over_B'],
                            'h_L': calculated_h / dir_result['L'] if dir_result['L'] > 0 else 0,
                            # h/B 需自行計算
                            'h_B': calculated_h / dir_result['B'] if dir_result['B'] > 0 else 0,

                            'Cp_windward': dir_result['wall_cp']['windward'],
                            'Cp_leeward': dir_result['wall_cp']['leeward'],
                            'Cp_side': dir_result['wall_cp']['side'],
                            'roof_cp': dir_result['roof_cp']
                        }

                        # 存入 chapter_4_data
                        key_map = {'positive': 'pos', 'negative': 'neg'}
                        chapter_4_data[f'{axis.lower()}_wind'][key_map[sign]] = mapped_result

                    except Exception as e:
                        print(f"Error calculating {axis} {sign}: {e}")
                        import traceback
                        traceback.print_exc()

        # 6. 其他資料 (Chapter 5, 6, Appendix)
        # -------------------------------------------------------
        # 建築物圖片路徑 (保持不變)
        building_image_path = None
        has_overhang = full_params['has_overhang']
        if roof_shape_en == 'flat':
            building_image_path = 'img/color/Flat_roof_building.png'
        elif roof_shape_en in ['gable', 'hip']:
            overhang_suffix = '_overhang' if has_overhang else ''
            if ridge_dir_en in ['X', 'Y']:
                building_image_path = f'img/color/{roof_shape_en.capitalize()}_roof_{ridge_dir_en}_ridge{overhang_suffix}_building.png'
        elif roof_shape_en == 'arched':
            if ridge_dir_en in ['X', 'Y']:
                building_image_path = f'img/color/Arched_roof_{ridge_dir_en}_ridge_building.png'
        elif roof_shape_en == 'shed':
            if ridge_dir_en in ['X', 'Y']:
                building_image_path = f'img/color/Shed_roof_{ridge_dir_en}_ridge_building.png'
        elif roof_shape_en == 'sawtooth_uniform':
            if ridge_dir_en in ['X', 'Y']:
                building_image_path = f'img/color/Sawtooth_uniform_roof_{ridge_dir_en}_ridge_building.png'

        # ==========================================
        # ==== START: 簡化後的第五章資料生成邏輯 ====
        # ==========================================
        chapter_5_data = {}
        # 針對封閉式/部分封閉式建築，gcpi_values 固定有兩個值 (例如 +0.375, -0.375 或 +1.146, -1.146)
        gcpi_values = full_params['gcpi']

        # 輔助函式：生成特定風向(X/Y)與方向(正/負)的詳細資料
        def get_chapter_5_case_data_simplified(wind_dir, sign):
            tables = []

            # 針對每一個 GCpi 值生成一份表格數據
            for gcpi in gcpi_values:
                # 呼叫核心計算函式
                table_data = wind_calculations.generate_report_table_data(
                    full_params, db, wind_dir, sign,
                    specific_gcpi=gcpi,
                    filter_roof_cp=True
                )
                # 加入 gcpi 方便模板使用
                table_data['gcpi'] = gcpi
                tables.append(table_data)

            # 從第一組數據中提取 q(h) 供標題顯示 (同一高度 q(h) 相同)
            q_h_display = tables[0]['summary_data'].get('q_h', 0) if tables else 0

            # 簡單的圖片邏輯 (可選)
            image_for_case = None
            # if roof_shape_en == 'flat': image_for_case = 'img/Flat_roof_building.png'

            return {
                'tables': tables,  # 包含兩個 GCpi 工況的詳細計算結果
                'q_h': q_h_display,
                'image_for_case': image_for_case
            }

        # 生成四種工況資料 (X+, X-, Y+, Y-)
        # 只有當有地形效應時，has_neg_case 才會是 True
        has_topo_x = chapter_4_data['x_wind']['has_neg_case']
        has_topo_y = chapter_4_data['y_wind']['has_neg_case']

        # 5.1 +X
        chapter_5_data['plus_x'] = get_chapter_5_case_data_simplified('X', 'positive')

        # 5.2 -X (若有地形)
        if has_topo_x:
            chapter_5_data['minus_x'] = get_chapter_5_case_data_simplified('X', 'negative')

        # 5.3 +Y
        chapter_5_data['plus_y'] = get_chapter_5_case_data_simplified('Y', 'positive')

        # 5.4 -Y (若有地形)
        if has_topo_y:
            chapter_5_data['minus_y'] = get_chapter_5_case_data_simplified('Y', 'negative')



        # 附錄資料
        appendix_data = {}
        if chapter_4_data.get('x_wind') and chapter_4_data['x_wind'].get('pos'):
            x_params = chapter_4_data['x_wind']['pos']
            # 準備計算用的參數
            params_for_g_x = {
                'h': full_params['h'],
                'B': x_params['B'],
                'L': x_params['L'],
                'terrain': full_params['terrain'],
                'fn': full_params['fn_X'],
                'beta': full_params['beta'],
                'V10_C': full_params['V10_C'],
                'I': full_params['I']
            }
            common_gust_x = wind_calculations.calculate_gust_common_params(params_for_g_x, db)

            if x_params['rigidity'] == '柔性':
                g_details_x = wind_calculations.calculate_Gf_factor(params_for_g_x, common_gust_x, db)
                g_details_x['rigidity'] = '柔性'
            else:
                g_details_x = wind_calculations.calculate_G_factor(params_for_g_x, common_gust_x)
                g_details_x['rigidity'] = '普通'

            # 【關鍵修正】：將輸入參數合併到結果字典中，這樣 Template 才能讀到 h, B, fn 等原始值
            g_details_x.update(params_for_g_x)
            appendix_data['x_wind_g_details'] = g_details_x
        if chapter_4_data.get('y_wind') and chapter_4_data['y_wind'].get('pos'):
            y_params = chapter_4_data['y_wind']['pos']
            params_for_g_y = {
                'h': full_params['h'],
                'B': y_params['B'],
                'L': y_params['L'],
                'terrain': full_params['terrain'],
                'fn': full_params['fn_Y'],
                'beta': full_params['beta'],
                'V10_C': full_params['V10_C'],
                'I': full_params['I']
            }
            common_gust_y = wind_calculations.calculate_gust_common_params(params_for_g_y, db)

            if y_params['rigidity'] == '柔性':
                g_details_y = wind_calculations.calculate_Gf_factor(params_for_g_y, common_gust_y, db)
                g_details_y['rigidity'] = '柔性'
            else:
                g_details_y = wind_calculations.calculate_G_factor(params_for_g_y, common_gust_y)
                g_details_y['rigidity'] = '普通'

            # 【關鍵修正】：合併參數
            g_details_y.update(params_for_g_y)
            appendix_data['y_wind_g_details'] = g_details_y

        # ==========================================
        # ==== START: 第六章 局部風壓資料 (新增) ====
        # ==========================================
        # 確保傳入所需的參數，如 theta
        full_params['theta'] = calculated_theta  # 確保 theta 已在 full_params
        chapter_6_data = wind_calculations.run_local_pressure_analysis(full_params)

        # ==========================================
        # ==== START: 第八章 橫風向風力資料 ====
        # ==========================================
        chapter_8_data = {}
        chapter_8_data['x_wind_transverse'] = wind_calculations.generate_transverse_report_data(full_params, db, 'X')
        chapter_8_data['y_wind_transverse'] = wind_calculations.generate_transverse_report_data(full_params, db, 'Y')

        # ==========================================
        # ==== START: 第九章 扭轉向風力資料 (新增) ====
        # ==========================================
        chapter_9_data = wind_calculations.generate_torsional_report_data(full_params, db)



        context = {
            'site_location': site_location,
            'v10c': v10c,
            'terrain_category': terrain_category,
            'terrain_params': terrain_params,
            'topo_x_data': topo_x_data_ch2,
            'topo_y_data': topo_y_data_ch2,
            'geometry_params': geometry_params,
            'basic_params': basic_params,
            'chapter_4_data': chapter_4_data,  # 傳遞計算好的第四章資料
            'chapter_5_data': chapter_5_data,
            'appendix_data': appendix_data,
            'topo_images': topo_images,
            'building_image_path': building_image_path,
            'show_chapter_6': full_params['use_asce7_c_and_c'],
            'chapter_6_data': chapter_6_data,
            # 'chapter_6_roof_image_path': chapter_6_roof_image_path,
            'chapter_8_data': chapter_8_data,
            'chapter_9_data': chapter_9_data,
        }

        return render(request, 'Wind_TW/wind_report_v2.html', context)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return render(request, 'Wind_TW/error.html', {'error_message': f'生成報告時發生錯誤: {e}'})




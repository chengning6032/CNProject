# Wind_TW/services.py

import numpy as np
import math
from .calculations.handlers.structures import ChimneyHandler, TrussTowerHandler, WaterTowerHandler
from .calculations.handlers.enclosed import EnclosedGeneralHandler, EnclosedLowRiseHandler


# 暫時註解掉尚未遷移的 Handler
# from .calculations.handlers.signs import SolidSignHandler, HollowSignHandler
# from .calculations.handlers.open_roofs import ShedRoofHandler, PitchedRoofHandler, TroughedRoofHandler

def get_handler_class(building_type, calc_method=None):
    """
    工廠方法：根據建築類型回傳對應的 Handler 類別
    :param building_type: 建築物類型 (如 'chimney', '封閉式建築')
    :param calc_method: 'general' or 'simplified_2_13' (僅對封閉式建築有效)
    """
    # 1. 處理結構類/開放式建築 (無須區分方法)
    structure_mapping = {
        'chimney': ChimneyHandler,
        'truss-tower': TrussTowerHandler,
        'water-tower': WaterTowerHandler,
        # 'solid-sign': SolidSignHandler, # 待遷移
        # 'hollow-sign': HollowSignHandler, # 待遷移
        # 'shed-roof': ShedRoofHandler, # 待遷移
        # 'pitched-free-roof': PitchedRoofHandler, # 待遷移
        # 'troughed-free-roof': TroughedRoofHandler, # 待遷移
        # 'street-light': StreetLightHandler # 待遷移
    }

    handler = structure_mapping.get(building_type)
    if handler:
        return handler

    # 2. 處理封閉式/部分封閉式建築
    if building_type in ['封閉式建築', '部分封閉式建築']:
        if calc_method == 'simplified_2_13':
            return EnclosedLowRiseHandler
        else:
            return EnclosedGeneralHandler

    return None


def calculate_unified_h(params):
    """
    統一計算建築物的參考高度 h。
    """
    building_type = params.get('enclosure_status')
    geo = params.get('geometry_data', {})

    # --- Case 1: 封閉式/部分封閉式建築 (依據 ASCE 7 平均屋頂高度定義) ---
    if building_type in ['封閉式建築', '部分封閉式建築']:
        h_eave = float(params.get('eave_height', 0))
        h_ridge = float(params.get('ridge_height', 0))
        theta = float(params.get('theta', 0))

        # 若屋頂角小於 10 度，h 取簷高；否則取簷高與脊高之平均
        if theta < 10:
            return h_eave
        else:
            return (h_eave + h_ridge) / 2

    # --- Case 2: 開放式屋頂 ---
    elif building_type in ['shed-roof', 'pitched-free-roof', 'troughed-free-roof']:
        roof = geo.get('roof', {})
        h_ridge = float(roof.get('h_ridge', 0))
        h_eave = float(roof.get('h_eave', 0))
        theta = float(roof.get('theta', 0))
        return h_eave if theta < 10 else (h_ridge + h_eave) / 2

    # --- Case 3: 結構物 ---
    elif building_type == 'chimney':
        return float(geo.get('h', 0))

    elif building_type == 'water-tower':
        body = geo.get('body', {})
        h_body = float(body.get('h', 0))
        clearance = float(body.get('C', 0))
        return h_body + clearance

    elif building_type == 'hollow-sign':
        sign = geo.get('sign', {})
        b_v = float(sign.get('b_v', 0))
        d = float(sign.get('d', 0))
        return d + (b_v / 2)

    elif building_type == 'solid-sign':
        sign = geo.get('sign', {})
        b_v = float(sign.get('b_v', 0))
        d = float(sign.get('d', 0))
        return d + b_v

    elif building_type == 'truss-tower':
        manual_inputs_x = geo.get('manual_inputs_x', [])
        manual_inputs_y = geo.get('manual_inputs_y', [])
        # 避免空列表導致 max() 錯誤
        all_inputs = manual_inputs_x + manual_inputs_y
        if not all_inputs:
            return 0.0
        return max(float(item.get('height', 0)) for item in all_inputs)

    elif building_type == 'street-light':
        main_pole = geo.get('main_pole', {})
        return float(main_pole.get('h_m', 0))

    return 0.0


def process_calculation_request(data):
    """
    服務層入口：處理來自 API 的原始 JSON 數據，協調計算流程。
    """
    landform_map = {
        'hill': '山丘',
        'ridge': '山脊',
        'escarpment': '懸崖',
        'not_considered': None
    }

    # 1. 基礎參數清洗與提取
    base_params = {
        'V10_C': float(data.get('v10c', 0)),
        'terrain': data.get('terrain', 'C'),
        'I': float(data.get('importanceFactor', 1.0)),
        'dampingRatio': float(data.get('dampingRatio', 0.01)),
        'enclosure_status': data.get('enclosureStatus'),
        'geometry_data': data.get('geometryData', {}),
        'simplify_gable': data.get('simplifyGable', False),
        # 封閉式建築參數
        'B_X': float(data.get('buildingDimX', 0)),
        'B_Y': float(data.get('buildingDimY', 0)),
        'eave_height': float(data.get('eaveHeight', 0)),  # 用於計算 h
        'ridge_height': float(data.get('ridgeHeight', 0)),  # 用於計算 h
        'roof_type': data.get('roofShape'),
        'ridge_orientation': data.get('ridgeDirection'),

        # 先給預設值，下面會重算覆蓋
        'theta': float(data.get('theta', 0)),
        'theta_X': float(data.get('theta_X', 0)),
        'theta_Y': float(data.get('theta_Y', 0)),

        'fn': 1.0,
    }

    # ==== ▼▼▼ START: 【核心修正】後端強制重算屋頂角度 θ ▼▼▼ ====
    # 避免依賴前端傳值，確保 calculate_unified_h 能讀到正確的 theta
    h_eave = base_params['eave_height']
    h_ridge = base_params['ridge_height']
    delta_h = h_ridge - h_eave
    roof_type = base_params['roof_type']
    ridge_dir = base_params['ridge_orientation']
    b_x = base_params['B_X']
    b_y = base_params['B_Y']

    if delta_h > 0.01:
        # Case A: 山形 (Gable) - 底邊為跨度的一半
        if roof_type == 'gable':
            # 若屋脊平行X，跨度為Y方向 (B_Y)；若平行Y，跨度為X方向 (B_X)
            span = b_y if ridge_dir == 'X' else b_x
            if span > 0:
                # Gable: tan(theta) = delta_h / (Span / 2)
                base_params['theta'] = math.degrees(math.atan(delta_h / (span / 2)))

        # Case B: 單斜 (Shed) - 底邊為全跨度
        elif roof_type == 'shed':
            span = b_y if ridge_dir == 'X' else b_x
            if span > 0:
                # Shed: tan(theta) = delta_h / Span
                base_params['theta'] = math.degrees(math.atan(delta_h / span))

        # Case C: 四坡水 (Hip) - 計算後取較大值
        elif roof_type == 'hip':
            theta_x = 0
            theta_y = 0
            if b_y > 0:
                theta_x = math.degrees(math.atan(delta_h / (b_y / 2)))
            if b_x > 0:
                theta_y = math.degrees(math.atan(delta_h / (b_x / 2)))

            base_params['theta_X'] = theta_x
            base_params['theta_Y'] = theta_y
            base_params['theta'] = max(theta_x, theta_y)

    else:
        # 平屋頂或其他狀況
        base_params['theta'] = 0.0

    print(f"--- Service: 重算角度 θ = {base_params['theta']:.2f}° ---")
    # ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====

    # 2. 計算統一高度 h
    # 若前端傳入 manualHeight，則優先使用
    if data.get('buildingHeightMode') == 'manual':
        base_params['h'] = float(data.get('manualHeight', 0))
    else:
        base_params['h'] = calculate_unified_h(base_params)

    print(f"--- Service: 統一高度 h = {base_params['h']:.3f} m ---")

    # 3. 準備地形參數來源
    # 防呆：如果 data['topoX'] 不存在 (雖然前端應該會送)，給預設值
    topo_x_raw = data.get('topoX', {})
    topo_y_raw = data.get('topoY', {})

    topo_config = {
        'X': {
            'is_topo': topo_x_raw.get('type') != 'not_considered',
            'params': {
                'landform': landform_map.get(topo_x_raw.get('type')),
                'H': float(topo_x_raw.get('H', 0)),
                'Lh': float(topo_x_raw.get('Lh', 0)),
                'x_base': float(topo_x_raw.get('x', 0))
            }
        },
        'Y': {
            'is_topo': topo_y_raw.get('type') != 'not_considered',
            'params': {
                'landform': landform_map.get(topo_y_raw.get('type')),
                'H': float(topo_y_raw.get('H', 0)),
                'Lh': float(topo_y_raw.get('Lh', 0)),
                'x_base': float(topo_y_raw.get('x', 0))
            }
        }
    }

    # 4. 決定要執行的工況
    wind_directions_to_run = {
        'X': ['positive'],
        'Y': ['positive']
    }
    if topo_config['X']['is_topo']:
        wind_directions_to_run['X'] = ['positive', 'negative']
    if topo_config['Y']['is_topo']:
        wind_directions_to_run['Y'] = ['positive', 'negative']

    print(f">>> Service: 將執行的工況: {wind_directions_to_run}")

    all_results_by_case = {}

    # 提取計算方法選擇
    calc_method = data.get('calculationMethod', 'general')

    # 5. 執行計算迴圈
    for axis in ['X', 'Y']:
        for sign in wind_directions_to_run[axis]:
            case_params = base_params.copy()
            case_params['wind_direction'] = axis

            if axis == 'X':
                case_params['fn'] = float(data.get('fnX', 1.0))
            else:
                case_params['fn'] = float(data.get('fnY', 1.0))

            current_topo = topo_config[axis]
            case_params['is_topo_site'] = current_topo['is_topo']

            if current_topo['is_topo']:
                p = current_topo['params'].copy()
                p['x'] = p['x_base'] if sign == 'positive' else -p['x_base']
                case_params['topo_params'] = p
            else:
                case_params['topo_params'] = {}

            HandlerClass = get_handler_class(case_params['enclosure_status'], calc_method)

            if HandlerClass:
                try:
                    handler = HandlerClass(case_params)
                    result = handler.calculate()
                    case_id = f"{axis}_{sign}"
                    all_results_by_case[case_id] = result
                except Exception as e:
                    print(f"Error calculating case {axis}_{sign}: {e}")
                    import traceback
                    traceback.print_exc()
                    all_results_by_case[f"{axis}_{sign}"] = {'error': str(e)}
            else:
                # 若尚未實作的類型，暫時忽略或記錄
                pass

    return {
        'status': 'success',
        'calculated_h': base_params['h'],
        'data_by_case': all_results_by_case
    }

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
import numpy as np
from scipy.spatial.distance import pdist

from .BPandAnchor import bpN_mainAnalysis as analysis
from .BPandAnchor import bpN_Axial_ConcCheck as conc_check
from .BPandAnchor import bpN_tpCheck as tp_check
from .BPandAnchor import bpN_AnchorTensionCheck as anchor_tension_check
from .BPandAnchor import bpN_AnchorShearCheck as anchor_shear_check
from .BPandAnchor.bpN_utils import safe_dc_ratio
from datetime import datetime  # 【核心新增】匯入 datetime 模組
from django.utils import timezone
from accounts.models import Profile

import gc


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)


def find_loads_by_id(loads_list, combo_id):
    """在荷載組合列表中，根據 ID 尋找特定的荷載組合。"""
    if not loads_list or combo_id is None:
        return None
    return next((l for l in loads_list if l.get('id') == combo_id), None)


# ===== 【核心修正】將所有單位轉換常數定義在檔案頂層 =====
KIP_TO_TF = 0.453592
KIP_IN_TO_TF_M = 0.453592 * 0.0254
IN_TO_CM = 2.54
IN2_TO_CM2 = 2.54 * 2.54
KSI_TO_KGF_CM2 = 70.307
PSI_TO_KGF_CM2 = 0.070307


# ==========================================================


def get_shear_details(loads_combo, plate_params_local, bolt_params_local, unit_system_local, bolt_coords_imperial):
    VX_kips = loads_combo.get('vx_applied', 0)
    VY_kips = loads_combo.get('vy_applied', 0)
    TZ_kip_in = loads_combo.get('tz_applied', 0)

    if bolt_coords_imperial is None or len(bolt_coords_imperial) == 0:
        return None, None, None, None, None

    num_bolts = len(bolt_coords_imperial)
    J = float(np.sum(bolt_coords_imperial[:, 0] ** 2 + bolt_coords_imperial[:, 1] ** 2))

    table_data, demands_for_plot = [], []
    critical_bolt_info = {'index': -1, 'total_shear': -1.0}

    for i in range(num_bolts):
        xi, yi = bolt_coords_imperial[i, 0], bolt_coords_imperial[i, 1]

        # --- 所有分量都先用 kips 計算 ---
        v_direct_x_kips = VX_kips / num_bolts if num_bolts > 0 else 0
        v_direct_y_kips = VY_kips / num_bolts if num_bolts > 0 else 0
        v_torsion_x_kips = -TZ_kip_in * yi / J if J > 0 else 0
        v_torsion_y_kips = TZ_kip_in * xi / J if J > 0 else 0
        v_total_x_kips = v_direct_x_kips + v_torsion_x_kips
        v_total_y_kips = v_direct_y_kips + v_torsion_y_kips
        v_total_mag_kips = np.sqrt(v_total_x_kips ** 2 + v_total_y_kips ** 2)

        # demands_for_plot 永遠儲存英制數據 (kips)
        demands_for_plot.append({
            'index': i,  # <--- 【核心修正】把索引加進去
            'coord': [xi, yi],
            'Vua_x': v_total_x_kips,
            'Vua_y': v_total_y_kips,
            'Vua_total': v_total_mag_kips
        })

        # --- [核心修正] 在此處進行單位轉換 ---
        table_data.append({
            'index': i,
            'v_direct_x': v_direct_x_kips,
            'v_direct_y': v_direct_y_kips,
            'v_torsion_x': v_torsion_x_kips,
            'v_torsion_y': v_torsion_y_kips,
            'v_total_x': v_total_x_kips,
            'v_total_y': v_total_y_kips,
            'v_total_mag': v_total_mag_kips
        })

        if v_total_mag_kips > critical_bolt_info['total_shear']:
            critical_bolt_info['index'] = i
            critical_bolt_info['total_shear'] = v_total_mag_kips

    # totals 的計算現在是基於已轉換單位的 table_data，所以也是正確的
    totals = {
        'sum_vx': sum(row['v_total_x'] for row in table_data),
        'sum_vy': sum(row['v_total_y'] for row in table_data)
    }

    return bolt_coords_imperial, table_data, demands_for_plot, critical_bolt_info, totals


# View 1: 渲染輸入頁面
def bpandanchor(request):
    """
    這個 view 函式只做一件事：顯示輸入用的 HTML 樣板。
    """
    template_path = 'SteelDesign/BPandAnchor/steel_BPandAnchor_Input.html'
    return render(request, template_path)


def safe_dc_ratio(demand, capacity):
    """
    安全地計算 D/C Ratio。
    如果容量為 0 或 None，回傳 None (會被序列化為 JSON 的 null)。
    """
    if capacity is None or abs(capacity) < 1e-9:
        return None
    if demand is None:
        return 0.0
    return demand / capacity


CONVERSION_FACTORS = {
    'IN_TO_CM': 2.54,
    'PSI_TO_KGF_CM2': 0.070307,
}


@login_required
def bp_anchor_calculate_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # [核心修改] 將原始的輸入和荷載也存入 session
            request.session['latest_bp_anchor_inputs'] = json.dumps(data)
            request.session['latest_bp_anchor_loads'] = json.dumps(data.get('loads_combinations', []))
            unit_system = data.get('unit_system', 'imperial')

            has_any_tension = False
            has_any_shear = False

            # --- 1. 提取固定的幾何與材料參數 ---
            materials = data.get('materials', {})
            column_params = data.get('column_params', {})
            plate_params = data.get('plate_params', {})
            bolt_params = data.get('bolt_params', {})
            pedestal_params = data.get('pedestal_params', {})
            anchor_check_params = data.get('anchor_check_params', {})

            # 這是給 mainAnalysis 用的，永遠是英制
            ANCHOR_PARAMS = {
                'unit_system': unit_system,
                'anchor_type': anchor_check_params.get('anchor_install_type'),
                'anchor_structural_type': anchor_check_params.get('anchor_structural_type'),
                'Abrg': bolt_params.get('Abrg_in2'),
                'is_headed': anchor_check_params.get('anchor_structural_type') == 'headed',
                'hook_type': 'J' if anchor_check_params.get('anchor_structural_type') == 'hooked' else None,
                'longitudinal_rebar_size': pedestal_params.get('longitudinal_rebar_size'),
                'bolt_layout_mode': bolt_params.get('layout_mode'),
                'phi_cb': 0.70, 'phi_st': 0.75,
                'phi_pn': 0.70, 'phi_sfb': 0.70, 'phi_sv': 0.65, 'phi_cv': 0.70,
                'h_ef': anchor_check_params.get('h_ef'),
                'is_cracked': anchor_check_params.get('is_cracked'),
                'has_supplementary_reinf': anchor_check_params.get('has_supplementary_reinf'),
                'supplementary_rebar_size': anchor_check_params.get('supplementary_rebar_size'),
                'supplementary_rebar_spacing': anchor_check_params.get('supplementary_rebar_spacing'),
                'reinf_condition_shear': anchor_check_params.get('reinf_condition_shear'),
                'reinf_condition_tension': anchor_check_params.get('reinf_condition_shear', 0),
                'is_lightweight': anchor_check_params.get('is_lightweight'),
                'lambda_a': anchor_check_params.get('lambda_a', 1.0),
                'fc_psi': materials.get('fc_psi'),
                'fya_ksi': materials.get('bolt_fya_ksi'),
                'futa_ksi': materials.get('bolt_futa_ksi'),
            }
            PLATE_FY_KSI = plate_params.get('fy_ksi')
            PLATE_TP_IN = plate_params.get('tp_in')

            # --- 2. 建立追蹤字典和輔助函式 ---
            envelope_results = {}
            all_combos_summaries = []
            all_combos_dc_ratios = []  # [核心新增] 用於儲存每個組合的詳細 D/C Ratio

            max_concrete_pressure_info = {'value': -1.0, 'combo_id': None}
            A_plate_constant = None
            loads_combinations = data.get('loads_combinations', [])
            # 【核心新增】初始化一个变量来追踪全局最大总剪力
            max_total_shear_info = {
                'value': -1.0,
                'combo_id': None,
                'vux': 0.0,  # 新增
                'vuy': 0.0  # 新增
            }

            def update_envelope(check_name, current_result, combo_id, all_combo_results):
                if not current_result or 'result' not in current_result:
                    return  # 如果結果無效，直接返回

                # 獲取當前 envelope 中的記錄
                existing_envelope = envelope_results.get(check_name)

                # [核心修正] 檢查 'dc_ratio' 鍵是否存在且不為 None
                if 'dc_ratio' in current_result and current_result['dc_ratio'] is not None:
                    # 情況 1: 當前結果有有效的 dc_ratio
                    max_ratio = -1.0
                    # 檢查現有記錄是否也有有效的 dc_ratio
                    if existing_envelope and 'dc_ratio' in existing_envelope and existing_envelope.get(
                            'dc_ratio') is not None:
                        max_ratio = existing_envelope.get('dc_ratio', -1.0)

                    if current_result['dc_ratio'] > max_ratio:
                        envelope_results[check_name] = {
                            'dc_ratio': current_result['dc_ratio'],
                            'combo_id': combo_id,
                            'details': current_result,
                            'full_combo_results': all_combo_results
                        }
                elif existing_envelope is None:
                    # 情況 2: 當前結果是 N/A (dc_ratio 為 None 或不存在)，且 envelope 中還沒有此項的記錄
                    # 我們將這個 N/A 的結果作為一個佔位符存儲起來
                    envelope_results[check_name] = {
                        'dc_ratio': None,  # 使用 None 來表示無效值
                        'combo_id': combo_id,
                        'details': current_result,
                        'full_combo_results': all_combo_results
                    }

            bolt_coords_for_shear_details = analysis.get_bolt_coordinates(plate_params, bolt_params)

            # --- 3. 第一階段：遍歷所有荷載組合 ---
            for combo_index, loads in enumerate(loads_combinations):
                combo_id = loads.get('id', combo_index + 1)
                print(f"\n\n=====>>>>> STAGE 1: PROCESSING LOAD COMBO #{combo_id} <<<<<=====")

                # [核心新增] 為當前組合初始化一個 D/C Ratio 字典
                current_combo_dcs = {'combo_id': combo_id}

                analysis_results = analysis.perform_analysis(plate_shape=plate_params.get('shape'),
                                                             P_applied=loads.get('p_applied'),
                                                             Mx_applied=loads.get('mx_applied'),
                                                             My_applied=loads.get('my_applied'),
                                                             Es=materials.get('es_ksi'),
                                                             Ec=materials.get('ec_ksi'),
                                                             bolt_layout_mode=bolt_params.get('layout_mode'),
                                                             plate_params=plate_params,
                                                             bolt_params=bolt_params,
                                                             show_plot=False,
                                                             generate_plot_data=False,
                                                             unit_system=unit_system)

                if not analysis_results: continue

                if A_plate_constant is None:
                    A_plate_constant = analysis_results.get('A_plate')

                current_pressure = analysis_results.get('max_pressure', 0.0)
                if current_pressure > max_concrete_pressure_info['value']:
                    max_concrete_pressure_info['value'] = current_pressure
                    max_concrete_pressure_info['combo_id'] = combo_id

                check_results_for_combo = {}
                bolt_forces = np.array(analysis_results['bolt_forces'])
                num_tension_bolts = int(np.sum(bolt_forces > 0.001))

                # [核心新增] 更新全域拉力標記
                if num_tension_bolts > 0:
                    has_any_tension = True

                # 【核心新增】在每次循环中，计算并更新全局最大总剪力
                vx = loads.get('vx_applied', 0.0)
                vy = loads.get('vy_applied', 0.0)
                total_shear = np.sqrt(vx ** 2 + vy ** 2)
                if total_shear > max_total_shear_info['value']:
                    max_total_shear_info['value'] = total_shear
                    max_total_shear_info['combo_id'] = combo_id
                    max_total_shear_info['vux'] = vx  # 记录 Vux
                    max_total_shear_info['vuy'] = vy  # 记录 Vuy

                # 【核心新增】建立并储存当前组合的摘要
                summary_for_this_combo = {
                    'combo_id': combo_id,
                    'max_pressure_ksi': analysis_results['max_pressure'],
                    'num_tension_bolts': num_tension_bolts,
                    'max_tension_force_kips': float(np.max(bolt_forces)) if num_tension_bolts > 0 else 0.0
                }
                all_combos_summaries.append(summary_for_this_combo)

                # ==========================================================
                # ==== START: 【核心修改】為檢核準備 MKS 或 Imperial 參數 ====
                # ==========================================================

                # 複製一份給檢核函式專用的參數字典
                ANCHOR_PARAMS_FOR_CHECKS = ANCHOR_PARAMS.copy()
                pedestal_params_for_checks = pedestal_params.copy()
                bolt_params_for_checks = bolt_params.copy()  # 新增 bolt_params 的副本

                # 從分析結果中取出英制的座標
                bolt_coords_np_imperial = np.array(analysis_results['bolt_coords'])
                max_tension_idx = int(np.argmax(bolt_forces))
                max_tension_anchor_coord_imperial = tuple(bolt_coords_np_imperial[max_tension_idx])

                # 預設檢核參數為英制
                all_bolt_coords_for_checks = bolt_coords_np_imperial
                max_tension_anchor_coord_for_checks = max_tension_anchor_coord_imperial

                analysis_results_for_checks = analysis_results.copy()

                if unit_system == 'mks':
                    print("    - [views.py] 偵測到 MKS 單位，正在轉換檢核參數...")
                    # 轉換 ANCHOR_PARAMS_FOR_CHECKS 中的長度和應力
                    if ANCHOR_PARAMS_FOR_CHECKS.get('h_ef') is not None:
                        ANCHOR_PARAMS_FOR_CHECKS['h_ef'] *= CONVERSION_FACTORS['IN_TO_CM']
                    if ANCHOR_PARAMS_FOR_CHECKS.get('fc_psi') is not None:
                        ANCHOR_PARAMS_FOR_CHECKS['fc_psi'] *= CONVERSION_FACTORS['PSI_TO_KGF_CM2']

                    if ANCHOR_PARAMS_FOR_CHECKS.get('fya_ksi') is not None:
                        ANCHOR_PARAMS_FOR_CHECKS['fya_ksi'] = ANCHOR_PARAMS_FOR_CHECKS['fya_ksi'] * 1000
                        ANCHOR_PARAMS_FOR_CHECKS['fya_ksi'] *= CONVERSION_FACTORS['PSI_TO_KGF_CM2']

                    if ANCHOR_PARAMS_FOR_CHECKS.get('futa_ksi') is not None:
                        ANCHOR_PARAMS_FOR_CHECKS['futa_ksi'] = ANCHOR_PARAMS_FOR_CHECKS['futa_ksi'] * 1000
                        ANCHOR_PARAMS_FOR_CHECKS['futa_ksi'] *= CONVERSION_FACTORS['PSI_TO_KGF_CM2']

                    if ANCHOR_PARAMS_FOR_CHECKS.get('Abrg') is not None:
                        ANCHOR_PARAMS_FOR_CHECKS['Abrg'] *= CONVERSION_FACTORS['IN_TO_CM'] ** 2

                    # 轉換 pedestal_params_for_checks 中的長度
                    for key in ['N', 'B', 'D', 'h']:
                        if pedestal_params_for_checks.get(key) is not None:
                            pedestal_params_for_checks[key] *= CONVERSION_FACTORS['IN_TO_CM']

                    # 轉換所有座標
                    all_bolt_coords_for_checks = bolt_coords_np_imperial * CONVERSION_FACTORS['IN_TO_CM']
                    max_tension_anchor_coord_for_checks = tuple(all_bolt_coords_for_checks[max_tension_idx])
                    analysis_results_for_checks['bolt_coords'] = all_bolt_coords_for_checks.tolist()

                # =========================================================================
                # ==== START: 移植自 bpN_Main.py 的檢核邏輯 (if analysis_results: 之後) ====
                # =========================================================================
                if analysis_results:
                    analysis_results['bolt_params_for_check'] = bolt_params

                    bolt_forces = np.array(analysis_results['bolt_forces'])
                    bolt_coords_np = np.array(analysis_results['bolt_coords'])
                    num_tension_bolts = int(np.sum(bolt_forces > 0.001))

                    # 將摘要資訊存入結果字典 (注意 NumPy array 轉換)
                    check_results_for_combo['analysis_summary'] = {
                        'status': analysis_results['status'],
                        'max_pressure_ksi': analysis_results['max_pressure'],
                        'concrete_force_Bu_kips': analysis_results['concrete_force_Bu'],
                        'num_tension_bolts': num_tension_bolts,
                        'num_total_bolts': analysis_results['num_bolts'],
                        'bolt_forces_kips': bolt_forces.tolist(),
                        'bolt_coords_in': np.array(analysis_results['bolt_coords']).tolist()
                    }

                    # --- 檢核 A: 混凝土承壓 ---
                    if analysis_results['concrete_force_Bu'] > 1e-6:
                        # 直接将函式的回传结果赋値给字典
                        check_results_for_combo['concrete_bearing_check'] = conc_check.perform_bearing_check(
                            analysis_results,
                            pedestal_params,
                            materials.get('fc_psi'),
                            unit_system=unit_system
                        )
                        if 'concrete_bearing_check' in check_results_for_combo:
                            check_results_for_combo['concrete_bearing_check']['f_pu_max_ksi'] = analysis_results.get(
                                'max_pressure')
                        current_combo_dcs['bearing'] = check_results_for_combo['concrete_bearing_check'].get('dc_ratio')
                    else:
                        check_results_for_combo['concrete_bearing_check'] = {'result': 'N/A',
                                                                             'message': '無混凝土壓力，不需檢核。'}
                        current_combo_dcs['bearing'] = None  # 或 0.0

                    # --- 檢核 B: 基礎版彎曲 (厚度) ---
                    if analysis_results['max_pressure'] > 1e-6 or np.any(bolt_forces > 0):
                        # 準備傳遞給彎曲檢核函式的資料
                        simplified_grid_data = None
                        if analysis_results.get('grid_pressures') is not None:
                            grid_data = analysis_results.get('grid_data', {})
                            cell_area_val = grid_data.get('ca')
                            if cell_area_val is None and 'xv' in grid_data:
                                xv = np.array(grid_data['xv'])
                                cell_area_val = (xv[0, 1] - xv[0, 0]) ** 2

                            simplified_grid_data = {
                                'xv': grid_data.get('xv'), 'yv': grid_data.get('yv'),
                                'pressures': analysis_results['grid_pressures'],
                                'cell_area': cell_area_val
                            }
                        analysis_results_for_tp_check = {
                            'grid_data': simplified_grid_data,
                            'bolt_coords': analysis_results['bolt_coords'],
                            'bolt_forces': analysis_results['bolt_forces'],
                            'plate_B': analysis_results['plate_B'],
                            'plate_N': analysis_results['plate_N'],
                            'plate_params': plate_params  # [核心新增] 傳遞完整的 plate_params
                        }
                        tp_res = tp_check.perform_plate_bending_check(
                            analysis_results=analysis_results,  # 傳遞完整的分析結果
                            column_params=column_params,
                            materials=materials,  # 傳遞材料參數
                            plate_params=plate_params,
                            plate_fy_ksi=PLATE_FY_KSI,
                            plate_tp_in=PLATE_TP_IN,
                            generate_plot=False,
                            unit_system=unit_system
                        )
                        check_results_for_combo['plate_bending_check'] = tp_res
                        current_combo_dcs['bending'] = check_results_for_combo['plate_bending_check'].get('dc_ratio')
                    else:
                        check_results_for_combo['plate_bending_check'] = {'result': 'N/A',
                                                                          'message': '無彎矩作用，不需檢核。'}
                        current_combo_dcs['bending'] = None

                    # 檢核 C: 錨栓拉力
                    if num_tension_bolts > 0:
                        tension_checks = {}
                        max_tension_force_Nua = float(np.max(bolt_forces))
                        max_tension_idx = int(np.argmax(bolt_forces))
                        max_tension_anchor_coord = tuple(bolt_coords_np[max_tension_idx])

                        # C1: 鋼材拉力強度 (Nsa)
                        nsa_res = anchor_tension_check.calculate_steel_strength_Nsa(bolt_params, ANCHOR_PARAMS)
                        phi_Nsa = nsa_res['phi_Nsa']
                        dc_ratio_nsa = safe_dc_ratio(max_tension_force_Nua, phi_Nsa)  # 現在 phi_Nsa 永遠是 kips
                        tension_checks['steel_strength_Nsa'] = {
                            **nsa_res,
                            'demand': max_tension_force_Nua,
                            'dc_ratio': dc_ratio_nsa,
                            'result': 'PASS' if dc_ratio_nsa is not None and dc_ratio_nsa <= 1.0 else 'FAIL',
                            'anchor_index': max_tension_idx
                        }

                        # C2: 拔出強度 (Npn)
                        npn_res = anchor_tension_check.calculate_pullout_strength_Npn(analysis_results, ANCHOR_PARAMS)
                        phi_Npn = npn_res['phi_Npn']
                        dc_ratio_npn = safe_dc_ratio(max_tension_force_Nua, phi_Npn)

                        tension_checks['pullout_strength_Npn'] = {
                            **npn_res,
                            'demand': max_tension_force_Nua,
                            'dc_ratio': dc_ratio_npn,
                            'result': 'PASS' if dc_ratio_npn is not None and dc_ratio_npn <= 1.0 else 'FAIL',
                            'anchor_index': max_tension_idx  # <-- [核心新增] 加入錨栓索引
                        }

                        # C3: Ncb & Ncbg
                        ncb_results = {}
                        ncb_res = anchor_tension_check.calculate_single_anchor_breakout_Ncb(
                            analysis_results_for_checks['bolt_coords'][max_tension_idx],  # <-- 使用轉換後的座標
                            pedestal_params_for_checks,  # <-- 使用轉換後的墩柱參數
                            ANCHOR_PARAMS_FOR_CHECKS,  # <-- 使用轉換後的錨栓參數
                            all_bolt_coords=all_bolt_coords_for_checks.tolist()  # <-- 使用轉換後的所有座標
                        )
                        if ncb_res:
                            phi_Ncb_for_ratio = ncb_res['phi_Ncb'] if unit_system == 'imperial' else ncb_res[
                                                                                                         'phi_Ncb'] / KIP_TO_TF
                            use_special_formula = ncb_res.get('use_special_formula', None)
                            # [核心修正] 使用 kips/kips 計算 dc_ratio
                            dc_ratio_ncb = safe_dc_ratio(max_tension_force_Nua, phi_Ncb_for_ratio)
                            ncb_results['single'] = {
                                **ncb_res,
                                'demand': max_tension_force_Nua,
                                'use_special_formula': use_special_formula,
                                'dc_ratio': dc_ratio_ncb,
                                'result': 'PASS' if dc_ratio_ncb is not None and dc_ratio_ncb <= 1.0 else 'FAIL'
                            }

                        if num_tension_bolts > 1:
                            tension_indices = np.where(bolt_forces > 0.001)[0]
                            tension_coords = np.array(analysis_results['bolt_coords'])[tension_indices]

                            max_spacing = np.max(pdist(tension_coords)) if len(tension_coords) > 1 else 0
                            critical_spacing = 3 * ANCHOR_PARAMS['h_ef']

                            # [核心修改] 為 Ncbg 準備繪圖所需的參數
                            ANCHOR_PARAMS_FOR_NCBG_PLOT = ANCHOR_PARAMS.copy()
                            pedestal_params_for_ncbg_plot = pedestal_params.copy()
                            analysis_results_for_ncbg_plot = analysis_results.copy()

                            if unit_system == 'mks':
                                if ANCHOR_PARAMS_FOR_NCBG_PLOT.get('h_ef') is not None:
                                    ANCHOR_PARAMS_FOR_NCBG_PLOT['h_ef'] *= CONVERSION_FACTORS['IN_TO_CM']
                                if ANCHOR_PARAMS_FOR_NCBG_PLOT.get('fc_psi') is not None:
                                    ANCHOR_PARAMS_FOR_NCBG_PLOT['fc_psi'] *= CONVERSION_FACTORS['PSI_TO_KGF_CM2']
                                for key in ['N', 'B', 'D', 'h']:
                                    if pedestal_params_for_ncbg_plot.get(key) is not None:
                                        pedestal_params_for_ncbg_plot[key] *= CONVERSION_FACTORS['IN_TO_CM']
                                analysis_results_for_ncbg_plot['bolt_coords'] = (
                                        np.array(analysis_results['bolt_coords']) * CONVERSION_FACTORS[
                                    'IN_TO_CM']).tolist()

                            # [核心修改] 呼叫函式時，增加 generate_plot=True
                            group_ncbg_res = anchor_tension_check.calculate_group_breakout_Ncbg(
                                analysis_results_for_ncbg_plot,
                                pedestal_params_for_ncbg_plot,
                                ANCHOR_PARAMS_FOR_NCBG_PLOT,
                                generate_plot=False
                            )
                            if group_ncbg_res:
                                total_tension_force = np.sum(bolt_forces[tension_indices])

                                # [核心修正] 確保 D/C Ratio 計算單位正確
                                phi_Ncbg_for_ratio = group_ncbg_res['phi_Ncbg']
                                if unit_system == 'mks':
                                    phi_Ncbg_for_ratio /= KIP_TO_TF

                                # [核心修正] 使用 kips/kips 計算 dc_ratio
                                dc_ratio_group = safe_dc_ratio(total_tension_force, phi_Ncbg_for_ratio)
                                group_ncbg_res['dc_ratio'] = dc_ratio_group
                                group_ncbg_res['demand'] = total_tension_force
                                group_ncbg_res['result'] = 'PASS' if dc_ratio_group <= 1.0 else 'FAIL'

                                # [核心新增] 重新命名 plot_base64 的鍵
                                if 'plot_base64' in group_ncbg_res and group_ncbg_res['plot_base64']:
                                    group_ncbg_res['ancg_plot_base64'] = group_ncbg_res.pop('plot_base64')

                                ncb_results['group'] = group_ncbg_res

                        tension_checks['concrete_breakout_Ncb'] = ncb_results

                        # ==========================================================
                        # ==== START: 【核心新增】C4: Nsb & Nsbg 完整檢核邏輯 ====
                        # ==========================================================
                        # 1. 預先建立 nsb_results 字典結構
                        nsb_results = {
                            'single': {'result': 'N/A', 'dc_ratio': None, 'message': '未計算'},
                            'group': {'result': 'N/A', 'dc_ratio': None, 'message': '未計算'}
                        }
                        tension_indices = np.where(bolt_forces > 0.001)[0]
                        tension_coords = bolt_coords_np[tension_indices]

                        # --- a) 單根錨栓檢核 (Nsb) ---
                        max_dc_ratio_nsb = -1.0
                        critical_nsb_anchor_info = None  # 【修正1】初始值设为 None
                        nsb_applicable_at_all = False
                        all_ca1_results = []

                        # 4a. 遍歷所有受拉錨栓，找出最不利的單根 Nsb D/C Ratio
                        print(f"\n  --- 單根錨栓混凝土邊緣脹破强度 (Nsb) 计算流程 ---")
                        for i in tension_indices:
                            current_anchor_coord_for_check = tuple(analysis_results_for_checks['bolt_coords'][i])
                            nsb_res = (anchor_tension_check.
                            calculate_side_face_blowout_for_single_anchor(
                                current_anchor_coord_for_check,  # <--- 使用新變數
                                pedestal_params_for_checks,
                                ANCHOR_PARAMS_FOR_CHECKS,
                                bolt_params,
                                all_bolt_coords=analysis_results_for_checks['bolt_coords'],
                                generate_plot=False
                            ))
                            if nsb_res:
                                nsb_applicable_at_all = True
                                if 'ca1' in nsb_res:
                                    all_ca1_results.append(
                                        {'index': i, 'coord': current_anchor_coord_for_check, 'ca1': nsb_res['ca1']})

                                phi_Nsb_kips = nsb_res['phi_Nsb']
                                if unit_system == 'mks':
                                    # 如果是 mks，將公制容量轉回英制來計算 ratio
                                    phi_Nsb_kips = nsb_res['phi_Nsb'] / KIP_TO_TF

                                demand = bolt_forces[i]  # demand 永遠是 kips

                                dc_ratio_i = safe_dc_ratio(demand, phi_Nsb_kips)  # 現在是 kips / kips
                                if dc_ratio_i is not None and dc_ratio_i > max_dc_ratio_nsb:
                                    max_dc_ratio_nsb = dc_ratio_i
                                    critical_nsb_anchor_info = {
                                        **nsb_res,
                                        'anchor_index': int(i),
                                        'demand': float(demand),
                                        'dc_ratio': float(dc_ratio_i),
                                        'result': 'PASS' if dc_ratio_i <= 1.0 else 'FAIL'
                                    }

                        if critical_nsb_anchor_info:
                            # [核心修正] 修正 print 語句中的 phi_Nsb 來源
                            phi_Nsb_display = critical_nsb_anchor_info['phi_Nsb']
                            print(f"    - 需求強度 = {critical_nsb_anchor_info['demand']}")
                            print(f"    - 設計強度 ΦNsb = {phi_Nsb_display}")
                            print(f"    - ratio = {critical_nsb_anchor_info['dc_ratio']}")

                        if nsb_applicable_at_all:
                            if critical_nsb_anchor_info:
                                nsb_results['single'] = critical_nsb_anchor_info
                            else:
                                # 檢核适用，但所有 D/C ratio 都很小或为 None (capacity=0)
                                nsb_results['single'] = {'result': 'PASS', 'dc_ratio': 0.0,
                                                         'message': '所有适用錨栓的 D/C Ratio 均合格或因容量为零而无法计算。'}

                            if 'plot_base64' in critical_nsb_anchor_info and critical_nsb_anchor_info['plot_base64']:
                                critical_nsb_anchor_info['nsb_plot_base64'] = critical_nsb_anchor_info.pop(
                                    'plot_base64')
                            nsb_results['single'] = critical_nsb_anchor_info
                        else:
                            nsb_results['single'] = {'result': 'N/A', 'dc_ratio': None,
                                                     'message': '所有受拉錨栓均不满足侧向胀破的几何条件 (h_ef <= 2.5ca1)。'}

                        # --- b) 錨栓群组檢核 (Nsbg) ---
                        nsbg_res_kips = anchor_tension_check.calculate_side_face_blowout_for_group(
                            analysis_results_for_checks,
                            pedestal_params_for_checks,
                            ANCHOR_PARAMS_FOR_CHECKS,
                            bolt_params_for_checks,
                            generate_plot=True  # 要求生成圖表
                        )
                        # [核心修正] 在 views.py 中進行最終的單位轉換
                        if nsbg_res_kips and nsbg_res_kips.get('result') != 'N/A':
                            if unit_system == 'mks':
                                # 如果是 MKS，將從計算函式收到的 kips 值轉換為 tf
                                # nsbg_res_kips['demand'] = nsbg_res_kips['demand'] * KIP_TO_TF
                                nsbg_res_kips['capacity'] = nsbg_res_kips['capacity'] * KIP_TO_TF
                                nsbg_res_kips['Nsbg'] = nsbg_res_kips['Nsbg'] * KIP_TO_TF
                                nsbg_res_kips['base_anchor_nsb'] = nsbg_res_kips['base_anchor_nsb'] * KIP_TO_TF

                            if 'plot_base64' in nsbg_res_kips and nsbg_res_kips['plot_base64']:
                                nsbg_res_kips['nsbg_plot_base64'] = nsbg_res_kips.pop('plot_base64')

                            nsb_results['group'] = nsbg_res_kips
                        else:
                            # 如果計算不適用，直接賦值
                            nsb_results['group'] = nsbg_res_kips

                        tension_checks['side_face_blowout_Nsb'] = nsb_results
                        # ==========================================================
                        # ==== END: C4 Nsb/Nsbg 檢核邏輯 ====
                        # ==========================================================

                        current_combo_dcs['nsa'] = tension_checks.get('steel_strength_Nsa', {}).get('dc_ratio')
                        current_combo_dcs['npn'] = tension_checks.get('pullout_strength_Npn', {}).get('dc_ratio')
                        current_combo_dcs['ncb'] = (
                            tension_checks.get('concrete_breakout_Ncb', {}).get('single', {}).get('dc_ratio'))
                        current_combo_dcs['ncbg'] = (
                            tension_checks.get('concrete_breakout_Ncb', {}).get('group', {}).get('dc_ratio'))
                        current_combo_dcs['nsb'] = (
                            tension_checks.get('side_face_blowout_Nsb', {}).get('single', {}).get('dc_ratio'))
                        current_combo_dcs['nsbg'] = (
                            tension_checks.get('side_face_blowout_Nsb', {}).get('group', {}).get('dc_ratio'))

                        check_results_for_combo['anchor_tension_checks'] = tension_checks
                    else:
                        check_results_for_combo['anchor_tension_checks'] = {'result': 'N/A',
                                                                            'message': '無受拉錨栓，跳過拉力檢核。'}
                        for key in ['nsa', 'npn', 'ncb', 'ncbg', 'nsb', 'nsbg']: current_combo_dcs[key] = None

                    # --- 檢核 D: 錨栓剪力 (整合扭力) ---
                    VX_APPLIED = loads.get('vx_applied', 0.0)
                    VY_APPLIED = loads.get('vy_applied', 0.0)
                    TZ_APPLIED = loads.get('tz_applied', 0.0)

                    if abs(VX_APPLIED) > 1e-6 or abs(VY_APPLIED) > 1e-6 or abs(TZ_APPLIED) > 1e-6:
                        has_any_shear = True
                        shear_checks = {}
                        num_bolts = analysis_results['num_bolts']
                        bolt_coords = np.array(analysis_results['bolt_coords'])
                        all_bolt_coords = bolt_coords  # for breakout checks

                        # 1. 計算螺栓群極慣性矩 J
                        J = float(np.sum(bolt_coords[:, 0] ** 2 + bolt_coords[:, 1] ** 2))

                        # 2. 計算每個錨栓的剪力需求 (向量疊加)
                        max_vua_total = 0.0
                        critical_bolt_info = {}
                        bolt_shear_demands = []
                        for i in range(num_bolts):
                            xi, yi = bolt_coords[i, 0], bolt_coords[i, 1]
                            v_direct_x = VX_APPLIED / num_bolts if num_bolts > 0 else 0
                            v_direct_y = VY_APPLIED / num_bolts if num_bolts > 0 else 0
                            v_torsion_x = -TZ_APPLIED * yi / J if J > 0 else 0
                            v_torsion_y = TZ_APPLIED * xi / J if J > 0 else 0
                            v_total_x = v_direct_x + v_torsion_x
                            v_total_y = v_direct_y + v_torsion_y
                            v_total_mag = np.sqrt(v_total_x ** 2 + v_total_y ** 2)

                            # [核心修正] 統一鍵名，與 get_shear_details 保持一致
                            bolt_demands = {
                                'index': i,
                                'coord': [xi, yi],
                                'v_direct_x': v_direct_x,
                                'v_direct_y': v_direct_y,
                                'v_torsion_x': v_torsion_x,
                                'v_torsion_y': v_torsion_y,
                                'v_total_x': v_total_x,
                                'v_total_y': v_total_y,
                                'v_total_mag': v_total_mag  # <--- 使用 'v_total_mag'
                            }
                            bolt_shear_demands.append(bolt_demands)
                            if v_total_mag > max_vua_total:
                                max_vua_total = v_total_mag
                                # critical_bolt_info 也使用新的結構
                                critical_bolt_info = bolt_demands

                        shear_checks['bolt_shear_demands'] = bolt_shear_demands
                        shear_checks['critical_demand'] = critical_bolt_info

                        # D1: Vsa - 使用最大總剪力檢核
                        vsa_res = anchor_shear_check.calculate_steel_strength_Vsa(bolt_params_for_checks,
                                                                                  ANCHOR_PARAMS_FOR_CHECKS)
                        phi_Vsa = vsa_res['phi_Vsa']
                        has_grout_pad = vsa_res['has_grout_pad']

                        dc_ratio_vsa = safe_dc_ratio(max_vua_total, phi_Vsa)  # [修正]
                        shear_checks['steel_strength_Vsa'] = {
                            **vsa_res,
                            'demand': max_vua_total,
                            'dc_ratio': dc_ratio_vsa,
                            'result': 'PASS' if dc_ratio_vsa <= 1.0 else 'FAIL'
                        }

                        # D2: Vcb & Vcbg
                        print("\n  --- 單根錨栓混凝土剪破強度 (Vcb) 檢核流程 ---")
                        vcb_results = {}
                        all_bolt_coords = bolt_coords_np
                        has_shear_x = any(abs(d['v_total_x']) > 1e-6 for d in bolt_shear_demands)

                        # --- a) Vcb - X 方向檢核 (遍歷所有錨栓) ---
                        if has_shear_x:
                            highest_dc_ratio_x = -1.0
                            critical_vcbx_info = {}

                            for bolt_demand in bolt_shear_demands:
                                anchor_coord_for_check = tuple(
                                    analysis_results_for_checks['bolt_coords'][bolt_demand['index']])
                                # X方向的檢核，只考慮X方向的剪力分量
                                vua_x = abs(bolt_demand['v_total_x'])

                                if vua_x > 1e-6:
                                    # 剪力方向向量
                                    direction_x = (1, 0) if bolt_demand['v_total_x'] > 0 else (-1, 0)
                                    vcb_x_res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                                        anchor_coord_for_check,
                                        direction_x,
                                        pedestal_params_for_checks,
                                        ANCHOR_PARAMS_FOR_CHECKS,
                                        bolt_params_for_checks,
                                        all_bolt_coords=all_bolt_coords_for_checks.tolist(),  # 傳入所有錨栓座標
                                        generate_plot=False  # 要求生成圖表
                                    )
                                    if vcb_x_res:
                                        phi_Vcb_x = vcb_x_res['phi_Vcb']
                                        demand = abs(vua_x)
                                        dc_ratio_x = safe_dc_ratio(demand, phi_Vcb_x)
                                        if dc_ratio_x is not None and dc_ratio_x > highest_dc_ratio_x:
                                            highest_dc_ratio_vcbx = dc_ratio_x
                                            critical_vcbx_info = {
                                                **vcb_x_res,
                                                'anchor_index': bolt_demand['index'],
                                                'demand': demand,
                                                'dc_ratio': dc_ratio_x,
                                                'result': 'PASS' if dc_ratio_x <= 1.0 else 'FAIL'
                                            }
                            if critical_vcbx_info:
                                # 找到這個檢核對應的 load combo
                                vcbx_combo_id = combo_id
                                vcbx_loads = loads

                                # 呼叫 get_shear_details 獲取該工況下的詳細剪力數據
                                bolt_coords_imperial, table_data, demands_imperial, _, totals = get_shear_details(
                                    vcbx_loads, plate_params, bolt_params, unit_system, all_bolt_coords_for_checks)

                                if bolt_coords_imperial is not None:
                                    # [核心重構] 準備繪圖參數
                                    plot_bolt_coords = bolt_coords_imperial.copy()
                                    plot_plate_params = plate_params.copy()
                                    plot_demands = demands_imperial.copy()  # 複製一份 demands

                                    if unit_system == 'mks':
                                        # 如果是 mks，將所有傳給繪圖函式的幾何數據都轉為 cm
                                        plot_bolt_coords *= CONVERSION_FACTORS['IN_TO_CM']
                                        for key in ['B', 'N', 'outer_radius']:
                                            if key in plot_plate_params:
                                                plot_plate_params[key] *= CONVERSION_FACTORS['IN_TO_CM']
                                        # 同時也要轉換 demands 中的座標！
                                        for demand in plot_demands:
                                            demand['coord'] = (np.array(demand['coord']) * CONVERSION_FACTORS[
                                                'IN_TO_CM']).tolist()

                                    # 生成剪力分佈圖
                                    plot_title = f"Vcb-X 控制工況剪力分佈圖 (Combo #{vcbx_combo_id})"
                                    shear_plot = analysis.generate_shear_vector_plot(
                                        plot_bolt_coords,
                                        plot_demands,
                                        plot_plate_params,
                                        pedestal_params,  # <--- 新增
                                        column_params,  # <--- 新增
                                        bolt_params,
                                        critical_bolt_index=critical_vcbx_info.get('anchor_index'),  # <-- 正確
                                        title=plot_title,
                                        unit_system=unit_system,
                                        vector_type='components',
                                        display_direction='X'
                                    )

                                # 將所有數據注入 critical_vcbx_info
                                critical_vcbx_info['shear_distribution_plot'] = shear_plot
                                critical_vcbx_info['shear_table_data'] = table_data
                                critical_vcbx_info['shear_table_totals'] = totals
                                if 'plot_base64' in critical_vcbx_info:
                                    critical_vcbx_info['avc_plot_base64'] = critical_vcbx_info.pop('plot_base64')

                            vcb_results['single_critical_x'] = critical_vcbx_info if critical_vcbx_info else {
                                'result': 'N/A', 'message': '無適用的 X 向剪力檢核'}

                        # --- b) Vcb - Y 方向檢核 (遍歷所有錨栓) ---
                        has_shear_y = any(abs(d['v_total_y']) > 1e-6 for d in bolt_shear_demands)
                        if has_shear_y:
                            highest_dc_ratio_y = -1.0
                            critical_vcby_info = {}

                            for bolt_demand in bolt_shear_demands:
                                anchor_coord_for_check = tuple(
                                    analysis_results_for_checks['bolt_coords'][bolt_demand['index']])
                                vua_y = abs(bolt_demand['v_total_y'])

                                if vua_y > 1e-6:
                                    direction_y = (0, 1) if bolt_demand['v_total_y'] > 0 else (0, -1)
                                    # [核心修改] 呼叫 Vcb 計算時，要求生成圖表
                                    vcb_y_res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                                        anchor_coord_for_check,
                                        direction_y,
                                        pedestal_params_for_checks,
                                        ANCHOR_PARAMS_FOR_CHECKS,
                                        bolt_params_for_checks,
                                        all_bolt_coords=all_bolt_coords_for_checks.tolist(),
                                        generate_plot=False
                                    )

                                    if vcb_y_res:
                                        phi_Vcb_y = vcb_y_res['phi_Vcb']
                                        demand = abs(vua_y)
                                        dc_ratio_y = safe_dc_ratio(demand, phi_Vcb_y)
                                        if dc_ratio_y is not None and dc_ratio_y > highest_dc_ratio_y:
                                            highest_dc_ratio_vcby = dc_ratio_y
                                            critical_vcby_info = {
                                                **vcb_y_res,
                                                'anchor_index': bolt_demand['index'],
                                                'demand': demand,
                                                'dc_ratio': dc_ratio_y,
                                                'result': 'PASS' if dc_ratio_y <= 1.0 else 'FAIL'
                                            }
                            # [核心新增] 在找到最不利的 Vcby 檢核後，為其準備附屬圖表
                            if critical_vcby_info:
                                vcby_combo_id = combo_id
                                vcby_loads = loads

                                bolt_coords_imperial, table_data, demands_imperial, _, totals = get_shear_details(
                                    vcby_loads, plate_params, bolt_params, unit_system, all_bolt_coords_for_checks)

                                plot_bolt_coords_for_shear_plot = bolt_coords_imperial.copy()
                                plot_plate_params_for_shear_plot = plate_params.copy()
                                if unit_system == 'mks':
                                    plot_bolt_coords_for_shear_plot *= CONVERSION_FACTORS['IN_TO_CM']
                                    for key in ['B', 'N', 'outer_radius']:
                                        if key in plot_plate_params_for_shear_plot:
                                            plot_plate_params_for_shear_plot[key] *= CONVERSION_FACTORS['IN_TO_CM']

                                plot_title = f"Vcb-Y 控制工況剪力分佈圖 (Combo #{vcby_combo_id})"
                                print(critical_vcby_info.get('anchor_index'))
                                shear_plot = analysis.generate_shear_vector_plot(
                                    plot_bolt_coords_for_shear_plot,
                                    demands_imperial,
                                    plot_plate_params_for_shear_plot,
                                    pedestal_params,
                                    column_params,
                                    bolt_params,
                                    critical_bolt_index=critical_vcby_info.get('anchor_index'),  # <-- 正確
                                    title=plot_title,
                                    unit_system=unit_system,
                                    vector_type='components',
                                    display_direction='Y'
                                )

                                critical_vcby_info['shear_distribution_plot'] = shear_plot
                                critical_vcby_info['shear_table_data'] = table_data
                                critical_vcby_info['shear_table_totals'] = totals

                                if 'plot_base64' in critical_vcby_info:
                                    critical_vcby_info['avc_plot_base64'] = critical_vcby_info.pop('plot_base64')

                            vcb_results['single_critical_y'] = critical_vcby_info if critical_vcby_info else {
                                'result': 'N/A', 'message': '無適用的 Y 向剪力檢核'}

                        print("\n--- 錨栓群混凝土剪破強度檢核 (Vcbg) ---")

                        # --- [核心修正] Vcbg - 錨栓群混凝土剪破强度檢核 ---
                        vcb_results['group_x'] = {'result': 'N/A', 'dc_ratio': None, 'message': '未计算 X 方向群组檢核'}
                        vcb_results['group_y'] = {'result': 'N/A', 'dc_ratio': None, 'message': '未计算 Y 方向群组檢核'}
                        all_bolt_coords = bolt_coords_np

                        # X方向群组檢核
                        if has_shear_x:
                            rounding_decimals = 4
                            coords_for_grouping_x = np.where(np.abs(all_bolt_coords) < 1e-9, 0, all_bolt_coords)
                            unique_x_coords = sorted(list(set(
                                round(c[0], rounding_decimals) for c in coords_for_grouping_x
                            )))

                            message_x = "錨栓只有一排，无需群组檢核。"
                            needs_group_check_x = False

                            if len(unique_x_coords) > 1:
                                # 2. 【核心修正】计算所有相邻排之间的平行间距，并找出最小值
                                spacings_x = [unique_x_coords[i + 1] - unique_x_coords[i] for i in
                                              range(len(unique_x_coords) - 1)]
                                s_parallel_x_min = min(spacings_x)

                                # 3. 确定最外排的 X 坐标
                                outermost_x = unique_x_coords[-1] if VX_APPLIED >= 0 else unique_x_coords[0]

                                # 4. 计算最外排的参考 ca1 (取该排錨栓中的最小值)
                                outer_row_bolts_x = [c for c in all_bolt_coords if
                                                     round(c[0], rounding_decimals) == outermost_x]
                                ca1_values_x = []
                                for c in outer_row_bolts_x:
                                    res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                                        c, (np.sign(VX_APPLIED) if VX_APPLIED != 0 else 0, 0),
                                        pedestal_params, ANCHOR_PARAMS, bolt_params
                                    )
                                    if res and res.get('ca1') is not None:
                                        ca1_values_x.append(res['ca1'])

                                if ca1_values_x:
                                    ca1_group_x = min(ca1_values_x)
                                    if s_parallel_x_min <= 3 * ca1_group_x:
                                        needs_group_check_x = True
                                        message_x = f"存在錨栓排，且最小平行间距 s_x_min={s_parallel_x_min:.2f} in <= 3*ca1={3 * ca1_group_x:.2f} in，需进行群组檢核。"
                                    else:
                                        message_x = f"所有錨栓排的最小平行间距 s_x_min={s_parallel_x_min:.2f} in > 3*ca1={3 * ca1_group_x:.2f} in，无需群组檢核。"
                                else:
                                    message_x = "无法计算最外排的 ca1，跳過群组檢核。"

                            if needs_group_check_x:
                                # 如果需要檢核，调用复杂的计算函数
                                vcbg_combinations_x = anchor_shear_check.calculate_group_shear_breakout_Vcbg(
                                    direction_x,
                                    pedestal_params_for_checks,
                                    ANCHOR_PARAMS_FOR_CHECKS,
                                    bolt_params_for_checks,
                                    all_bolt_coords_for_checks,
                                    bolt_shear_demands,
                                    generate_plot=True  # <--- 確保這裡永遠是 True
                                )
                                if vcbg_combinations_x:
                                    critical_vcbg_x_res = min(vcbg_combinations_x, key=lambda x: x['phi_Vcbg'])
                                    capacity_x = critical_vcbg_x_res['phi_Vcbg']
                                    demand_x = abs(VX_APPLIED)
                                    dc_ratio_x = safe_dc_ratio(demand_x, capacity_x)

                                    # 1. 提取參與檢核的錨栓索引號碼
                                    anchor_indices = critical_vcbg_x_res.get('controlling_anchor_indices', [])

                                    # 2. 將索引號碼格式化為 "#0, #1, #2" 的字串
                                    if anchor_indices:
                                        anchors_text = ", ".join([f"#{i}" for i in anchor_indices])
                                        group_description = f"最不利狀態之錨栓群包含錨栓 {anchors_text}。"
                                    else:
                                        group_description = "由最不利錨栓群控制。"

                                    # 3. 創建新的、更完整的描述
                                    full_description = f"此檢核由載重组合 <b>#{combo_id}</b> 控制。{group_description}"

                                    # 4. 將新描述存入結果字典
                                    critical_vcbg_x_res['full_description'] = full_description

                                    # [核心移除] 刪除舊的 message 欄位
                                    if 'message' in critical_vcbg_x_res:
                                        del critical_vcbg_x_res['message']

                                    vcbgx_combo_id = combo_id
                                    vcbgx_loads = loads

                                    # 1. 呼叫 get_shear_details 獲取該工況下的詳細剪力數據
                                    _, table_data, demands_imperial, _, totals = get_shear_details(
                                        vcbgx_loads,
                                        plate_params,
                                        bolt_params,
                                        unit_system,
                                        bolt_coords_for_shear_details  # <--- 使用正確的純英制座標
                                    )

                                    # 2. 準備繪圖參數
                                    plot_bolt_coords_for_shear_plot = np.array(analysis_results['bolt_coords'])
                                    plot_plate_params_for_shear_plot = plate_params.copy()
                                    if unit_system == 'mks':
                                        plot_bolt_coords_for_shear_plot *= CONVERSION_FACTORS['IN_TO_CM']
                                        for key in ['B', 'N', 'outer_radius']:
                                            if key in plot_plate_params_for_shear_plot:
                                                plot_plate_params_for_shear_plot[key] *= CONVERSION_FACTORS['IN_TO_CM']

                                    plot_title = f"Vcbg-X 控制工況剪力分佈圖 (Combo #{vcbgx_combo_id})"
                                    shear_plot = analysis.generate_shear_vector_plot(
                                        plot_bolt_coords_for_shear_plot,
                                        demands_imperial,
                                        plot_plate_params_for_shear_plot,
                                        pedestal_params,
                                        column_params,
                                        bolt_params,
                                        critical_bolt_index=None,
                                        highlight_indices=anchor_indices,
                                        title=plot_title,
                                        unit_system=unit_system,
                                        vector_type='components',
                                        display_direction='X'
                                    )

                                    # 將所有數據注入 critical_vcbg_x_res
                                    critical_vcbg_x_res['shear_distribution_plot'] = shear_plot
                                    critical_vcbg_x_res['shear_table_data'] = table_data
                                    critical_vcbg_x_res['shear_table_totals'] = totals
                                    if 'plot_base64' in critical_vcbg_x_res:
                                        critical_vcbg_x_res['avc_plot_base64'] = critical_vcbg_x_res.pop('plot_base64')

                                    # 5. 將包含所有數據的字典存入 vcb_results
                                    vcb_results['group_x'] = {
                                        **critical_vcbg_x_res,
                                        'demand': demand_x,
                                        'capacity': capacity_x,
                                        'dc_ratio': dc_ratio_x,
                                        'result': 'PASS' if dc_ratio_x is not None and dc_ratio_x <= 1.0 else 'FAIL'
                                    }
                                else:
                                    vcb_results['group_x'] = {'result': 'N/A', 'dc_ratio': None,
                                                              'message': 'Vcbg 計算返回空列表，無法確定強度。'}
                            else:
                                vcb_results['group_x'] = {'result': 'N/A', 'dc_ratio': None, 'message': message_x}

                        # --- Y 方向群组檢核 (逻辑与 X 方向完全对称) ---
                        if has_shear_y:
                            rounding_decimals = 4
                            coords_for_grouping_y = np.where(np.abs(all_bolt_coords) < 1e-9, 0, all_bolt_coords)
                            unique_y_coords = sorted(list(set(
                                round(c[1], rounding_decimals) for c in coords_for_grouping_y
                            )))
                            message_y = "錨栓只有一排，无需群组檢核。"
                            needs_group_check_y = False

                            if len(unique_y_coords) > 1:
                                spacings_y = [unique_y_coords[i + 1] - unique_y_coords[i] for i in
                                              range(len(unique_y_coords) - 1)]
                                s_parallel_y_min = min(spacings_y)

                                outermost_y = unique_y_coords[-1] if VY_APPLIED >= 0 else unique_y_coords[0]

                                outer_row_bolts_y = [c for c in all_bolt_coords if
                                                     round(c[1], rounding_decimals) == outermost_y]
                                ca1_values_y = []
                                for c in outer_row_bolts_y:
                                    res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                                        c, (0, np.sign(VY_APPLIED) if VY_APPLIED != 0 else 0),
                                        pedestal_params, ANCHOR_PARAMS, bolt_params
                                    )
                                    if res and res.get('ca1') is not None:
                                        ca1_values_y.append(res['ca1'])

                                if ca1_values_y:
                                    ca1_group_y = min(ca1_values_y)
                                    if s_parallel_y_min <= 3 * ca1_group_y:
                                        needs_group_check_y = True
                                        message_y = f"存在錨栓排，且最小平行间距 s_y_min={s_parallel_y_min:.2f} in <= 3*ca1={3 * ca1_group_y:.2f} in，需进行群组檢核。"
                                    else:
                                        message_y = f"所有錨栓排的最小平行间距 s_y_min={s_parallel_y_min:.2f} in > 3*ca1={3 * ca1_group_y:.2f} in，无需群组檢核。"
                                else:
                                    message_y = "无法计算最外排的 ca1，跳过群组檢核。"

                            if needs_group_check_y:
                                direction_y = (0, np.sign(VY_APPLIED))
                                vcbg_combinations_y = anchor_shear_check.calculate_group_shear_breakout_Vcbg(
                                    direction_y,
                                    pedestal_params_for_checks,
                                    ANCHOR_PARAMS_FOR_CHECKS,
                                    bolt_params_for_checks,
                                    all_bolt_coords_for_checks,
                                    bolt_shear_demands,
                                    generate_plot=True  # <--- 新增此參數
                                )
                                if vcbg_combinations_y:
                                    critical_vcbg_y_res = min(vcbg_combinations_y, key=lambda x: x['phi_Vcbg'])
                                    capacity_y = critical_vcbg_y_res['phi_Vcbg']
                                    demand_y = abs(VY_APPLIED)
                                    dc_ratio_y = safe_dc_ratio(demand_y, capacity_y)

                                    # [核心新增] 整合報告書的描述文字
                                    anchor_indices = critical_vcbg_y_res.get('controlling_anchor_indices', [])
                                    if anchor_indices:
                                        anchors_text = ", ".join([f"#{i}" for i in anchor_indices])
                                        group_description = f"最不利狀態之錨栓群包含錨栓 {anchors_text}。"
                                    else:
                                        group_description = "由最不利錨栓群控制。"
                                    full_description = f"此檢核由載重组合 <b>#{combo_id}</b> 控制。{group_description}"
                                    critical_vcbg_y_res['full_description'] = full_description
                                    if 'message' in critical_vcbg_y_res:
                                        del critical_vcbg_y_res['message']

                                    # [核心新增] 為 critical_vcbg_y_res 準備附屬圖表
                                    _, table_data, demands_imperial, _, totals = get_shear_details(loads, plate_params,
                                                                                                   bolt_params,
                                                                                                   unit_system,
                                                                                                   all_bolt_coords_for_checks)

                                    plot_bolt_coords_for_shear_plot = np.array(analysis_results['bolt_coords'])
                                    plot_plate_params_for_shear_plot = plate_params.copy()
                                    if unit_system == 'mks':
                                        plot_bolt_coords_for_shear_plot *= CONVERSION_FACTORS['IN_TO_CM']
                                        for key in ['B', 'N', 'outer_radius']:
                                            if key in plot_plate_params_for_shear_plot:
                                                plot_plate_params_for_shear_plot[key] *= CONVERSION_FACTORS['IN_TO_CM']

                                    critical_bolt_for_plot_y = max(demands_imperial, key=lambda d: d['Vua_total'])
                                    critical_index_for_plot_y = critical_bolt_for_plot_y['index']

                                    plot_title = f"Vcbg-Y 控制工況剪力分佈圖 (Combo #{combo_id})"
                                    shear_plot = analysis.generate_shear_vector_plot(
                                        plot_bolt_coords_for_shear_plot,
                                        demands_imperial,
                                        plot_plate_params_for_shear_plot,
                                        pedestal_params,
                                        column_params,
                                        bolt_params,
                                        critical_bolt_index=None,
                                        title=plot_title,
                                        unit_system=unit_system,
                                        vector_type='components',
                                        display_direction='Y'
                                    )

                                    critical_vcbg_y_res['shear_distribution_plot'] = shear_plot
                                    critical_vcbg_y_res['shear_table_data'] = table_data
                                    critical_vcbg_y_res['shear_table_totals'] = totals
                                    if 'plot_base64' in critical_vcbg_y_res:
                                        critical_vcbg_y_res['avc_plot_base64'] = critical_vcbg_y_res.pop('plot_base64')

                                    vcb_results['group_y'] = {
                                        **critical_vcbg_y_res,
                                        'demand': demand_y,
                                        'capacity': capacity_y,
                                        'dc_ratio': dc_ratio_y,
                                        'result': 'PASS' if dc_ratio_y is not None and dc_ratio_y <= 1.0 else 'FAIL'
                                    }
                                else:
                                    vcb_results['group_y'] = {'result': 'N/A', 'dc_ratio': None, 'message': message_y}
                            else:
                                vcb_results['group_y'] = {'result': 'N/A', 'dc_ratio': None, 'message': message_y}

                        shear_checks['concrete_breakout_Vcb'] = vcb_results

                        # D3: Vcp & Vcpg
                        vcp_results = {}

                        # 在 Vcp/Vcpg 檢核前，我們先用 get_shear_details 計算一次當前工況的詳細剪力數據
                        # 這樣可以確保數據結構與其他檢核項一致
                        _, table_data_for_pryout, _, critical_bolt_info_for_pryout, totals_for_pryout = get_shear_details(
                            loads, plate_params, bolt_params, unit_system, all_bolt_coords_for_checks)

                        # 檢核最不利角落錨栓的 Vcp
                        coords_for_pryout_check = np.array(analysis_results_for_checks['bolt_coords'])
                        abs_coords = np.abs(coords_for_pryout_check)
                        corner_idx = np.argmax(np.sum(abs_coords, axis=1))
                        corner_coord_for_checks = tuple(coords_for_pryout_check[corner_idx])
                        vcp_res = anchor_shear_check.calculate_single_anchor_pryout_Vcp(
                            corner_coord_for_checks,
                            pedestal_params_for_checks,
                            ANCHOR_PARAMS_FOR_CHECKS,
                            bolt_params_for_checks
                        )
                        if vcp_res:
                            # [核心修正] 從 critical_bolt_info_for_pryout 獲取最大剪力
                            max_vua_total = critical_bolt_info_for_pryout.get('total_shear', 0)
                            phi_Vcp = vcp_res['phi_Vcp']
                            dc_ratio_vcp = max_vua_total / phi_Vcp if phi_Vcp > 0 else float('inf')

                            vcp_results['single'] = {
                                **vcp_res,
                                'demand': max_vua_total,
                                'dc_ratio': dc_ratio_vcp,
                                'result': 'PASS' if dc_ratio_vcp <= 1.0 else 'FAIL'
                            }
                            if table_data_for_pryout:
                                vcp_results['single']['shear_table_data'] = table_data_for_pryout
                                vcp_results['single']['critical_bolt_index'] = critical_bolt_info_for_pryout.get(
                                    'index')
                                vcp_results['single']['shear_table_totals'] = totals_for_pryout

                        print(vcp_results['single']['shear_table_data'])

                        # 檢核 Vcpg
                        vcpg_res = anchor_shear_check.calculate_group_pryout_Vcpg(
                            analysis_results_for_checks,
                            pedestal_params_for_checks,
                            ANCHOR_PARAMS_FOR_CHECKS
                        )
                        if vcpg_res:
                            phi_Vcpg = vcpg_res['phi_Vcpg']
                            # [核心修正] 分別計算 X 和 Y 方向的需求與 D/C Ratio
                            demand_x = abs(VX_APPLIED)
                            demand_y = abs(VY_APPLIED)
                            demand = np.sqrt(demand_x ** 2 + demand_y ** 2)
                            dc_ratio_vcpg = demand / phi_Vcpg if phi_Vcpg > 0 else float('inf')
                            vcp_results['group'] = {
                                **vcpg_res,
                                'demand': demand,
                                'dc_ratio': dc_ratio_vcpg,
                                'Vuxg': demand_x,
                                'Vuyg': demand_y,
                                'result': 'PASS' if dc_ratio_vcpg <= 1.0 else 'FAIL'
                            }
                            # [核心修正] 使用 get_shear_details 產生的 table_data
                            if table_data_for_pryout:
                                vcp_results['group']['shear_table_data'] = table_data_for_pryout
                                vcp_results['group']['shear_table_totals'] = totals_for_pryout

                        shear_checks['pryout_strength_Vcp'] = vcp_results
                        print()

                        current_combo_dcs['vsa'] = shear_checks.get('steel_strength_Vsa', {}).get('dc_ratio')
                        vcbx_dc = shear_checks.get('concrete_breakout_Vcb', {}).get('single_critical_x', {}).get(
                            'dc_ratio')
                        vcby_dc = shear_checks.get('concrete_breakout_Vcb', {}).get('single_critical_y', {}).get(
                            'dc_ratio')
                        current_combo_dcs['vcb'] = max(vcbx_dc or 0, vcby_dc or 0) if (vcbx_dc or vcby_dc) else None
                        current_combo_dcs['vcbg_x'] = shear_checks.get('concrete_breakout_Vcb', {}).get('group_x',
                                                                                                        {}).get(
                            'dc_ratio')
                        current_combo_dcs['vcbg_y'] = shear_checks.get('concrete_breakout_Vcb', {}).get('group_y',
                                                                                                        {}).get(
                            'dc_ratio')
                        current_combo_dcs['vcp'] = shear_checks.get('pryout_strength_Vcp', {}).get('single', {}).get(
                            'dc_ratio')
                        current_combo_dcs['vcpg'] = shear_checks.get('pryout_strength_Vcp', {}).get('group', {}).get(
                            'dc_ratio')
                        check_results_for_combo['anchor_shear_checks'] = shear_checks
                    else:
                        check_results_for_combo['anchor_shear_checks'] = {'result': 'N/A',
                                                                          'message': '無施加剪力或扭力'}
                        for key in ['vsa', 'vcb', 'vcbg_x', 'vcbg_y', 'vcp', 'vcpg']: current_combo_dcs[key] = None

                # ==========================================================
                # ==== START: 【核心新增】檢核 E: 拉剪互制作用 ====
                # ==========================================================
                # 只有在同时存在拉力和剪力檢核结果时，才需要檢核
                if 'anchor_tension_checks' in check_results_for_combo and 'anchor_shear_checks' in check_results_for_combo:

                    # 1. 找出当前组合下，所有拉力檢核项中的最大 D/C Ratio
                    max_ratio_N = 0.0
                    controlling_check_N = None
                    tension_checks = check_results_for_combo.get('anchor_tension_checks', {})
                    if tension_checks and isinstance(tension_checks, dict):
                        for check_name, result in tension_checks.items():
                            if isinstance(result, dict) and 'dc_ratio' in result and result['dc_ratio'] is not None:
                                if result['dc_ratio'] > max_ratio_N:
                                    max_ratio_N = result['dc_ratio']
                                    controlling_check_N = result
                            elif isinstance(result, dict):  # 处理嵌套的 Ncb, Nsb
                                for sub_key, sub_result in result.items():
                                    if isinstance(sub_result, dict) and 'dc_ratio' in sub_result and sub_result[
                                        'dc_ratio'] is not None:
                                        if sub_result['dc_ratio'] > max_ratio_N:
                                            max_ratio_N = sub_result['dc_ratio']
                                            controlling_check_N = sub_result

                    # 2. 找出当前组合下，所有剪力檢核项中的最大 D/C Ratio
                    max_ratio_V = 0.0
                    controlling_check_V = None
                    shear_checks = check_results_for_combo.get('anchor_shear_checks', {})
                    if shear_checks and isinstance(shear_checks, dict):
                        for check_name, result in shear_checks.items():
                            if isinstance(result, dict) and 'dc_ratio' in result and result['dc_ratio'] is not None:
                                if result['dc_ratio'] > max_ratio_V:
                                    max_ratio_V = result['dc_ratio']
                                    controlling_check_V = result
                            elif isinstance(result, dict):  # 处理嵌套的 Vcb, Vcp
                                for sub_key, sub_result in result.items():
                                    if isinstance(sub_result, dict) and 'dc_ratio' in sub_result and sub_result[
                                        'dc_ratio'] is not None:
                                        if sub_result['dc_ratio'] > max_ratio_V:
                                            max_ratio_V = sub_result['dc_ratio']
                                            controlling_check_V = sub_result

                    # 3. 根据规范进行判断
                    # ==========================================================
                    # ==== START: 【核心修正】检核 E: 拉剪互制作用 (僅考慮群組) ====
                    # ==========================================================
                    interaction_result = {}

                    # 只有在同時存在拉力和剪力檢核結果時，才需要檢核
                    if 'anchor_tension_checks' in check_results_for_combo and 'anchor_shear_checks' in check_results_for_combo:

                        # 1. 找出當前組合下，所有 "群組拉力" 檢核項中的最大 D/C Ratio
                        max_ratio_N_group = 0.0
                        controlling_check_N_group = "N/A"
                        tension_checks = check_results_for_combo.get('anchor_tension_checks', {})

                        tension_group_ratios = {
                            "Ncbg": tension_checks.get('concrete_breakout_Ncb', {}).get('group',
                                                                                        {}).get(
                                'dc_ratio'),
                            "Nsbg": tension_checks.get('side_face_blowout_Nsb', {}).get('group',
                                                                                        {}).get(
                                'dc_ratio'),
                            # Nag (黏結式錨栓) 未來可加入
                        }

                        for check_name, ratio in tension_group_ratios.items():
                            if ratio is not None and ratio > max_ratio_N_group:
                                max_ratio_N_group = ratio
                                controlling_check_N_group = check_name

                        # 2. 找出當前組合下，所有 "群組剪力" 檢核項中的最大 D/C Ratio
                        max_ratio_V_group = 0.0
                        controlling_check_V_group = "N/A"
                        shear_checks = check_results_for_combo.get('anchor_shear_checks', {})

                        shear_group_ratios = {
                            "Vcbg_x": shear_checks.get('concrete_breakout_Vcb', {}).get('group_x',
                                                                                        {}).get(
                                'dc_ratio'),
                            "Vcbg_y": shear_checks.get('concrete_breakout_Vcb', {}).get('group_y',
                                                                                        {}).get(
                                'dc_ratio'),
                            "Vcpg": shear_checks.get('pryout_strength_Vcp', {}).get('group', {}).get(
                                'dc_ratio'),
                        }

                        for check_name, ratio in shear_group_ratios.items():
                            if ratio is not None and ratio > max_ratio_V_group:
                                max_ratio_V_group = ratio
                                controlling_check_V_group = check_name

                        # 3. 根據規範進行判斷 (ACI 17.8)
                        # 假設為延性鋼材控制或混凝土破壞，線性公式適用
                        interaction_dc_ratio = 0.0

                        if max_ratio_N_group > 0.2 or max_ratio_V_group > 0.2:
                            # 只要任一 ratio 大于 0.2，就需要进行互制检核
                            interaction_dc_ratio = max_ratio_N_group + max_ratio_V_group
                            limit = 1.2  # 線性互制作用的上限
                            formula_type = 'linear'
                            message = f"因群組拉力比值 ({max_ratio_N_group:.3f}) 或群組剪力比值 ({max_ratio_V_group:.3f}) > 0.2，需進行互制檢核。"
                        else:
                            # 两者都 <= 0.2，无需进行互制检核
                            # 此時，整體的 D/C Ratio 就是兩者中的較大值
                            interaction_dc_ratio = max(max_ratio_N_group, max_ratio_V_group)
                            limit = 1.0  # 退化為單獨檢核的上限
                            formula_type = 'not_applicable'
                            message = f'因群組拉力比值 ({max_ratio_N_group:.3f}) 及群組剪力比值 ({max_ratio_V_group:.3f}) 均 ≤ 0.2，無需互制檢核。'

                        interaction_result = {
                            'ratio_N': max_ratio_N_group,
                            'controlling_check_N': controlling_check_N_group,
                            'ratio_V': max_ratio_V_group,
                            'controlling_check_V': controlling_check_V_group,
                            'dc_ratio': interaction_dc_ratio,
                            'result': 'PASS' if interaction_dc_ratio <= limit else 'FAIL',
                            'formula_type': formula_type,
                            'limit': limit,
                            'message': message,
                        }
                    else:
                        interaction_result = {'result': 'N/A',
                                              'message': '缺少拉力或剪力檢核結果，無法進行互制檢核。'}

                    current_combo_dcs['interaction'] = interaction_result.get('dc_ratio')
                    check_results_for_combo['anchor_interaction'] = interaction_result
                    # ==========================================================
                    # ==== END: 检核 E: 拉剪互制作用 ====
                    # ==========================================================

                # 更新包络结果
                update_envelope('concrete_bearing', check_results_for_combo.get('concrete_bearing_check'), combo_id,
                                check_results_for_combo)
                update_envelope('plate_bending', check_results_for_combo.get('plate_bending_check'), combo_id,
                                check_results_for_combo)

                # 拉力檢核
                tension_checks = check_results_for_combo.get('anchor_tension_checks', {})
                if tension_checks and isinstance(tension_checks, dict):
                    # [核心修正] 第四個參數應為 check_results_for_combo
                    update_envelope('anchor_nsa', tension_checks.get('steel_strength_Nsa'), combo_id,
                                    check_results_for_combo)
                    update_envelope('anchor_npn', tension_checks.get('pullout_strength_Npn'), combo_id,
                                    check_results_for_combo)
                    if 'concrete_breakout_Ncb' in tension_checks:
                        update_envelope('anchor_ncb_single', tension_checks['concrete_breakout_Ncb'].get('single', ),
                                        combo_id, check_results_for_combo)
                        update_envelope('anchor_ncbg_group', tension_checks['concrete_breakout_Ncb'].get('group'),
                                        combo_id, check_results_for_combo)
                    if 'side_face_blowout_Nsb' in tension_checks:
                        update_envelope('anchor_nsb_single',
                                        tension_checks.get('side_face_blowout_Nsb', {}).get('single'), combo_id,
                                        check_results_for_combo)
                        update_envelope('anchor_nsbg_group',
                                        tension_checks.get('side_face_blowout_Nsb', {}).get('group'), combo_id,
                                        check_results_for_combo)

                # 剪力檢核
                shear_checks = check_results_for_combo.get('anchor_shear_checks', {})
                if shear_checks and isinstance(shear_checks, dict):
                    update_envelope('anchor_vsa', shear_checks.get('steel_strength_Vsa'), combo_id,
                                    check_results_for_combo)
                    if 'concrete_breakout_Vcb' in shear_checks:
                        update_envelope('anchor_vcb_single_x',
                                        shear_checks['concrete_breakout_Vcb'].get('single_critical_x'), combo_id,
                                        check_results_for_combo)
                        update_envelope('anchor_vcb_single_y',
                                        shear_checks['concrete_breakout_Vcb'].get('single_critical_y'), combo_id,
                                        check_results_for_combo)
                        update_envelope('anchor_vcbg_group_x', shear_checks['concrete_breakout_Vcb'].get('group_x'),
                                        combo_id, check_results_for_combo)
                        update_envelope('anchor_vcbg_group_y', shear_checks['concrete_breakout_Vcb'].get('group_y'),
                                        combo_id, check_results_for_combo)
                    if 'pryout_strength_Vcp' in shear_checks:
                        update_envelope('anchor_vcp_single', shear_checks['pryout_strength_Vcp'].get('single'),
                                        combo_id, check_results_for_combo)

                        update_envelope('anchor_vcpg_group', shear_checks['pryout_strength_Vcp'].get('group'),
                                        combo_id, check_results_for_combo)

                update_envelope('anchor_interaction', check_results_for_combo.get('anchor_interaction'), combo_id,
                                check_results_for_combo)

                all_combos_dc_ratios.append(current_combo_dcs)

                del analysis_results
                del check_results_for_combo
                gc.collect()

            envelope_results['has_any_tension'] = has_any_tension
            envelope_results['has_any_shear'] = has_any_shear
            # ==========================================================
            # ==== START: 【核心修正】将 STAGE 2 和最终 return 移到循环外部 ====
            # ==========================================================
            # --- 4. 第二階段：找出最不利的荷载组合，并为其生成图片 ---
            if envelope_results:
                most_critical_combo_id = -1
                highest_ratio = -1.0
                for check_name, data in envelope_results.items():
                    if isinstance(data, dict) and 'dc_ratio' in data and data.get('dc_ratio') is not None:
                        if data['dc_ratio'] > highest_ratio:
                            highest_ratio = data['dc_ratio']
                            most_critical_combo_id = data['combo_id']

                if most_critical_combo_id != -1:
                    print(
                        f"\n\n=====>>>>> STAGE 2: GENERATING PLOT FOR CRITICAL COMBO #{most_critical_combo_id} <<<<<=====")
                    critical_loads = next((l for l in loads_combinations if l.get('id') == most_critical_combo_id),
                                          None)
                    if critical_loads:
                        try:
                            # 重新运行一次分析，这次只为了生成图片
                            critical_analysis_results = analysis.perform_analysis(
                                plate_shape=plate_params.get('shape'),
                                P_applied=critical_loads.get('p_applied'),
                                Mx_applied=critical_loads.get('mx_applied'),
                                My_applied=critical_loads.get('my_applied'),
                                Es=materials.get('es_ksi'), Ec=materials.get('ec_ksi'),
                                bolt_layout_mode=bolt_params.get('layout_mode'),
                                plate_params=plate_params, bolt_params=bolt_params,
                                generate_plot_data=True,
                                unit_system=unit_system
                            )

                            # 将图片数据和组合ID附加到最终结果中
                            if critical_analysis_results and 'plot_base64' in critical_analysis_results:
                                envelope_results['critical_plot_base64'] = critical_analysis_results.get('plot_base64')
                                envelope_results['most_critical_combo_id'] = most_critical_combo_id
                        except Exception as plot_error:
                            print(f"      - ERROR: Failed to generate plot for critical combo. Reason: {plot_error}")
                            # 即使图片生成失败，我们也要确保其他结果能被返回
                            envelope_results['critical_plot_base64'] = None
                            envelope_results['most_critical_combo_id'] = most_critical_combo_id

            # --- 5. 迴圈結束後，回傳 envelope_results ---
            envelope_results['all_combos_summaries'] = all_combos_summaries
            print("\n=====>>>>> ENVELOPE RESULTS <<<<<=====")

            # --- 4. 第二階段：最终包络檢核 (Final Envelope Checks) ---
            print("\n\n=====>>>>> STAGE 2: FINAL ENVELOPE CHECKS & PLOT GENERATION <<<<<=====")

            print("\n\n=====>>>>> STAGE 3: GENERATING PLOTS FOR SPECIFIC CHECKS <<<<<=====")
            # [核心新增] 為 Ncb 檢核生成專屬附圖
            if 'anchor_ncb_single' in envelope_results:
                ncb_data = envelope_results['anchor_ncb_single']
                if ncb_data and ncb_data.get('details', {}).get('result') != 'N/A':
                    ncb_combo_id = ncb_data.get('combo_id')
                    full_combo_results = ncb_data.get('full_combo_results', {})
                    analysis_summary = full_combo_results.get('analysis_summary', {})
                    all_bolts_imperial = analysis_summary.get('bolt_coords_in')
                    bolt_forces_imperial = analysis_summary.get('bolt_forces_kips')

                    if ncb_combo_id and all_bolts_imperial and bolt_forces_imperial:
                        # 找出最不利錨栓的座標
                        max_force_imperial = max(bolt_forces_imperial)
                        max_tension_idx = bolt_forces_imperial.index(max_force_imperial)
                        critical_anchor_coord_imperial = tuple(all_bolts_imperial[max_tension_idx])

                        # --- 重新準備檢核所需的參數 (包含單位轉換) ---
                        ANCHOR_PARAMS_FOR_NCB_PLOT = ANCHOR_PARAMS.copy()
                        pedestal_params_for_ncb_plot = pedestal_params.copy()
                        all_bolts_for_ncb_plot = np.array(all_bolts_imperial)
                        critical_anchor_for_ncb_plot = critical_anchor_coord_imperial

                        if unit_system == 'mks':
                            # 轉換長度和應力
                            if ANCHOR_PARAMS_FOR_NCB_PLOT.get('h_ef') is not None:
                                ANCHOR_PARAMS_FOR_NCB_PLOT['h_ef'] *= CONVERSION_FACTORS['IN_TO_CM']
                            if ANCHOR_PARAMS_FOR_NCB_PLOT.get('fc_psi') is not None:
                                ANCHOR_PARAMS_FOR_NCB_PLOT['fc_psi'] *= CONVERSION_FACTORS['PSI_TO_KGF_CM2']
                            for key in ['N', 'B', 'D', 'h']:
                                if pedestal_params_for_ncb_plot.get(key) is not None:
                                    pedestal_params_for_ncb_plot[key] *= CONVERSION_FACTORS['IN_TO_CM']
                            all_bolts_for_ncb_plot = all_bolts_for_ncb_plot * CONVERSION_FACTORS['IN_TO_CM']
                            critical_anchor_for_ncb_plot = tuple(
                                np.array(critical_anchor_coord_imperial) * CONVERSION_FACTORS['IN_TO_CM'])

                        print(f"      - Generating ANc plot for Ncb Check (Combo #{ncb_combo_id})")

                        # 重新呼叫計算函式，這次只為了生成圖片
                        ncb_res_with_plot = anchor_tension_check.calculate_single_anchor_breakout_Ncb(
                            anchor_coord=critical_anchor_for_ncb_plot,
                            pedestal_params=pedestal_params_for_ncb_plot,
                            anchor_params=ANCHOR_PARAMS_FOR_NCB_PLOT,
                            all_bolt_coords=all_bolts_for_ncb_plot.tolist(),
                            generate_plot=True  # <--- 關鍵：要求生成圖表
                        )

                        if ncb_res_with_plot and ncb_res_with_plot.get('plot_base64'):
                            # [核心修改] 使用 'anc_plot_base64' 這個獨特的鍵來儲存 ANc 圖，避免與應力圖衝突
                            envelope_results['anchor_ncb_single']['details']['anc_plot_base64'] = ncb_res_with_plot[
                                'plot_base64']

            # ==========================================================
            # ==== START: 【核心修正】为 "混凝土承压" 檢核生成专属附图 ====
            # ==========================================================
            if 'concrete_bearing' in envelope_results:
                bearing_data = envelope_results['concrete_bearing']
                if bearing_data and bearing_data.get('details', {}).get('result') != 'N/A':
                    bearing_combo_id = bearing_data['combo_id']
                    bearing_loads = next((l for l in loads_combinations if l.get('id') == bearing_combo_id), None)
                    if bearing_loads:
                        print(f"      - Generating plot for Concrete Bearing Check (Combo #{bearing_combo_id})")
                        bearing_analysis_results = analysis.perform_analysis(
                            plate_shape=plate_params.get('shape'),
                            P_applied=bearing_loads.get('p_applied'),
                            Mx_applied=bearing_loads.get('mx_applied'),
                            My_applied=bearing_loads.get('my_applied'),
                            Es=materials.get('es_ksi'), Ec=materials.get('ec_ksi'),
                            bolt_layout_mode=bolt_params.get('layout_mode'),
                            plate_params=plate_params, bolt_params=bolt_params,
                            generate_plot_data=True,
                            unit_system=unit_system
                        )
                        if bearing_analysis_results and bearing_analysis_results.get('plot_base64'):
                            envelope_results['concrete_bearing']['details'][
                                'plot_base64'] = bearing_analysis_results.get('plot_base64')

            # ==========================================================
            # ==== START: 【核心修正】对 Vcpg 使用全局最大总剪力进行最终檢核 ====
            # ==========================================================
            if 'anchor_vcpg_group' in envelope_results and max_total_shear_info['value'] > 0:
                vcpg_details = envelope_results['anchor_vcpg_group']['details']
                capacity = vcpg_details['phi_Vcpg']
                demand = max_total_shear_info['value']

                dc_ratio = safe_dc_ratio(demand, capacity)
                result = 'PASS' if dc_ratio is not None and dc_ratio <= 1.0 else 'FAIL'

                # 更新 envelope_results 中的 Vcpg 条目
                envelope_results['anchor_vcpg_group']['details']['demand'] = demand
                envelope_results['anchor_vcpg_group']['details']['dc_ratio'] = dc_ratio
                envelope_results['anchor_vcpg_group']['details']['result'] = result

                # 将 Vux 和 Vuy 加入 details 字典，以便模板访问
                envelope_results['anchor_vcpg_group']['details']['demand_vux'] = max_total_shear_info['vux']
                envelope_results['anchor_vcpg_group']['details']['demand_vuy'] = max_total_shear_info['vuy']

                # 更新 message，让报告更清晰
                original_combo_id = envelope_results['anchor_vcpg_group']['combo_id']
                envelope_results['anchor_vcpg_group']['details']['message'] = (
                    f"容量由 Combo #{original_combo_id} 控制；"
                    f"需求採用 Combo #{max_total_shear_info['combo_id']} 產生的最大總剪力。"
                )
                # 更新顶层的 dc_ratio 和 combo_id 以反映需求来源
                envelope_results['anchor_vcpg_group']['dc_ratio'] = dc_ratio
                envelope_results['anchor_vcpg_group']['combo_id'] = max_total_shear_info['combo_id']

            # ====================================================================
            # ==== START: 【核心新增】为弯曲檢核生成专属图片 ====
            # ====================================================================
            if 'plate_bending' in envelope_results:
                bending_data = envelope_results['plate_bending']
                bending_combo_id = bending_data['combo_id']
                bending_loads = next((l for l in loads_combinations if l.get('id') == bending_combo_id), None)

                if bending_loads:
                    print(f"      - Re-running Bending Check for Plot Generation (Combo #{bending_combo_id})")
                    # 重新运行一次分析，以获取该组合的 analysis_results
                    bending_analysis_results = analysis.perform_analysis(
                        plate_shape=plate_params.get('shape'),
                        P_applied=bending_loads.get('p_applied'),
                        Mx_applied=bending_loads.get('mx_applied'),
                        My_applied=bending_loads.get('my_applied'),
                        Es=materials.get('es_ksi'),
                        Ec=materials.get('ec_ksi'),
                        bolt_layout_mode=bolt_params.get('layout_mode'),
                        plate_params=plate_params,
                        bolt_params=bolt_params,
                        show_plot=False,
                        generate_plot_data=False
                    )

                    if bending_analysis_results:
                        # 2. 准备传递给弯曲檢核函式的资料 (这部分逻辑是正确的)
                        simplified_grid_data = None
                        if bending_analysis_results.get('grid_pressures') is not None:
                            grid_data = bending_analysis_results.get('grid_data', {})
                            cell_area_val = grid_data.get('ca')
                            if cell_area_val is None and 'xv' in grid_data:
                                xv = np.array(grid_data['xv'])
                                cell_area_val = (xv[0, 1] - xv[0, 0]) ** 2
                            simplified_grid_data = {
                                'xv': grid_data.get('xv'), 'yv': grid_data.get('yv'),
                                'pressures': bending_analysis_results['grid_pressures'],
                                'cell_area': cell_area_val
                            }

                        analysis_results_for_tp_check = {
                            'grid_data': simplified_grid_data,
                            'bolt_coords': bending_analysis_results['bolt_coords'],
                            'bolt_forces': bending_analysis_results['bolt_forces'],
                            'plate_B': bending_analysis_results['plate_B'],
                            'plate_N': bending_analysis_results['plate_N'],
                            'plate_params': plate_params  # [核心新增] 傳遞完整的 plate_params
                        }

                        # 重新运行一次弯曲檢核，这次只为了生成图片
                        final_tp_res = tp_check.perform_plate_bending_check(
                            analysis_results=bending_analysis_results,  # 使用對應工況的分析結果
                            column_params=column_params,
                            materials=materials,
                            plate_params=plate_params,
                            plate_fy_ksi=PLATE_FY_KSI,
                            plate_tp_in=PLATE_TP_IN,
                            generate_plot=True,
                            unit_system=unit_system
                        )

                        # 将生成的图片附加到最终结果中
                        if final_tp_res:
                            envelope_results['plate_bending']['details'] = final_tp_res

            # ====================================================================
            # ==== START: 【核心新增】第六阶段：为特定檢核项准备附图和表格 ====
            # ====================================================================
            print("\n\n=====>>>>> STAGE 4: PREPARING DATA FOR REPORT <<<<<=====")

            # 为 Vcp 單根檢核准备剪力分布图和表格
            if 'anchor_vcp_single' in envelope_results:
                vcp_data = envelope_results['anchor_vcp_single']
                vcp_combo_id = vcp_data['combo_id']
                vcp_loads = next((l for l in loads_combinations if l.get('id') == vcp_combo_id), None)

                if vcp_loads:
                    # 重新计算该工况下的详细剪力分量
                    VX, VY, TZ = vcp_loads.get('vx_applied', 0), vcp_loads.get('vy_applied', 0), vcp_loads.get(
                        'tz_applied', 0)
                    temp_analysis = analysis.perform_analysis(plate_shape=plate_params.get('shape'), P_applied=0,
                                                              Mx_applied=0, My_applied=0, Es=1, Ec=1,
                                                              bolt_layout_mode=bolt_params.get('layout_mode'),
                                                              plate_params=plate_params, bolt_params=bolt_params)

                    if temp_analysis:
                        num_bolts = temp_analysis['num_bolts']
                        bolt_coords = np.array(temp_analysis['bolt_coords'])
                        J = float(np.sum(bolt_coords[:, 0] ** 2 + bolt_coords[:, 1] ** 2))

                        shear_table_data = []
                        shear_demands_for_plot = []

                        for i in range(num_bolts):
                            xi, yi = bolt_coords[i, 0], bolt_coords[i, 1]
                            v_direct_x = VX / num_bolts if num_bolts > 0 else 0
                            v_direct_y = VY / num_bolts if num_bolts > 0 else 0
                            v_torsion_x = -TZ * yi / J if J > 0 else 0
                            v_torsion_y = TZ * xi / J if J > 0 else 0

                            v_total_x = v_direct_x + v_torsion_x
                            v_total_y = v_direct_y + v_torsion_y
                            v_total_mag = np.sqrt(v_total_x ** 2 + v_total_y ** 2)  # <--- 補上計算

                            shear_demands_for_plot.append({
                                'index': i,
                                'coord': [xi, yi],
                                'Vua_x': v_total_x,
                                'Vua_y': v_total_y,
                                'Vua_total': v_total_mag
                            })

                            shear_table_data.append({
                                'index': i,
                                'coord_x': xi, 'coord_y': yi,
                                'v_direct_x': v_direct_x, 'v_direct_y': v_direct_y,
                                'v_torsion_x': v_torsion_x, 'v_torsion_y': v_torsion_y,
                                'v_total_x': v_direct_x + v_torsion_x,
                                'v_total_y': v_direct_y + v_torsion_y,
                                'v_total_mag': v_total_mag
                            })

                        # 生成剪力向量图
                        plot_title = f"錨栓剪力分布图 (Load Combo #{vcp_combo_id})"
                        vcp_plot_base64 = analysis.generate_shear_vector_plot(
                            bolt_coords,
                            shear_demands_for_plot,
                            plate_params,
                            pedestal_params,
                            column_params,
                            bolt_params,
                            critical_bolt_index=critical_bolt_info_for_pryout.get('index'),  # <-- 正確
                            title=plot_title
                        )

                        # 将图和表格数据附加到 envelope_results 中
                        envelope_results['anchor_vcp_single']['details']['shear_distribution_plot'] = vcp_plot_base64
                        envelope_results['anchor_vcp_single']['details']['shear_table_data'] = shear_table_data

            # --- 6. 迴圈結束後，回傳 envelope_results ---
            envelope_results['all_combos_dc_ratios'] = all_combos_dc_ratios
            envelope_results['all_combos_summaries'] = all_combos_summaries

            # ====================================================================
            # ==== START: 【核心新增】第七階段：為報告書準備最不利情況的詳細數據 ====
            # ====================================================================
            print("\n\n=====>>>>> STAGE 5: PREPARING DETAILED DATA FOR REPORT <<<<<=====")
            # --- 7a. 為所有 "最大拉力控制" 的檢核項 (Nsa, Npn) 準備共用的圖表數據 ---
            tension_check_keys = ['anchor_nsa', 'anchor_npn', 'anchor_ncb_single', 'anchor_ncbg_group',
                                  'anchor_nsb_single', 'anchor_nsbg_group']
            for key in tension_check_keys:
                if key in envelope_results:
                    check_data = envelope_results[key]
                    combo_id = check_data.get('combo_id')

                    if combo_id:
                        # 找到對應的荷載組合
                        loads_for_plot = next((l for l in loads_combinations if l.get('id') == combo_id), None)
                        if loads_for_plot:
                            print(f"      - Generating plot and table for '{key}' (Combo #{combo_id})")

                            # 重新運行一次分析，要求生成圖片
                            plot_analysis_results = analysis.perform_analysis(
                                plate_shape=plate_params.get('shape'),
                                P_applied=loads_for_plot.get('p_applied'),
                                Mx_applied=loads_for_plot.get('mx_applied'),
                                My_applied=loads_for_plot.get('my_applied'),
                                Es=materials.get('es_ksi'), Ec=materials.get('ec_ksi'),
                                bolt_layout_mode=bolt_params.get('layout_mode'),
                                plate_params=plate_params, bolt_params=bolt_params,
                                generate_plot_data=True,
                                unit_system=unit_system  # <--- 傳遞單位制
                            )

                            if plot_analysis_results:
                                # 準備表格數據
                                forces = np.array(plot_analysis_results['bolt_forces'])
                                coords = np.array(plot_analysis_results['bolt_coords'])
                                tension_table_data = []
                                total_tension = 0.0

                                for i in range(len(forces)):
                                    tension_force = forces[i] if forces[i] > 1e-9 else 0.0
                                    tension_table_data.append({
                                        'index': i,
                                        'coord_x': coords[i, 0],
                                        'coord_y': coords[i, 1],
                                        'tension_force': tension_force
                                    })
                                    total_tension += tension_force

                                # 將圖、表、總和數據全部存入對應的 details 字典中
                                envelope_results[key]['details']['plot_base64'] = plot_analysis_results.get(
                                    'plot_base64')
                                envelope_results[key]['details']['tension_table_data'] = tension_table_data
                                envelope_results[key]['details']['total_tension'] = total_tension

            # --- 7b. 準備最不利 "剪力" 工況的數據 (圖+表) ---
            shear_check_keys = ['anchor_vsa', 'anchor_vcb_single_x', 'anchor_vcb_single_y',
                                'anchor_vcbg_group_x', 'anchor_vcbg_group_y', 'anchor_vcp_single',
                                'anchor_vcpg_group']
            critical_shear_combo_id = -1
            max_shear_ratio = -1.0
            controlling_shear_check_key = None

            for key in shear_check_keys:
                check_item = envelope_results.get(key, {})
                if check_item and check_item.get('dc_ratio') is not None and check_item.get(
                        'dc_ratio') > max_shear_ratio:
                    max_shear_ratio = check_item['dc_ratio']
                    critical_shear_combo_id = check_item['combo_id']
                    controlling_shear_check_key = key

            # 輔助函式，避免程式碼重複

            # --- 7b-1. [核心重構] 為 anchor_vsa 準備專屬的圖表數據 ---
            if 'anchor_vsa' in envelope_results:
                vsa_data = envelope_results['anchor_vsa']
                vsa_combo_id = vsa_data['combo_id']
                vsa_loads = next((l for l in loads_combinations if l.get('id') == vsa_combo_id), None)

                if vsa_loads:
                    bolt_coords_imperial, table_data, demands_imperial, critical_bolt_info, totals = (
                        get_shear_details(vsa_loads, plate_params, bolt_params, unit_system,
                                          bolt_coords_for_shear_details)  # <-- 使用正確的座標變數
                    )

                    if bolt_coords_imperial is not None:
                        # [核心修正] 傳遞給繪圖函式的 plate_params 永遠是英制
                        plot_base64 = analysis.generate_shear_vector_plot(
                            bolt_coords_imperial,  # <-- 使用正確的變數
                            demands_imperial,  # <-- 使用正確的變數
                            plate_params,
                            pedestal_params,
                            column_params,
                            bolt_params,
                            critical_bolt_index=critical_bolt_info.get('index'),  # <-- 補上
                            title=plot_title,
                            unit_system=unit_system
                            # vector_type 預設為 'components'，符合需求
                        )

                        # 將圖、表和最不利錨栓資訊注入 'anchor_vsa' 的 details
                        envelope_results['anchor_vsa']['details']['shear_distribution_plot'] = plot_base64
                        envelope_results['anchor_vsa']['details']['shear_table_data'] = table_data
                        envelope_results['anchor_vsa']['details']['shear_table_totals'] = totals
                        envelope_results['anchor_vsa']['details']['critical_bolt_index'] = critical_bolt_info['index']

            # --- 7b-2. 為整體最不利剪力工況準備數據 (如果與 Vsa 不同) ---
            if critical_shear_combo_id != -1:
                shear_loads = next((l for l in loads_combinations if l.get('id') == critical_shear_combo_id), None)
                if shear_loads:
                    bolt_coords_imperial, table_data, demands_imperial, critical_bolt_info, totals = get_shear_details(
                        shear_loads,
                        plate_params,
                        bolt_params,
                        unit_system,
                        bolt_coords_for_shear_details  # <-- 使用正確的座標變數
                    )
                    if bolt_coords is not None:
                        # plot_title = f"最不利總剪力分佈圖 (Combo #{critical_shear_combo_id})"
                        # 為 6.8 節生成 'resultant' 風格的圖
                        plot_base64_resultant = analysis.generate_shear_vector_plot(
                            bolt_coords_imperial,
                            demands_imperial,
                            plate_params,
                            pedestal_params,
                            column_params,
                            bolt_params,
                            critical_bolt_index=critical_bolt_info.get('index'),  # <-- 補上
                            title=plot_title,
                            vector_type='resultant',
                            unit_system=unit_system  # <-- 補上 unit_system
                        )
                        # [核心修正] 無論如何，都將數據賦值到頂層變數
                        envelope_results['critical_shear_plot_base64'] = plot_base64_resultant
                        envelope_results['critical_shear_table_data'] = table_data
                        envelope_results['critical_shear_table_data'] = totals
                        envelope_results['critical_shear_combo_id'] = critical_shear_combo_id

                        # 如果 Vsa 恰好是控制項，也將數據注入其中
                        if controlling_shear_check_key == 'anchor_vsa' and 'anchor_vsa' in envelope_results:
                            envelope_results['anchor_vsa']['details']['shear_distribution_plot'] = plot_base64_resultant
                            envelope_results['anchor_vsa']['details']['shear_table_data'] = table_data
                            envelope_results['anchor_vsa']['details']['shear_table_totals'] = totals

            # --- 7b-3. 為 Vcb/Vcbg 各自的控制工況，生成 "Components" 風格的圖表 ---
            shear_component_plot_keys = ['anchor_vcb_single_x', 'anchor_vcb_single_y',
                                         'anchor_vcbg_group_x', 'anchor_vcbg_group_y']

            for key in shear_component_plot_keys:
                check_data = envelope_results.get(key)
                if check_data and check_data.get('details'):
                    combo_id = check_data.get('combo_id')
                    loads = find_loads_by_id(loads_combinations, combo_id)

                    if loads:
                        bolt_coords_imperial, table_data, demands_imperial, _, totals = get_shear_details(
                            loads,
                            plate_params,
                            bolt_params,
                            unit_system,
                            bolt_coords_for_shear_details
                        )

                        if bolt_coords_imperial is not None:
                            plot_title = f"{key} 控制工況剪力分佈圖 (Combo #{combo_id})"

                            # ===== 【核心修正】區分單根和群組的索引提取邏輯 =====
                            critical_idx = None
                            highlight_idxs = None

                            if 'group' in key:
                                # 這是群組檢核 (Vcbg)，提取 'controlling_anchor_indices'
                                highlight_idxs = check_data.get('details', {}).get('controlling_anchor_indices')
                                critical_idx = None
                            else:
                                # 這是單根檢核 (Vcb)，提取 'anchor_index'
                                critical_idx = check_data.get('details', {}).get('anchor_index')
                                highlight_idxs = None

                            # 3. 傳入所有必要的參數
                            plot_base64_components = analysis.generate_shear_vector_plot(
                                bolt_coords_imperial,
                                demands_imperial,
                                plate_params,
                                pedestal_params,
                                column_params,
                                bolt_params,
                                critical_bolt_index=critical_idx,      # <-- 傳入單根索引
                                highlight_indices=highlight_idxs,  # <-- 傳入群組索引列表
                                title=plot_title,
                                vector_type='components',
                                unit_system=unit_system,
                                show_background_geometry=False
                            )

                            envelope_results[key]['details']['shear_distribution_plot'] = plot_base64_components
                            envelope_results[key]['details']['shear_table_data'] = table_data
                            envelope_results[key]['details']['shear_table_totals'] = totals

            # return JsonResponse({'status': 'success', 'results': envelope_results}, encoder=NumpyEncoder)

            # ==========================================================
            # ==== START: 【核心新增】權限檢查邏輯 ====
            # ==========================================================
            can_generate_report = False
            user = request.user

            print(f"\n--- 開始為使用者 '{user.username}' 檢查報告書權限 ---")

            if user.is_superuser:
                can_generate_report = True
                print("    - 判斷: 使用者是 Superuser，授予權限。")
            else:
                try:
                    profile = user.profile
                    purchased_modules = profile.purchased_modules

                    # 【核心修正】統一使用 'base-plate-and-anchor' 作為檢查的 ID
                    product_id_to_check = 'base-plate-and-anchor'

                    print(f"    - 1. 從資料庫讀取的 purchased_modules 內容: {purchased_modules}")
                    print(f"    - 2. 檢查的商品 ID: '{product_id_to_check}'")

                    if isinstance(purchased_modules, dict) and product_id_to_check in purchased_modules:
                        print(f"    - 3. 判斷: '{product_id_to_check}' 存在於購買記錄中。")

                        module_data = purchased_modules[product_id_to_check]
                        expiration_date_str = module_data.get('expiration_date')

                        print(f"    - 4. 讀取到的到期日 (字串): {expiration_date_str}")

                        if expiration_date_str:
                            try:
                                expiration_date = datetime.fromisoformat(expiration_date_str.replace('Z', '+00:00'))
                                now = timezone.now()

                                print(f"    - 5. 解析後的到期日: {expiration_date}")
                                print(f"    - 6. 當前伺服器時間: {now}")

                                if expiration_date > now:
                                    can_generate_report = True
                                    print("    - 7. 判斷: 到期日 > 當前時間。授予權限。")
                                else:
                                    print("    - 7. 判斷: 到期日 <= 當前時間。權限已過期。")

                            except (ValueError, TypeError) as e:
                                print(f"    - 錯誤: 無法解析日期字串 '{expiration_date_str}'。錯誤詳情: {e}")
                        else:
                            print("    - 錯誤: 購買記錄中缺少 'expiration_date' 鍵。")
                    else:
                        print(f"    - 3. 判斷: '{product_id_to_check}' 不存在於購買記錄中。")

                except (Profile.DoesNotExist, AttributeError):
                    print("    - 錯誤: 找不到使用者的 Profile。")
                    can_generate_report = False

            print(f"--- 最終權限檢查結果: {can_generate_report} ---\n")

            final_results_dict = {
                'status': 'success',
                'results': envelope_results,
                'can_generate_report': can_generate_report  # 權限檢查邏輯保持不變
            }

            results_json_str = json.dumps(final_results_dict, cls=NumpyEncoder)
            request.session['latest_bp_anchor_results'] = results_json_str

            return HttpResponse(results_json_str, content_type='application/json')

        except Exception as e:
            import traceback
            return JsonResponse({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def generate_report_view(request):
    """
    【全新優化完整版 v2.0 - 無任何省略】
    此 view 負責從 session 讀取純數據結果，然後按需重新計算並生成報告書所需的所有圖表，
    最後將包含圖表的完整 context 渲染到報告書模板。
    """
    try:
        # 1. 從 session 讀取核心數據
        inputs_json_str = request.session.get('latest_bp_anchor_inputs', '{}')
        results_json_str = request.session.get('latest_bp_anchor_results', '{}')
        inputs_data = json.loads(inputs_json_str)
        envelope_results = json.loads(results_json_str).get('results', {})

        if not inputs_data or not envelope_results:
            return HttpResponse("計算資料已過期或不存在，請返回計算頁面重新分析。", status=400)

        # 2. 提取常用參數
        unit_system = inputs_data.get('unit_system', 'imperial')
        plate_params = inputs_data.get('plate_params', {})
        pedestal_params = inputs_data.get('pedestal_params', {})
        bolt_params = inputs_data.get('bolt_params', {})
        column_params = inputs_data.get('column_params', {})
        anchor_check_params = inputs_data.get('anchor_check_params', {})
        materials = inputs_data.get('materials', {})
        loads_combinations = inputs_data.get('loads_combinations', [])

        # 準備 ANCHOR_PARAMS (與 bp_anchor_calculate_api 中的版本保持一致)
        ANCHOR_PARAMS = {
            'unit_system': unit_system,
            'anchor_type': anchor_check_params.get('anchor_install_type'),
            'anchor_structural_type': anchor_check_params.get('anchor_structural_type'),
            'Abrg': bolt_params.get('Abrg_in2'),
            'is_headed': anchor_check_params.get('anchor_structural_type') == 'headed',
            'hook_type': 'J' if anchor_check_params.get('anchor_structural_type') == 'hooked' else None,
            'longitudinal_rebar_size': pedestal_params.get('longitudinal_rebar_size'),
            'bolt_layout_mode': bolt_params.get('layout_mode'),
            'phi_cb': 0.70, 'phi_st': 0.75, 'phi_pn': 0.70, 'phi_sfb': 0.70, 'phi_sv': 0.65, 'phi_cv': 0.70,
            'h_ef': anchor_check_params.get('h_ef'),
            'is_cracked': anchor_check_params.get('is_cracked'),
            'has_supplementary_reinf': anchor_check_params.get('has_supplementary_reinf'),
            'supplementary_rebar_size': anchor_check_params.get('supplementary_rebar_size'),
            'supplementary_rebar_spacing': anchor_check_params.get('supplementary_rebar_spacing'),
            'reinf_condition_shear': anchor_check_params.get('reinf_condition_shear'),
            'reinf_condition_tension': anchor_check_params.get('reinf_condition_shear', 0),
            'is_lightweight': anchor_check_params.get('is_lightweight'),
            'lambda_a': anchor_check_params.get('lambda_a', 1.0),
            'fc_psi': materials.get('fc_psi'),
            'fya_ksi': materials.get('bolt_fya_ksi'),
            'futa_ksi': materials.get('bolt_futa_ksi'),
        }

        # ==========================================================
        # ==== START: 優化核心：快取與輔助函式 ====
        # ==========================================================
        print("\n--- [Report Generation] Starting plot generation with Caching ---")

        analysis_cache = {}
        plot_data_cache = {}

        # 預先計算一次英制錨栓座標，供 get_shear_details 使用
        bolt_coords_imperial_global = analysis.get_bolt_coordinates(plate_params, bolt_params)

        def get_analysis_results(combo_id, generate_plot=False):
            cache_key = (combo_id, generate_plot)
            if cache_key in analysis_cache:
                return analysis_cache[cache_key]

            loads = find_loads_by_id(loads_combinations, combo_id)
            if not loads: return None

            print(f"    - ANALYSIS CACHE MISS: Running analysis for Combo #{combo_id} (plot={generate_plot})")
            results = analysis.perform_analysis(
                plate_shape=plate_params.get('shape'), P_applied=loads.get('p_applied'),
                Mx_applied=loads.get('mx_applied'), My_applied=loads.get('my_applied'),
                Es=materials.get('es_ksi'), Ec=materials.get('ec_ksi'),
                bolt_layout_mode=bolt_params.get('layout_mode'), plate_params=plate_params,
                bolt_params=bolt_params, generate_plot_data=generate_plot, unit_system=unit_system
            )
            analysis_cache[cache_key] = results
            return results

        def get_plot_data(combo_id):
            if combo_id in plot_data_cache:
                return plot_data_cache[combo_id]

            print(f"    - PLOT DATA CACHE MISS: Generating plot data for Combo #{combo_id}")
            data = {
                'stress_plot': None,
                'tension_table': [],
                'total_tension': 0,
                'shear_plot': None,
                'shear_table': [],
                'shear_totals': {}
            }

            # --- 生成應力圖和拉力數據 ---
            analysis_res = get_analysis_results(combo_id, generate_plot=True)
            if analysis_res:
                data['stress_plot'] = analysis_res.get('plot_base64')
                forces = np.array(analysis_res.get('bolt_forces', []))
                if forces.size > 0:
                    data['tension_table'] = [{'index': i, 'tension_force': f if f > 1e-9 else 0.0} for i, f in
                                             enumerate(forces)]
                    data['total_tension'] = np.sum(forces[forces > 1e-9])

            # --- 生成剪力圖和表格數據 ---
            loads = find_loads_by_id(loads_combinations, combo_id)
            if loads:
                # 注意：這裡的第五個參數 bolt_coords_imperial_global 是我們在 view 函式開頭就計算好的純英制座標
                bolt_coords_imperial, table_data, demands_imperial, critical_bolt_info, totals = get_shear_details(
                    loads,
                    plate_params,
                    bolt_params,
                    unit_system,
                    bolt_coords_imperial_global
                )

                if table_data:
                    plot_title = f"剪力分佈圖 (Combo #{combo_id})"
                    shear_plot = analysis.generate_shear_vector_plot(
                        bolt_coords_imperial_global,
                        demands_imperial,
                        plate_params,
                        pedestal_params,
                        column_params,
                        bolt_params,
                        critical_bolt_index=critical_bolt_info.get('index'),
                        title=plot_title,
                        vector_type='components',
                        unit_system=unit_system,
                        show_background_geometry=False  # <--- 【核心新增】
                    )
                    data.update({
                        'shear_plot': shear_plot,
                        'shear_table': table_data,
                        'shear_totals': totals
                    })

            plot_data_cache[combo_id] = data
            return data

        # ===== 【2. prepare_check_params 完整內容】 =====
        def prepare_check_params(unit_system_local):
            """
            準備一套適用於當前單位制的、用於檢核的參數字典副本。
            """
            # 從最外層作用域複製基礎參數
            anchor_params_check = ANCHOR_PARAMS.copy()
            pedestal_params_check = pedestal_params.copy()
            bolt_params_check = bolt_params.copy()

            # get_bolt_coordinates 永遠返回英制座標
            all_bolt_coords_check = analysis.get_bolt_coordinates(plate_params, bolt_params)

            if unit_system_local == 'mks':
                print("    - Preparing MKS parameters for geometry plots...")
                # 轉換長度相關的參數
                if anchor_params_check.get('h_ef') is not None:
                    anchor_params_check['h_ef'] *= IN_TO_CM
                if anchor_params_check.get('supplementary_rebar_spacing') is not None:
                    anchor_params_check['supplementary_rebar_spacing'] *= IN_TO_CM

                # 轉換面積相關的參數
                if anchor_params_check.get('Abrg') is not None:
                    anchor_params_check['Abrg'] *= IN2_TO_CM2

                # 轉換應力相關的參數
                if anchor_params_check.get('fc_psi') is not None:
                    anchor_params_check['fc_psi'] *= PSI_TO_KGF_CM2
                if anchor_params_check.get('fya_ksi') is not None:
                    anchor_params_check['fya_ksi'] *= KSI_TO_KGF_CM2
                if anchor_params_check.get('futa_ksi') is not None:
                    anchor_params_check['futa_ksi'] *= KSI_TO_KGF_CM2

                # 轉換墩柱幾何參數
                for key in ['N', 'B', 'D', 'h']:
                    if pedestal_params_check.get(key) is not None:
                        pedestal_params_check[key] *= IN_TO_CM

                # 轉換錨栓座標
                all_bolt_coords_check = all_bolt_coords_check * IN_TO_CM

            return anchor_params_check, pedestal_params_check, bolt_params_check, all_bolt_coords_check

        # ==========================================================
        # ==== START: 按需生成圖表 (Plot Generation on Demand) ====
        # ==========================================================
        print("\n--- [Report Generation] Starting plot generation ---")

        # --- 圖表 1: 幾何關係示意圖 (固定生成) ---
        geometry_plot_base64 = analysis.generate_geometry_plot(
            plate_params=plate_params, pedestal_params=pedestal_params,
            bolt_params=bolt_params, column_params=column_params, unit_system=unit_system
        )

        # --- 圖表 2 & 3: 為「混凝土承壓」和「基礎版彎曲」生成應力圖 ---
        plot_generating_keys = ['concrete_bearing', 'plate_bending']
        for key in plot_generating_keys:
            check_data = envelope_results.get(key)
            if check_data and check_data.get('details', {}).get('result') != 'N/A':

                # ===== 【核心修正】在這裡明確地定義 combo_id 變數 =====
                combo_id = check_data.get('combo_id')
                if not combo_id:
                    continue  # 如果沒有 combo_id，就跳過這個檢核項

                loads = find_loads_by_id(loads_combinations, combo_id)
                # =======================================================

                if loads:
                    print(f"    - Generating plot for '{key}' (Combo #{combo_id})")  # <-- 現在可以安全使用 combo_id
                    analysis_res_for_plot = get_analysis_results(combo_id, generate_plot=True)  # <-- 紅線消失

                    if analysis_res_for_plot and analysis_res_for_plot.get('plot_base64'):
                        envelope_results[key]['details']['plot_base64'] = analysis_res_for_plot.get('plot_base64')

        # --- 圖表 4: 為所有「拉力控制」的檢核項準備「應力圖」和「拉力表」 ---
        tension_check_keys = ['anchor_nsa', 'anchor_npn', 'anchor_ncb_single', 'anchor_ncbg_group', 'anchor_nsb_single',
                              'anchor_nsbg_group']
        tension_plot_cache = {}

        for key in tension_check_keys:
            check_data = envelope_results.get(key)
            combo_id = check_data.get('combo_id') if check_data else None
            if combo_id:
                if combo_id not in tension_plot_cache:
                    print(f"    - Generating tension plot/table for Combo #{combo_id} (triggered by '{key}')")
                    loads = find_loads_by_id(loads_combinations, combo_id)
                    plot_data = {'plot_base64': None, 'tension_table_data': [], 'total_tension': 0}
                    if loads:
                        plot_analysis_results = get_analysis_results(combo_id, generate_plot=True)
                        if plot_analysis_results:
                            forces = np.array(plot_analysis_results['bolt_forces'])
                            coords = np.array(plot_analysis_results['bolt_coords'])
                            table_data = [{'index': i, 'tension_force': f if f > 1e-9 else 0.0} for i, f in
                                          enumerate(forces)]
                            plot_data.update({
                                'plot_base64': plot_analysis_results.get('plot_base64'),
                                'tension_table_data': table_data,
                                'total_tension': np.sum(forces[forces > 1e-9])
                            })
                    tension_plot_cache[combo_id] = plot_data

                if 'details' in check_data:
                    check_data['details'].update(tension_plot_cache[combo_id])

        # --- 圖表 5: 為 Ncb, Ncbg, Nsb, Vcb, Vcbg 等生成專屬「幾何示意圖」 ---

        anchor_params_for_plot, pedestal_params_for_plot, bolt_params_for_plot, all_bolt_coords_for_plot = prepare_check_params(
            unit_system)

        # 5a. Ncb_single 的 ANc 圖
        check_data = envelope_results.get('anchor_ncb_single')
        if check_data and check_data.get('details', {}).get('result') != 'N/A':
            critical_anchor_index = check_data['details'].get('anchor_index')
            if critical_anchor_index is not None:
                critical_anchor_coord = all_bolt_coords_for_plot[critical_anchor_index]
                ncb_res = anchor_tension_check.calculate_single_anchor_breakout_Ncb(
                    critical_anchor_coord, pedestal_params_for_plot, anchor_params_for_plot,
                    all_bolt_coords=all_bolt_coords_for_plot.tolist(), generate_plot=True
                )
                if ncb_res and ncb_res.get('plot_base64'):
                    check_data['details']['anc_plot_base64'] = ncb_res['plot_base64']

        # 5b. Ncbg_group 的 ANcg 圖
        check_data = envelope_results.get('anchor_ncbg_group')
        if check_data and check_data.get('details', {}).get('result') != 'N/A':
            combo_id = check_data.get('combo_id')
            analysis_res_imperial = get_analysis_results(combo_id, generate_plot=False)  # 從快取獲取英制基礎數據
            if analysis_res_imperial:
                # 建立一個副本用於傳遞，避免修改快取中的原始數據
                analysis_res_for_plot = analysis_res_imperial.copy()
                if unit_system == 'mks':
                    # 如果是 MKS，手動轉換座標
                    analysis_res_for_plot['bolt_coords'] = (
                            np.array(analysis_res_for_plot['bolt_coords']) * IN_TO_CM).tolist()

                ncbg_res = anchor_tension_check.calculate_group_breakout_Ncbg(
                    analysis_res_for_plot,  # <--- 傳遞單位制正確的 analysis 結果
                    pedestal_params_for_plot,
                    anchor_params_for_plot,
                    generate_plot=True
                )
                if ncbg_res and ncbg_res.get('plot_base64'):
                    check_data['details']['ancg_plot_base64'] = ncbg_res['plot_base64']

        # 5c. Nsb_single 的幾何圖
        check_data = envelope_results.get('anchor_nsb_single')
        if check_data and check_data.get('details', {}).get('result') != 'N/A':
            critical_anchor_index = check_data['details'].get('anchor_index')

            if critical_anchor_index is not None:
                critical_anchor_coord = all_bolt_coords_for_plot[critical_anchor_index]
                nsb_res = anchor_tension_check.calculate_side_face_blowout_for_single_anchor(
                    critical_anchor_coord, pedestal_params_for_plot, anchor_params_for_plot,
                    bolt_params_for_plot, all_bolt_coords=all_bolt_coords_for_plot.tolist(), generate_plot=True
                )
                if nsb_res and nsb_res.get('plot_base64'):
                    check_data['details']['nsb_plot_base64'] = nsb_res['plot_base64']

        # 5d. Nsbg_group 的幾何圖
        check_data = envelope_results.get('anchor_nsbg_group')
        if check_data and check_data.get('details', {}).get('result') != 'N/A':
            combo_id = check_data.get('combo_id')
            loads = find_loads_by_id(loads_combinations, combo_id)  # <--- 補上
            if loads:
                analysis_res = get_analysis_results(combo_id, generate_plot=True)
                if unit_system == 'mks':
                    analysis_res['bolt_coords'] = (np.array(analysis_res['bolt_coords']) * IN_TO_CM).tolist()

                nsbg_res = anchor_tension_check.calculate_side_face_blowout_for_group(
                    analysis_res, pedestal_params_for_plot, anchor_params_for_plot,
                    bolt_params_for_plot, generate_plot=True
                )
                if nsbg_res and nsbg_res.get('plot_base64'):
                    check_data['details']['nsbg_plot_base64'] = nsbg_res['plot_base64']

            # --- 圖表 6: 為「剪力控制」的檢核項準備「剪力分佈圖」和「剪力分量表」 ---
            shear_check_keys = [
                'anchor_vsa', 'anchor_vcp_single', 'anchor_vcpg_group',  # 總合力檢核
                'anchor_vcb_single_x', 'anchor_vcb_single_y',  # 單根分量檢核
                'anchor_vcbg_group_x', 'anchor_vcbg_group_y'  # 群組分量檢核
            ]

            for key in shear_check_keys:
                check_data = envelope_results.get(key)
                if not (check_data and check_data.get('details') and check_data.get('details', {}).get(
                        'result') != 'N/A'):
                    continue  # 如果沒有這個檢核項或不適用，就跳過

                combo_id = check_data.get('combo_id')
                loads = find_loads_by_id(loads_combinations, combo_id)

                if loads:
                    print(f"    - Generating shear plot/table for '{key}' (Combo #{combo_id})")

                    bolt_coords_imperial, table_data, demands_imperial, critical_bolt_info, totals = get_shear_details(
                        loads,
                        plate_params,
                        bolt_params,
                        unit_system,
                        bolt_coords_imperial_global  # <-- 使用在 view 開頭計算好的純英制座標
                    )

                    if bolt_coords_imperial is not None:
                        plot_title = f"{key.replace('_', ' ').title()} 控制工況剪力分佈圖 (Combo #{combo_id})"

                        # 2. 【核心修正】在這裡，我們根據檢核項的類型，從正確的來源提取索引
                        critical_idx = None
                        highlight_idxs = None
                        display_dir = None

                        if 'group' in key:
                            # 這是群組檢核 (Vcbg, Vcpg)
                            highlight_idxs = check_data.get('details', {}).get('controlling_anchor_indices')
                        else:
                            if key in ['anchor_vsa', 'anchor_vcp_single']:
                                critical_idx = critical_bolt_info.get('index')
                            # Vcb 是基於該檢核自身算出的最不利錨栓
                            else:
                                critical_idx = check_data.get('details', {}).get('anchor_index')

                        # 根據 key 決定是否只顯示特定方向
                        if '_x' in key:
                            display_dir = 'X'
                        elif '_y' in key:
                            display_dir = 'Y'

                        # 傳入所有必要的參數
                        plot_base64_components = analysis.generate_shear_vector_plot(
                            bolt_coords_imperial,
                            demands_imperial,
                            plate_params,
                            pedestal_params,
                            column_params,
                            bolt_params,
                            critical_bolt_index=critical_idx,  # <-- 傳入單根索引 (可能是 None)
                            highlight_indices=highlight_idxs,  # <-- 傳入群組索引列表 (可能是 None)
                            title=plot_title,
                            vector_type='components',
                            unit_system=unit_system,
                            show_background_geometry=False,  # 在報告書中顯示完整背景
                            display_direction=display_dir
                        )

                        # 將圖表和表格數據注入到對應的檢核項中
                        envelope_results[key]['details']['shear_distribution_plot'] = plot_base64_components
                        envelope_results[key]['details']['shear_table_data'] = table_data
                        envelope_results[key]['details']['shear_table_totals'] = totals

        # --- 圖表 7: 為 Vcb 和 Vcbg 生成 AVc 幾何示意圖 ---
        vcb_keys = ['anchor_vcb_single_x', 'anchor_vcb_single_y', 'anchor_vcbg_group_x', 'anchor_vcbg_group_y']
        for key in vcb_keys:
            check_data = envelope_results.get(key)
            if check_data and check_data.get('details', {}).get('result') != 'N/A':
                combo_id = check_data.get('combo_id')
                loads = find_loads_by_id(loads_combinations, combo_id)
                if loads:
                    _, _, demands_imperial, _, _ = get_shear_details(loads, plate_params, bolt_params, unit_system,
                                                                     bolt_coords_imperial_global)
                    if 'single' in key:
                        direction = (1, 0) if '_x' in key else (0, 1)
                        anchor_index = check_data['details'].get('anchor_index')
                        if anchor_index is not None:
                            anchor_coord = all_bolt_coords_for_plot[anchor_index]
                            vcb_res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                                anchor_coord, direction, pedestal_params_for_plot, anchor_params_for_plot,
                                bolt_params_for_plot, all_bolt_coords=all_bolt_coords_for_plot.tolist(),
                                generate_plot=True
                            )
                            if vcb_res and vcb_res.get('plot_base64'):
                                check_data['details']['avc_plot_base64'] = vcb_res['plot_base64']
                        elif 'group' in key:
                            # 【核心修正】為 Vcbg 準備正確單位的 demands
                            demands_for_plot = demands_imperial
                            if unit_system == 'mks':
                                # 雖然 get_shear_details 返回的 demands 內部值是 kips，但座標是英制 in
                                # 我們需要將座標轉換為 cm 以匹配 _for_plot 參數
                                demands_for_plot = json.loads(json.dumps(demands_imperial))  # 深拷貝
                                for d in demands_for_plot:
                                    d['coord'] = (np.array(d['coord']) * IN_TO_CM).tolist()

                            direction = (1, 0) if '_x' in key else (0, 1)
                            vcbg_combinations = anchor_shear_check.calculate_group_shear_breakout_Vcbg(
                                direction, pedestal_params_for_plot, anchor_params_for_plot,
                                bolt_params_for_plot, all_bolt_coords_for_plot,
                                demands_for_plot,  # <--- 傳遞單位制正確的 demands
                                generate_plot=True
                            )
                            if vcbg_combinations:
                                critical_vcbg_res = min(vcbg_combinations, key=lambda x: x['phi_Vcbg'])
                                if critical_vcbg_res.get('plot_base64'):
                                    check_data['details']['avc_plot_base64'] = critical_vcbg_res['plot_base64']

        print("--- [Report Generation] Plot generation finished ---")

        # 準備最終傳遞給模板的 context
        context = {
            'inputs': inputs_data,
            'results': envelope_results,
            'loads': loads_combinations,
            'geometry_plot_base64': geometry_plot_base64,
            'results_json_for_debug': json.dumps(envelope_results, indent=2, cls=NumpyEncoder),
            'unit_system': unit_system
        }

        return render(request, 'SteelDesign/BPandAnchor/steel_BPandAnchor_Report.html', context)

    except (json.JSONDecodeError, KeyError) as e:
        import traceback
        print(traceback.format_exc())
        return HttpResponse(
            f"生成報告時發生嚴重錯誤，可能是 session 資料已過期或格式不符。請返回重新計算。<br>錯誤詳情: {e}", status=400)

import bpN_mainAnalysis as analysis
import bpN_Axial_ConcCheck as conc_check
import bpN_tpCheck as tp_check
import bpN_AnchorTensionCheck as anchor_tension_check
import bpN_AnchorShearCheck as anchor_shear_check
import numpy as np
from scipy.spatial.distance import pdist

# --- 使用者輸入區 ---
# (与您上一版提供的完全相同)
PLATE_SHAPE = 'rectangle'
BOLT_LAYOUT = 'grid'
RECT_PARAMS = {'N': 25.0, 'B': 20.0, 'n': 0.0, 'b': 0.0}
GRID_BOLT_PARAMS = {
    'diameter': 0.625, 'threads_per_inch': 11, 'Abrg_in2': 0.454,
    'edge_dist_X': 2.5, 'edge_dist_Y': 2.5, 'num_inserted_X': 1, 'num_inserted_Y': 1
}
CIRCULAR_BOLT_PARAMS = {'diameter': 5.0 / 8.0, 'count': 8, 'radius': 8.5, 'start_angle': 0.0, 'Abrg_in2': 0.454}
# [修改] B. 荷载设定 - 新增剪力输入
P_APPLIED = -90.0
MX_APPLIED = 25 * 12
MY_APPLIED = 36.67 * 12
VX_APPLIED = 63.0  # [新增] X 方向总剪力 (kips)
VY_APPLIED = 30.0  # [新增] Y 方向总剪力 (kips)

ES_KSI = 29000.0
EC_KSI = 3122.02
FC_PSI = 3000.0
PLATE_FY_KSI = 36.0
BOLT_FYA_KSI = 36.0
BOLT_FUTA_KSI = 58.0
PEDESTAL_PARAMS = {'N': 50.0, 'B': 30.0, 'h': 40.0}
COLUMN_PARAMS = {'type': 'H-Shape', 'd': 10.0, 'bf': 10.0, 'tf': 0.56, 'tw': 0.34}
PLATE_TP_IN = 1.5

ANCHOR_PARAMS = {
    'h_ef': 20.0, 'anchor_type': 'cast-in', 'is_headed': True, 'is_cracked': True,
    'reinf_condition_shear': 0,
    'is_lightweight': False, 'fc_psi': FC_PSI, 'fya_ksi': BOLT_FYA_KSI,
    'futa_ksi': BOLT_FUTA_KSI, 'phi_cb': 0.70, 'phi_st': 0.75,
    'phi_pn': 0.70, 'phi_sfb': 0.70, 'phi_sv': 0.65, 'phi_cv': 0.70
}

# --- 主程式執行區 ---
if __name__ == "__main__":

    if PLATE_SHAPE == 'rectangle':
        plate_params = RECT_PARAMS
    else:
        plate_params = CIRCLE_OCT_PARAMS
    if BOLT_LAYOUT == 'grid':
        bolt_params = GRID_BOLT_PARAMS
    else:
        bolt_params = CIRCULAR_BOLT_PARAMS

    # 1. 執行應力分析
    analysis_results = analysis.perform_analysis(
        plate_shape=PLATE_SHAPE, P_applied=P_APPLIED, Mx_applied=MX_APPLIED, My_applied=MY_APPLIED,
        Es=ES_KSI, Ec=EC_KSI, bolt_layout_mode=BOLT_LAYOUT,
        plate_params=plate_params, bolt_params=bolt_params, show_plot=False
    )

    if analysis_results:
        analysis_results['bolt_params_for_check'] = bolt_params

        # --- 分析結果摘要 ---
        print("\n--- 分析結果摘要 ---")
        print(f"  分析模式: {analysis_results['status']}")
        print(f"  最大混凝土壓力: {analysis_results['max_pressure']:.2f} ksi")
        print(f"  混凝土總壓力 (Bu): {analysis_results['concrete_force_Bu']:.2f} kips")
        bolt_forces = analysis_results['bolt_forces']
        num_tension_bolts = np.sum(bolt_forces > 0.001)
        print(f"  受拉錨栓數: {num_tension_bolts} / {analysis_results['num_bolts']}")

        # --- 檢核 A: 混凝土承壓 ---
        if analysis_results['concrete_force_Bu'] > 1e-6:
            conc_check.perform_bearing_check(
                analysis_results=analysis_results,
                pedestal_params=PEDESTAL_PARAMS,
                fc_psi=FC_PSI
            )

        # --- 檢核 B: 基礎版彎曲 (厚度) ---
        if analysis_results['max_pressure'] > 1e-6 or np.any(bolt_forces > 0):
            # (此部分逻辑与您提供的版本相同)
            simplified_grid_data = None
            if analysis_results.get('grid_pressures') is not None:
                grid_data = analysis_results.get('grid_data', {})
                cell_area_val = grid_data.get('ca')
                if cell_area_val is None and 'xv' in grid_data:
                    xv = grid_data['xv']
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
                'plate_N': analysis_results['plate_N']
            }
            tp_check.perform_plate_bending_check(
                analysis_results=analysis_results_for_tp_check,
                column_params=COLUMN_PARAMS,
                plate_fy_ksi=PLATE_FY_KSI,
                plate_tp_in=PLATE_TP_IN
            )

        # --- 檢核 C: 錨栓拉力 (仅检核钢材强度) ---
        if num_tension_bolts > 0:
            print("\n\n=============================================")
            print("--- 開始錨栓拉力強度檢核 ---")

            # 找出受最大拉力的锚栓
            max_tension_force_Nua = np.max(bolt_forces)
            max_tension_idx = np.argmax(bolt_forces)
            max_tension_anchor_coord = analysis_results['bolt_coords'][max_tension_idx]

            # --- 检核 C1: 钢材拉力强度 (Nsa) ---
            nsa_res = anchor_tension_check.calculate_steel_strength_Nsa(bolt_params, ANCHOR_PARAMS)
            phi_Nsa = nsa_res['phi_Nsa']
            dc_ratio_nsa = max_tension_force_Nua / phi_Nsa if phi_Nsa > 0 else float('inf')
            print("\n--- [檢核 C1] 鋼材拉力強度 (Nsa) ---")
            print(f"  (针对受力最大锚栓 #{max_tension_idx + 1})")
            print(f"  D/C Ratio = {dc_ratio_nsa:.3f} => {'PASS' if dc_ratio_nsa <= 1.0 else 'FAIL'}")

            # --- 检核 C2: 拔出强度 (Npn) ---
            npn_res = anchor_tension_check.calculate_pullout_strength_Npn(analysis_results, ANCHOR_PARAMS)
            if npn_res:
                phi_Npn = npn_res['phi_Npn']
                dc_ratio_npn = max_tension_force_Nua / phi_Npn if phi_Npn > 0 else float('inf')
                print("\n--- [檢核 C2] 拔出強度 (Npn) ---")
                print(f"  (针对受力最大锚栓 #{max_tension_idx + 1})")
                print(f"  D/C Ratio = {dc_ratio_npn:.3f} => {'PASS' if dc_ratio_npn <= 1.0 else 'FAIL'}")

            # --- [核心修正] 检核 C3: 混凝土拉破强度 (Ncb & Ncbg) ---
            print("\n--- [檢核 C3] 混凝土拉破強度 (Ncb/Ncbg) ---")

            # 3a. 先检核最不利单根锚栓 (受力最大者)
            ncb_res = anchor_tension_check.calculate_single_anchor_breakout_Ncb(
                max_tension_anchor_coord, PEDESTAL_PARAMS, ANCHOR_PARAMS
            )
            if ncb_res:
                phi_Ncb = ncb_res['phi_Ncb']
                dc_ratio_ncb = max_tension_force_Nua / phi_Ncb if phi_Ncb > 0 else float('inf')
                print(f"  单根检核 (锚栓 #{max_tension_idx + 1}):")
                print(f"    D/C Ratio = {dc_ratio_ncb:.3f} => {'PASS' if dc_ratio_ncb <= 1.0 else 'FAIL'}")

            # 3b. 判断是否需要额外进行群组检核
            if num_tension_bolts > 1:
                tension_indices = np.where(bolt_forces > 0.001)[0]
                tension_coords = analysis_results['bolt_coords'][tension_indices]
                max_spacing = np.max(pdist(tension_coords))
                critical_spacing = 3 * ANCHOR_PARAMS['h_ef']
                print("")
                if max_spacing < critical_spacing:
                    print(f"  群组检核: 最大间距 s={max_spacing:.2f} < 3*hef={critical_spacing:.2f} => 需进行群组检核")
                    group_ncbg_res = anchor_tension_check.calculate_group_breakout_Ncbg(
                        analysis_results, PEDESTAL_PARAMS, ANCHOR_PARAMS)
                    if group_ncbg_res:
                        total_tension_force = np.sum(bolt_forces[tension_indices])
                        phi_Ncbg = group_ncbg_res['phi_Ncbg']
                        dc_ratio_group = total_tension_force / phi_Ncbg if phi_Ncbg > 0 else float('inf')
                        print(
                            f"    群组 D/C Ratio = {dc_ratio_group:.3f} => {'PASS' if dc_ratio_group <= 1.0 else 'FAIL'}")
                else:
                    print(f"  群组检核: 最大间距 s={max_spacing:.2f} >= 3*hef={critical_spacing:.2f} => 无需群组检核")

            print("\n--- [檢核 C4] 側向脹破強度 (Nsb/Nsbg) ---")

            # 4a. 先对最不利单根锚栓进行检核 (遍历所有受拉锚栓找出最不利者)
            tension_indices = np.where(bolt_forces > 0.001)[0]
            max_dc_ratio_nsb = 0.0
            critical_nsb_anchor_index = -1
            nsb_applicable = False

            # 这个循环是为了找出最不利的单根 Nsb D/C Ratio
            for i in tension_indices:
                nsb_res = anchor_tension_check.calculate_side_face_blowout_for_single_anchor(
                    analysis_results['bolt_coords'][i], PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params)
                if nsb_res:
                    nsb_applicable = True
                    phi_Nsb = nsb_res['phi_Nsb']
                    dc_ratio_i = bolt_forces[i] / phi_Nsb if phi_Nsb > 0 else float('inf')
                    if dc_ratio_i > max_dc_ratio_nsb:
                        max_dc_ratio_nsb = dc_ratio_i
                        critical_nsb_anchor_index = i + 1

            if nsb_applicable:
                print(f"  单根检核:")
                print(f"    最不利锚栓: #{critical_nsb_anchor_index}")
                print(f"    D/C Ratio = {max_dc_ratio_nsb:.3f} => {'PASS' if max_dc_ratio_nsb <= 1.0 else 'FAIL'}")
            else:
                print("  单根检核: 条件不符 (如埋深不足)，此破坏模式不适用。")

            # 4b. 判断是否需要额外进行群组检核
            if nsb_applicable and num_tension_bolts > 1:
                # 找出所有受拉锚栓中，ca1 最小的那个
                tension_coords = analysis_results['bolt_coords'][tension_indices]
                all_ca1s = [
                    min(PEDESTAL_PARAMS['N'] / 2 - y, y - (-PEDESTAL_PARAMS['N'] / 2), PEDESTAL_PARAMS['B'] / 2 - x,
                        x - (-PEDESTAL_PARAMS['B'] / 2)) for x, y in tension_coords]
                group_ca1 = min(all_ca1s)

                # 找出所有在最不利边缘上的锚栓
                edge_group_indices = [i for i, ca in enumerate(all_ca1s) if abs(ca - group_ca1) < 0.1]
                edge_group_coords = tension_coords[edge_group_indices]

                if len(edge_group_coords) > 1:
                    s = np.max(pdist(edge_group_coords))
                    critical_spacing = 6 * group_ca1

                    if s < critical_spacing:
                        print(
                            f"  群组检核: 临界边缘上存在间距 s={s:.2f} < 6*ca1={critical_spacing:.2f} 的锚栓群 => 需进行群组检核")

                        # 使用已有的计算器函式
                        nsbg_res = anchor_tension_check.calculate_side_face_blowout_for_group(
                            edge_group_coords, PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params)

                        if nsbg_res:
                            # 计算作用在此边缘群组上的总力
                            original_indices = tension_indices[edge_group_indices]
                            total_group_force = np.sum(bolt_forces[original_indices])
                            phi_Nsbg = nsbg_res['phi_Nsbg']
                            dc_ratio_group = total_group_force / phi_Nsbg if phi_Nsbg > 0 else float('inf')

                            print(
                                f"    群组 D/C Ratio = {dc_ratio_group:.3f} => {'PASS' if dc_ratio_group <= 1.0 else 'FAIL'}")
                    else:
                        print("  群组检核: 临界边缘上锚栓间距足够，无需群组检核。")
                else:
                    print("  群组检核: 临界边缘上只有一根锚栓，无需群组检核。")


        else:
            print("\n--- 無受拉錨栓，跳過錨栓拉力檢核 ---")

        V_total = np.sqrt(VX_APPLIED ** 2 + VY_APPLIED ** 2)
        if V_total > 1e-6:
            print("\n\n=============================================")
            print("--- 開始錨栓剪力強度檢核 ---")

            num_bolts = analysis_results['num_bolts']
            # [核心修正] 分别计算 X, Y 方向的单根锚栓需求剪力
            Vua_x_per_bolt = abs(VX_APPLIED) / num_bolts if num_bolts > 0 else 0
            Vua_y_per_bolt = abs(VY_APPLIED) / num_bolts if num_bolts > 0 else 0
            print(f"  X向需求剪力 Vua,x = {Vua_x_per_bolt:.2f} kips/bolt")
            print(f"  Y向需求剪力 Vua,y = {Vua_y_per_bolt:.2f} kips/bolt")

            # --- 检核 D1: 钢材剪力强度 (Vsa) ---
            # (此检核是针对总剪力，保持不变)
            Vua_total_per_bolt = V_total / num_bolts
            vsa_res = anchor_shear_check.calculate_steel_strength_Vsa(bolt_params, ANCHOR_PARAMS)
            phi_Vsa = vsa_res['phi_Vsa']
            dc_ratio_vsa = Vua_total_per_bolt / phi_Vsa if phi_Vsa > 0 else float('inf')
            print("\n--- [檢核 D1] 鋼材剪力強度 (Vsa) ---")
            print(f"  D/C Ratio = {dc_ratio_vsa:.3f} => {'PASS' if dc_ratio_vsa <= 1.0 else 'FAIL'}")

            # --- [新增] 检核 D2: 混凝土剪破强度 (Vcb) ---
            print("\n--- [檢核 D2] 混凝土剪破強度 (Vcb) ---")

            all_bolt_coords = analysis_results['bolt_coords']
            pedestal_B = PEDESTAL_PARAMS['B']
            pedestal_N = PEDESTAL_PARAMS['N']

            # a) 检核 X 方向剪力
            if abs(VX_APPLIED) > 1e-6:
                Vua_x_per_bolt = abs(VX_APPLIED) / analysis_results['num_bolts']

                # 找出最外侧的一排锚栓
                if VX_APPLIED > 0:  # 正向剪力，找 X 坐标最大的
                    max_x = np.max(all_bolt_coords[:, 0])
                    outermost_bolts_indices = np.where(np.isclose(all_bolt_coords[:, 0], max_x))[0]
                else:  # 负向剪力，找 X 坐标最小的
                    min_x = np.min(all_bolt_coords[:, 0])
                    outermost_bolts_indices = np.where(np.isclose(all_bolt_coords[:, 0], min_x))[0]

                outermost_bolts_coords = all_bolt_coords[outermost_bolts_indices]

                # 在这排锚栓中，找出 ca2 (Y方向边距) 最小的那根
                y_distances = np.minimum(pedestal_N / 2 - outermost_bolts_coords[:, 1],
                                         outermost_bolts_coords[:, 1] - (-pedestal_N / 2))
                critical_idx_local = np.argmin(y_distances)
                critical_anchor_coord_x = outermost_bolts_coords[critical_idx_local]

                # 计算这根最不利锚栓的剪破强度
                direction_x = (1, 0) if VX_APPLIED > 0 else (-1, 0)
                vcb_x_res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                    critical_anchor_coord_x, direction_x, PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params)

                if vcb_x_res:
                    phi_Vcb_x = vcb_x_res['phi_Vcb']
                    dc_ratio_vcb_x = Vua_x_per_bolt / phi_Vcb_x if phi_Vcb_x > 0 else float('inf')
                    print(
                        f"  X方向检核 (最不利锚栓 at ({critical_anchor_coord_x[0]:.1f}, {critical_anchor_coord_x[1]:.1f}), ca1={vcb_x_res['ca1']:.2f} in):")
                    print(f"    D/C Ratio = {dc_ratio_vcb_x:.3f} => {'PASS' if dc_ratio_vcb_x <= 1.0 else 'FAIL'}")

            if VX_APPLIED > 0:
                max_x = np.max(all_bolt_coords[:, 0]);
                outermost_bolts_indices = \
                    np.where(np.isclose(all_bolt_coords[:, 0], max_x))[0]
            else:
                min_x = np.min(all_bolt_coords[:, 0]);
                outermost_bolts_indices = \
                    np.where(np.isclose(all_bolt_coords[:, 0], min_x))[0]

            if len(outermost_bolts_indices) > 1:
                outermost_group_coords = all_bolt_coords[outermost_bolts_indices]
                s_group = np.max(outermost_group_coords[:, 1]) - np.min(outermost_group_coords[:, 1])
                ca1_group = vcb_x_res['ca1'] if vcb_x_res else 0  # 使用单根检核算出的 ca1

                if s_group < 3 * ca1_group:
                    print(f"  X方向群组检核: 间距 s={s_group:.2f} < 3*ca1={3 * ca1_group:.2f} => 需进行群组检核")
                    vcbg_x_res = anchor_shear_check.calculate_group_shear_breakout_Vcbg(
                        direction_x, PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params, all_bolt_coords)
                    if vcbg_x_res:
                        phi_Vcbg_x = vcbg_x_res['phi_Vcbg']
                        dc_ratio_vcbg_x = abs(VX_APPLIED) / phi_Vcbg_x if phi_Vcbg_x > 0 else float('inf')
                        print(
                            f"    群组 D/C Ratio = {dc_ratio_vcbg_x:.3f} => {'PASS' if dc_ratio_vcbg_x <= 1.0 else 'FAIL'}")

            # b) 检核 Y 方向剪力
            if abs(VY_APPLIED) > 1e-6:
                Vua_y_per_bolt = abs(VY_APPLIED) / analysis_results['num_bolts']

                if VY_APPLIED > 0:  # 正向剪力，找 Y 坐标最大的
                    max_y = np.max(all_bolt_coords[:, 1])
                    outermost_bolts_indices = np.where(np.isclose(all_bolt_coords[:, 1], max_y))[0]
                else:  # 负向剪力，找 Y 坐标最小的
                    min_y = np.min(all_bolt_coords[:, 1])
                    outermost_bolts_indices = np.where(np.isclose(all_bolt_coords[:, 1], min_y))[0]

                outermost_bolts_coords = all_bolt_coords[outermost_bolts_indices]

                x_distances = np.minimum(pedestal_B / 2 - outermost_bolts_coords[:, 0],
                                         outermost_bolts_coords[:, 0] - (-pedestal_B / 2))
                critical_idx_local = np.argmin(x_distances)
                critical_anchor_coord_y = outermost_bolts_coords[critical_idx_local]

                direction_y = (0, 1) if VY_APPLIED > 0 else (0, -1)
                vcb_y_res = anchor_shear_check.calculate_single_anchor_shear_breakout_Vcb(
                    critical_anchor_coord_y, direction_y, PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params)

                if vcb_y_res:
                    phi_Vcb_y = vcb_y_res['phi_Vcb']
                    dc_ratio_vcb_y = Vua_y_per_bolt / phi_Vcb_y if phi_Vcb_y > 0 else float('inf')
                    print(
                        f"  Y方向检核 (最不利锚栓 at ({critical_anchor_coord_y[0]:.1f}, {critical_anchor_coord_y[1]:.1f}), ca1={vcb_y_res['ca1']:.2f} in):")
                    print(f"    D/C Ratio = {dc_ratio_vcb_y:.3f} => {'PASS' if dc_ratio_vcb_y <= 1.0 else 'FAIL'}")

            if VY_APPLIED > 0:
                max_y = np.max(all_bolt_coords[:, 1]); outermost_bolts_indices = \
                    np.where(np.isclose(all_bolt_coords[:, 1], max_y))[0]
            else:
                min_y = np.min(all_bolt_coords[:, 1]); outermost_bolts_indices = \
                    np.where(np.isclose(all_bolt_coords[:, 1], min_y))[0]

            if len(outermost_bolts_indices) > 1:
                outermost_group_coords = all_bolt_coords[outermost_bolts_indices]
                s_group = np.max(outermost_group_coords[:, 0]) - np.min(outermost_group_coords[:, 0])
                ca1_group = vcb_y_res['ca1'] if vcb_y_res else 0

                if s_group < 3 * ca1_group:
                    print(f"  Y方向群组检核: 间距 s={s_group:.2f} < 3*ca1={3 * ca1_group:.2f} => 需进行群组检核")
                    vcbg_y_res = anchor_shear_check.calculate_group_shear_breakout_Vcbg(
                        direction_y, PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params, all_bolt_coords)
                    if vcbg_y_res:
                        phi_Vcbg_y = vcbg_y_res['phi_Vcbg']
                        dc_ratio_vcbg_y = abs(VY_APPLIED) / phi_Vcbg_y if phi_Vcbg_y > 0 else float('inf')
                        print(
                            f"    群组 D/C Ratio = {dc_ratio_vcbg_y:.3f} => {'PASS' if dc_ratio_vcbg_y <= 1.0 else 'FAIL'}")

            # --- [新增] 检核 D3: 混凝土撬破强度 (Vcp) ---
            print("\n--- [檢核 D3] 混凝土撬破強度 (Vcp) ---")

            # 撬破强度与剪力方向无关，但与锚栓位置 (影响Ncb) 有关。
            # 我们同样只检核最不利的角落锚栓。
            abs_coords = np.abs(analysis_results['bolt_coords'])
            corner_anchor_idx = np.argmax(np.sum(abs_coords, axis=1))
            corner_anchor_coord = analysis_results['bolt_coords'][corner_anchor_idx]
            print(f"  (将针对最不利的角落锚栓 #{corner_anchor_idx + 1} 进行检核)")

            vcp_res = anchor_shear_check.calculate_single_anchor_pryout_Vcp(
                corner_anchor_coord, PEDESTAL_PARAMS, ANCHOR_PARAMS, bolt_params
            )

            if vcp_res:
                phi_Vcp = vcp_res['phi_Vcp']
                # 撬破检核使用总剪力
                Vua_total_per_bolt = V_total / analysis_results['num_bolts']
                dc_ratio_vcp = Vua_total_per_bolt / phi_Vcp if phi_Vcp > 0 else float('inf')
                print(f"  撬破强度检核: D/C = {dc_ratio_vcp:.3f} => {'PASS' if dc_ratio_vcp <= 1.0 else 'FAIL'}")

            # 混凝土撬破 Vcpg
            vcpg_res = anchor_shear_check.calculate_group_pryout_Vcpg(
                analysis_results, PEDESTAL_PARAMS, ANCHOR_PARAMS)
            if vcpg_res:
                phi_Vcpg = vcpg_res['phi_Vcpg']
                dc_ratio = abs(VX_APPLIED) / phi_Vcpg if phi_Vcpg > 0 else float('inf')
                print(f"  撬破 (Vcpg) D/C = {dc_ratio:.3f} => {'PASS' if dc_ratio <= 1.0 else 'FAIL'}")

        else:
            print("\n--- 無施加剪力，跳過錨栓剪力檢核 ---")

    else:
        print("\n--- 主程式未收到分析結果，无法进行后续检核 ---")

    print("\n--- 主程式執行完畢 ---")

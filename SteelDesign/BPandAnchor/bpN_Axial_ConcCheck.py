# 檔案名稱: bpN_Axial_ConcCheck.py (最終修正版 - 精確處理所有 A2 案例)
import numpy as np
from .bpN_utils import safe_dc_ratio


def calculate_bearing_capacity(plate_params, pedestal_params, fc_psi, phi_c=0.65):
    """
    纯容量计算器，已升级，可精确计算所有组合下（含偏心）的 A2 面积。
    """
    # --- A. 提取所需參數 ---
    plate_shape = plate_params.get('shape')
    plate_N = plate_params.get('N', 0)
    plate_B = plate_params.get('B', 0)
    plate_R = plate_params.get('outer_radius', 0)
    e_x = plate_params.get('e_x', 0.0)
    e_y = plate_params.get('e_y', 0.0)

    pedestal_shape = pedestal_params.get('shape')
    pedestal_N = pedestal_params.get('N', 0)
    pedestal_B = pedestal_params.get('B', 0)
    pedestal_D = pedestal_params.get('D', 0)
    fc_ksi = fc_psi / 1000.0

    print(f"\n  計算標稱強度 (Bn):")

    # --- B. 計算 A1 (承載面積) ---
    A1 = 0
    if plate_shape == 'rectangle':
        A1 = plate_N * plate_B
    elif plate_shape == 'circle':
        A1 = np.pi * plate_R ** 2
    elif plate_shape == 'octagon':
        A1 = 2 * np.sqrt(2) * plate_R ** 2

    print(f"    - 承載面積 (A1): {A1:.2f} in^2")
    print(f"    - 基礎版偏心 (e_x, e_y): ({e_x:.2f}, {e_y:.2f}) in")

    # --- C. [核心修正] 計算 A2 (支承面有效面積)，完整考慮偏心 ---
    A2 = A1  # 預設 A2 等於 A1 (無圍束效應)

    if pedestal_shape == 'rectangle':
        ped_half_N, ped_half_B = pedestal_N / 2.0, pedestal_B / 2.0

        if plate_shape == 'rectangle':
            print("    - 檢核案例: 矩形版 on 矩形墩 (有偏心)")
            plate_top_y, plate_bot_y = e_y + plate_N / 2.0, e_y - plate_N / 2.0
            plate_right_x, plate_left_x = e_x + plate_B / 2.0, e_x - plate_B / 2.0

            if (plate_top_y <= ped_half_N and plate_bot_y >= -ped_half_N and
                    plate_right_x <= ped_half_B and plate_left_x >= -ped_half_B):
                m = min(ped_half_N - plate_top_y, plate_bot_y - (-ped_half_N))
                n = min(ped_half_B - plate_right_x, plate_left_x - (-ped_half_B))

                if plate_B > 1e-9 and plate_N > 1e-9:
                    A2_option1 = (plate_B + 2 * m * (plate_B / plate_N)) * (plate_N + 2 * m)
                    A2_option2 = (plate_B + 2 * n) * (plate_N + 2 * n * (plate_N / plate_B))
                    A2 = min(A2_option1, A2_option2)
        else:  # 圓形/八邊形版 on 矩形墩
            print("    - 檢核案例: 圓形/八邊形版 on 矩形墩 (有偏心)")
            # A2 是與 A1 (圓形) 幾何相似且能被矩形墩柱包含的最大圓形。
            # 其直徑受限於墩柱的短邊以及基礎版的偏心。

            # 1. 計算基礎版圓心 (考慮偏心)
            plate_center_x, plate_center_y = e_x, e_y

            # 2. 計算基礎版圓心到墩柱四個邊界的距離
            dist_to_top = ped_half_N - plate_center_y
            dist_to_bottom = plate_center_y - (-ped_half_N)
            dist_to_right = ped_half_B - plate_center_x
            dist_to_left = plate_center_x - (-ped_half_B)

            # 3. 找出最小的距離，這就是 A2 的最大可能半徑
            max_radius_A2 = min(dist_to_top, dist_to_bottom, dist_to_right, dist_to_left)

            # 4. 確保基礎版本身在墩柱內，且 A2 半徑不小於 A1 半徑
            if max_radius_A2 >= plate_R * np.cos(np.pi / 8):  # 比较内切圆半径
                # 将 A2 的内切圆半径 max_radius_A2 转换回外接圆半径来计算面积
                cos_22_5 = 0.9238795325112867  # cos(pi/8)
                A2_outer_radius = max_radius_A2 / cos_22_5
                A2 = 2 * np.sqrt(2) * (A2_outer_radius ** 2)
            else:
                # 如果基礎版已超出墩柱邊界，則無圍束效應
                A2 = A1

    elif pedestal_shape == 'circle':
        pedestal_radius = pedestal_D / 2.0

        if plate_shape == 'rectangle':
            print("    - 檢核案例: 矩形版 on 圓形墩 (有偏心)")
            if plate_B > 1e-9:
                k = plate_N / plate_B
                a = (1 + k ** 2) / 4.0
                b = abs(e_x) + k * abs(e_y)
                c = e_x ** 2 + e_y ** 2 - pedestal_radius ** 2
                discriminant = b ** 2 - 4 * a * c

                if discriminant >= 0:
                    B_prime = (-b + np.sqrt(discriminant)) / (2 * a)
                    N_prime = k * B_prime
                    A2 = B_prime * N_prime
                else:
                    A2 = A1
        else:  # 圓形或八邊形版 on 圓形墩
                dist_center = np.sqrt(e_x ** 2 + e_y ** 2)
                # 檢查 A1 是否完全在墩柱內
                # 對於八邊形，用外接圓半徑 R 檢查
                if dist_center + plate_R <= pedestal_radius:
                    # 如果完全在內，A2 是與 A1 幾何相似的最大形狀
                    if plate_shape == 'circle':
                        print("    - 檢核案例: 圓形版 on 圓形墩 (有偏心)")
                        # A2 是整個墩柱面積
                        A2 = np.pi * (pedestal_radius ** 2)

                    elif plate_shape == 'octagon':
                        print("    - 檢核案例: 八邊形版 on 圓形墩 (有偏心)")
                        # 【核心修正】A2 是內接於墩柱圓的最大八邊形
                        # 其外接圓半徑就是墩柱的半徑
                        A2_outer_radius = pedestal_radius
                        A2 = 2 * np.sqrt(2) * (A2_outer_radius ** 2)
                else:
                    # 如果基礎版已超出墩柱邊界，則無圍束效應
                    A2 = A1

    print(f"    - 支承面有效面積 (A2): {A2:.2f} in^2")

    # --- D. 計算圍束效應並計算強度 ---
    confinement_factor = 1.0
    if A1 > 1e-9 and A2 > A1:
        confinement_factor = min(np.sqrt(A2 / A1), 2.0)

    print(f"    - 圍束效應係數 sqrt(A2/A1) = {confinement_factor:.2f} (上限為 2.0)")

    Bn = confinement_factor * (0.85 * fc_ksi * A1)
    phi_Bn = phi_c * Bn

    print(f"    - 標稱承載強度 (Bn): {Bn:.2f} kips")
    print(f"    - 設計承載強度 (ΦBn): {phi_Bn:.2f} kips")

    return {
        "phi_Bn": phi_Bn, "Bn": Bn, "phi_c": phi_c, "A1": A1, "A2": A2,
        "fc_ksi": fc_ksi, "confinement_factor": confinement_factor
    }


# [核心新增] 將常數移到檔案開頭
IN_TO_CM = 2.54
KIP_TO_TF = 0.453592
KSI_TO_KGF_CM2 = 70.307
PSI_TO_KGF_CM2 = 0.070307

def perform_bearing_check(analysis_results, pedestal_params, fc_psi, phi_c=0.65, unit_system='imperial'):
    """
    执行完整的混凝土承压强度检核。
    此版本已修正圓形基礎版的參數傳遞問題。
    """
    print("\n--- 2. 開始執行混凝土承壓檢核模組 ---")

    Bu_kips = analysis_results['concrete_force_Bu']

    plate_params_imperial = {
        'shape': analysis_results.get('plate_shape'),
        'e_x': analysis_results.get('plate_params', {}).get('e_x', 0.0),
        'e_y': analysis_results.get('plate_params', {}).get('e_y', 0.0)
    }

    if plate_params_imperial['shape'] == 'rectangle':
        plate_params_imperial['N'] = analysis_results.get('plate_N')
        plate_params_imperial['B'] = analysis_results.get('plate_B')
    else:
        diameter = analysis_results.get('plate_B', 0.0)
        plate_params_imperial['outer_radius'] = diameter / 2.0

    capacity_results_imperial = calculate_bearing_capacity(plate_params_imperial, pedestal_params, fc_psi, phi_c)

    phi_Bn_kips = capacity_results_imperial['phi_Bn']
    dc_ratio = safe_dc_ratio(Bu_kips, phi_Bn_kips)

    final_results = {
        **capacity_results_imperial,
        "Bu": Bu_kips,
        "dc_ratio": dc_ratio,
        "result": "PASS" if dc_ratio is not None and dc_ratio <= 1.0 else "FAIL",

        # 附加 MKS 單位的值，供報告書使用
        "Bu_mks": Bu_kips * KIP_TO_TF,
        "phi_Bn_mks": phi_Bn_kips * KIP_TO_TF,
        "Bn_mks": capacity_results_imperial['Bn'] * KIP_TO_TF,
        "A1_mks": capacity_results_imperial['A1'] * (IN_TO_CM ** 2),
        "A2_mks": capacity_results_imperial['A2'] * (IN_TO_CM ** 2),
        "fc_mks": (capacity_results_imperial['fc_ksi'] * 1000) / (1 / PSI_TO_KGF_CM2),  # 修正: 這裡應該是 fc_psi
        "f_pu_max_mks": analysis_results.get('max_pressure', 0) * KSI_TO_KGF_CM2,
    }

    # [次要修正] 修正 fc_mks 的計算來源
    # fc_psi 才是原始的 psi 單位值
    fc_psi_original = analysis_results.get('materials', {}).get('fc_psi', fc_psi)
    final_results["fc_mks"] = fc_psi_original * PSI_TO_KGF_CM2

    return final_results
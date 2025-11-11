import numpy as np
from scipy.spatial.distance import pdist
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.geometry import Polygon
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import base64
from .bpN_utils import safe_dc_ratio

KGF_TO_KIPS = 0.00220462
KIP_TO_TF = 0.453592
IN_TO_CM = 2.54
IN2_TO_CM2 = IN_TO_CM * IN_TO_CM
KSI_TO_KGF_CM2 = 70.307
PSI_TO_KGF_CM2 = 0.070307


def calculate_steel_strength_Nsa(bolt_params, anchor_params):
    """
    [計算器] 依规范 17.6.1 計算单根锚栓的钢材设计强度 (ΦNsa)。
    (v2.0 - 新增回傳 MKS 單位)
    """
    fya_ksi = anchor_params['fya_ksi']
    futa_ksi = anchor_params['futa_ksi']
    phi_st = anchor_params.get('phi_st', 0.75)

    da = bolt_params['diameter']
    nt = bolt_params['threads_per_inch']

    Ase_N_in2 = (np.pi / 4.0) * (da - 0.9743 / nt) ** 2 if nt > 0 else np.pi / 4.0 * da ** 2
    futa_eff_ksi = min(futa_ksi, 1.9 * fya_ksi, 125.0)
    Nsa_kips = Ase_N_in2 * futa_eff_ksi
    phi_Nsa_kips = phi_st * Nsa_kips
    print(f"\n  --- 錨栓抗拉強度 (Nsa) ---")
    print(f"    - 標稱強度 (Nsa): {Nsa_kips:.2f} kips, 設計強度 (ΦNsa): {phi_Nsa_kips:.2f} kips")

    return {
        "phi_Nsa": phi_Nsa_kips,
        "Nsa": Nsa_kips,
        "phi_st": phi_st,
        "Ase_N": Ase_N_in2,
        "futa_eff": futa_eff_ksi,
        # --- [核心新增] MKS 單位 ---
        "phi_Nsa_mks": phi_Nsa_kips * KIP_TO_TF,
        "Nsa_mks": Nsa_kips * KIP_TO_TF,
        "Ase_N_mks": Ase_N_in2 * IN2_TO_CM2,
        "futa_eff_mks": futa_eff_ksi * KSI_TO_KGF_CM2,
    }


def calculate_pullout_strength_Npn(analysis_results, anchor_params):
    """
    [計算器] 依规范 17.6.3 計算 "单根" 錨栓的拔出设计强度 (ΦNpn)。
    (v2.0 - 新增回傳 MKS 單位)
    """
    bolt_params = analysis_results['bolt_params_for_check']
    anchor_type = anchor_params['anchor_type']
    anchor_structural_type = anchor_params.get('anchor_structural_type')

    fc_psi = anchor_params['fc_psi']
    is_cracked = anchor_params.get('is_cracked', True)
    phi_pn = anchor_params.get('phi_pn', 0.70)

    Np_kips = 0.0
    Abrg_in2 = bolt_params.get('Abrg_in2')
    eh_in = bolt_params.get('eh_in')
    da_in = bolt_params.get('diameter')

    if anchor_type == 'cast-in':
        if anchor_structural_type == 'headed':
            if Abrg_in2:
                Np_kips = (8 * Abrg_in2 * fc_psi) / 1000.0
        elif anchor_structural_type == 'hooked':
            if da_in and eh_in:
                Np_kips = (0.9 * fc_psi * eh_in * da_in) / 1000.0
    else:
        Np_kips = anchor_params.get('Np_test_kips', 0.0)

    psi_c_p = 1.0 if is_cracked else 1.4
    Npn_kips = psi_c_p * Np_kips
    phi_Npn_kips = phi_pn * Npn_kips

    print(f"\n  --- 錨栓拔出強度 (Npn) ---")
    print(f"    - 標稱強度 (Npn): {Npn_kips:.2f} kips, 設計強度 (ΦNpn): {phi_Npn_kips:.2f} kips")

    return {
        "phi_Npn": phi_Npn_kips,
        "Npn": Npn_kips,
        "phi_pn": phi_pn,
        "psi_c_p": psi_c_p,
        "Np_kips": Np_kips,  # <--- [核心修正] 將 'Np' 修改為 'Np_kips'
        "Abrg_in2": Abrg_in2,
        "fc_psi": fc_psi,
        'eh_in': eh_in,
        "da": da_in,
        "is_cracked": is_cracked,
        "anchor_structural_type": anchor_structural_type,
        # --- MKS 單位 ---
        "phi_Npn_mks": phi_Npn_kips * KIP_TO_TF,
        "Npn_mks": Npn_kips * KIP_TO_TF,
        "Np_mks": Np_kips * KIP_TO_TF,
        "Abrg_mks": Abrg_in2 * IN2_TO_CM2 if Abrg_in2 else None,
        "fc_mks": fc_psi * PSI_TO_KGF_CM2,
        "eh_mks": eh_in * IN_TO_CM if eh_in else None,
        "da_mks": da_in * IN_TO_CM if da_in else None,
    }


def calculate_single_anchor_breakout_Ncb(anchor_coord, pedestal_params, anchor_params, all_bolt_coords=None,
                                         generate_plot=False):
    # --- A. 提取參數 ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    h_ef_orig = anchor_params['h_ef']  # 可能是 cm 或 in
    fc_orig = anchor_params['fc_psi']  # 可能是 kgf/cm2 或 psi
    anchor_type = anchor_params['anchor_type']
    is_headed = anchor_params.get('is_headed', False)
    x, y = anchor_coord
    is_cracked = anchor_params.get('is_cracked', True)
    has_supplementary_reinf = anchor_params.get('has_supplementary_reinf', False)
    lambda_a = anchor_params.get('lambda_a')

    if has_supplementary_reinf:
        phi_cb = 0.75
    else:
        phi_cb = 0.70

    # [核心修改] 新增更詳細的 print 語句來驗證
    print(f"\n  --- 單根拉破強度 (Ncb) 計算流程 (錨栓 at ({x:.2f},{y:.2f})) ---")
    print(f"    - 單位系統 (Unit System): {unit_system}")
    if unit_system == 'mks':
        print(f"    - 接收到的參數 (MKS): h_ef={h_ef_orig:.2f} cm, fc'={fc_orig:.2f} kgf/cm²")
        print(f"    - 接收到的墩柱尺寸 (MKS): {pedestal_params}")
    else:
        print(f"    - 接收到的參數 (Imperial): h_ef={h_ef_orig:.2f} in, fc'={fc_orig:.2f} psi")
        print(f"    - 接收到的墩柱尺寸 (Imperial): {pedestal_params}")

    # --- B. 計算基本拉破強度 (Nb) (ACI 17.6.2.2) ---
    if unit_system == 'imperial':
        use_special_formula = (anchor_type == 'cast-in') and is_headed and (11.0 <= h_ef_orig <= 25.0)
        k_c = 17
        if use_special_formula:
            # 使用 ACI Eq. (17.6.2.2.3)
            Nb_lb = 16.0 * lambda_a * np.sqrt(fc_orig) * h_ef_orig ** (5 / 3)
        else:
            # 使用 ACI Eq. (17.6.2.2.1)
            if anchor_type == 'cast-in':
                k_c = 24
            Nb_lb = k_c * lambda_a * np.sqrt(fc_orig) * h_ef_orig ** 1.5
        Nb = Nb_lb / 1000.0
        print(f"    - 基本拉破強度 (Nb): {Nb:.2f} kips (基於 hef={h_ef_orig:.2f} in)")
    else:
        use_special_formula = (anchor_type == 'cast-in') and is_headed and (28.0 <= h_ef_orig <= 63.5)
        k_c = 7
        if use_special_formula:
            Nb_kgf = 5.8 * lambda_a * np.sqrt(fc_orig) * h_ef_orig ** (5 / 3)
        else:
            if anchor_type == 'cast-in':
                k_c = 10
            Nb_kgf = k_c * lambda_a * np.sqrt(fc_orig) * h_ef_orig ** 1.5
        Nb = Nb_kgf / 1000
        print(f"    - 基本拉破強度 (Nb): {Nb_kgf:.2f} tf (基於 hef={h_ef_orig:.2f} cm)")

    # 根據墩柱形狀建立邊界並計算 ca_min
    pedestal_shape = pedestal_params.get('shape')
    pedestal_poly = None
    if pedestal_shape == 'rectangle':
        pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
        half_B, half_N = pedestal_B / 2.0, pedestal_N / 2.0
        pedestal_poly = Polygon([(-half_B, -half_N), (half_B, -half_N), (half_B, half_N), (-half_B, half_N)])
        ca_min = min(half_N - y, y - (-half_N), half_B - x, x - (-half_B))
    elif pedestal_shape == 'circle':
        pedestal_D = pedestal_params.get('D', 0)
        R = pedestal_D / 2.0
        pedestal_poly = Point(0, 0).buffer(R, resolution=64)

        # [核心修正] 依據您的描述，重新計算 ca_min
        # 檢查錨栓是否在圓內
        if x ** 2 + y ** 2 > R ** 2:
            ca_min = -1  # 錨栓在圓外，邊距為負
        else:
            # 計算 Y 方向上下邊距
            y_boundary_dist = np.sqrt(R ** 2 - x ** 2)
            ca_top = y_boundary_dist - y
            ca_bottom = y - (-y_boundary_dist)

            # 計算 X 方向左右邊距
            x_boundary_dist = np.sqrt(R ** 2 - y ** 2)
            ca_right = x_boundary_dist - x
            ca_left = x - (-x_boundary_dist)

            # 從四個方向的邊距中取最小值
            ca_min = min(ca_top, ca_bottom, ca_right, ca_left)
    else:
        return None  # 不支援的形狀

    # --- C. 計算投影面積 (ANc 和 ANco) 及邊距 (ca_min) ---

    critical_edge_dist = 1.5 * h_ef_orig
    A_Nco = 9 * h_ef_orig ** 2

    # C.1 建立以錨栓 (x,y) 為中心的理想破壞正方形
    breakout_square_poly = Polygon([
        (x - critical_edge_dist, y - critical_edge_dist), (x + critical_edge_dist, y - critical_edge_dist),
        (x + critical_edge_dist, y + critical_edge_dist), (x - critical_edge_dist, y + critical_edge_dist)
    ])

    # C.3 計算兩個形狀的交集面積，即為實際投影面積 ANc
    A_Nc_poly = breakout_square_poly.intersection(pedestal_poly)
    A_Nc = A_Nc_poly.area

    if unit_system == 'imperial':
        print(f"    - 投影面積 ANc/ANco: {A_Nc:.2f} in^2 / {A_Nco:.2f} in^2 (使用幾何交集法)")
        print(f"    - 最小邊距 ca_min: {ca_min:.2f} in")
    else:
        print(f"    - 投影面積 ANc/ANco: {A_Nc:.2f} cm^2 / {A_Nco:.2f} cm^2 (使用幾何交集法)")
        print(f"    - 最小邊距 ca_min: {ca_min:.2f} cm")

    # --- D. 計算修正係數 ---
    # D.1 邊距修正 Ψ_ed,N (ACI 17.6.2.4)
    is_deep_enough = 0
    psi_ed_N = 1.0
    if ca_min < critical_edge_dist:
        is_deep_enough = 1
        psi_ed_N = 0.7 + 0.3 * (ca_min / critical_edge_dist)

    # E.2 開裂修正 Ψ_c,N (ACI 17.6.2.5)
    if not is_cracked:
        psi_c_N = 1.25  # 無開裂
    else:  # 開裂情況
        psi_c_N = 1.0
        # 規範註解：對於 cast-in headed anchor，Ψc,N = 1.0
        # 為求通用性，這裡保留判斷，但對您的情況結果都是 1.0
        if anchor_type == 'post-installed' and not has_supplementary_reinf:
            psi_c_N = 0.75  # 對於後置錨栓無補強的情況

    # E.3 劈裂修正 Ψ_cp,N (ACI 17.6.2.6)
    # 這個係數主要用於後置錨栓(post-installed)。對於預埋式擴頭錨栓(cast-in headed)，此破壞模式通常不控制。
    # 因此，對於您的情況，Ψcp,N = 1.0。
    if anchor_type == 'cast-in':
        psi_cp_N = 1.0
    else:  # 後置錨栓的邏輯
        if ca_min >= 2.0 * h_ef_orig:
            psi_cp_N = 1.0
        else:
            # 這裡需要更複雜的計算，例如 ca_c 和 k_cal
            # 為簡化起見，我們先假設它不控制 (即為 1.0)
            # 完整實作需要從前端獲取更多安裝資訊
            psi_cp_N = 1.0
            print("    - 警告: 對於後置錨栓，Ψcp,N 的計算已被簡化。")

    print(f"    - 修正係數: Ψed,N={psi_ed_N:.3f}, Ψc,N={psi_c_N:.2f}, Ψcp,N={psi_cp_N:.2f}")

    # --- F. 計算標稱強度 (Ncb) ---
    Ncb = (A_Nc / A_Nco) * psi_ed_N * psi_c_N * psi_cp_N * Nb if A_Nco > 0 else 0
    phi_Ncb = phi_cb * Ncb

    print(f"    - 標稱強度 (Ncb): {Ncb:.2f} kips, 設計強度 (ΦNcb): {phi_Ncb:.2f} kips")

    # [核心新增] 繪圖邏輯
    plot_base64 = None
    if generate_plot:
        fig, ax = plt.subplots(figsize=(8, 8))
        unit_label = 'cm' if unit_system == 'mks' else 'in'

        # 1. 繪製墩柱輪廓
        if pedestal_poly:
            ped_x, ped_y = pedestal_poly.exterior.xy
            ax.fill(ped_x, ped_y, color='#E9ECEF', ec='#adb5bd', lw=1.5, label='Pedestal')

        # 2. [核心修正] 繪製被墩柱裁切後的理論破壞面積
        #    我們只繪製 breakout_square_poly 和 pedestal_poly 的 "邊界" 交集
        clipped_theoretical_poly = breakout_square_poly.intersection(pedestal_poly)
        if not clipped_theoretical_poly.is_empty:
            # 如果交集是一個多邊形(Polygon)
            if clipped_theoretical_poly.geom_type == 'Polygon':
                ctp_x, ctp_y = clipped_theoretical_poly.exterior.xy
                ax.plot(ctp_x, ctp_y, color='#457b9d', linestyle='--', lw=2, label='Theoretical Area Boundary')
            # 如果交集是多個多邊形(MultiPolygon)，分別繪製
            elif clipped_theoretical_poly.geom_type == 'MultiPolygon':
                for i, poly in enumerate(clipped_theoretical_poly.geoms):
                    ctp_x, ctp_y = poly.exterior.xy
                    # 只為第一個多邊形添加圖例標籤
                    ax.plot(ctp_x, ctp_y, color='#457b9d', linestyle='--', lw=2,
                            label='Theoretical Area Boundary' if i == 0 else "")

        # 3. 繪製實際破壞面積 (ANc) - 邏輯不變，因為 ANc 本身就是交集結果
        if not A_Nc_poly.is_empty:
            anc_x, anc_y = A_Nc_poly.exterior.xy
            ax.fill(anc_x, anc_y, color=(230/255, 57/255, 70/255, 0.4), ec='#e63946', lw=2, label=f'Actual Area (A_Nc)')

        # 4. 繪製所有錨栓
        if all_bolt_coords is not None and len(all_bolt_coords) > 0:
            all_bolts_np = np.array(all_bolt_coords)
            ax.plot(all_bolts_np[:, 0], all_bolts_np[:, 1], 'o', color='gray', markersize=8, label='Other Anchors')

        # 5. 突顯被檢核的錨栓
        ax.plot(x, y, '*', color='#fca311', markersize=15, markeredgecolor='black', label='Critical Anchor')

        # 6. 圖表設定
        ax.set_aspect('equal', 'box')
        ax.grid(True, linestyle=':', linewidth=0.5)
        ax.set_title(f'Concrete Breakout Area ($A_{{Nc}}$) for Single Anchor', fontsize=14)
        ax.set_xlabel(f'X-axis ({unit_label})')
        ax.set_ylabel(f'Y-axis ({unit_label})')
        ax.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

    return {
        # 主要結果 (英制)
        "phi_Ncb": phi_Ncb,
        "Ncb": Ncb,
        "is_deep_enough": is_deep_enough,
        # 報告書公式所需參數
        "unit_system": unit_system,
        "use_special_formula": use_special_formula,
        "k_c": k_c,
        "lambda_a": lambda_a,
        "is_cracked": is_cracked,
        "anchor_type": anchor_type,
        "psi_ed_N": psi_ed_N,
        "psi_c_N": psi_c_N,
        "psi_cp_N": psi_cp_N,
        "phi_cb": phi_cb,

        # 英制單位的值
        "Nb_imp": Nb,
        "h_ef_imp": h_ef_orig,
        "ca_min_imp": ca_min,
        "fc_imp": fc_orig if unit_system == 'imperial' else fc_orig / PSI_TO_KGF_CM2,
        "A_Nc_imp": A_Nc,
        "A_Nco_imp": A_Nco,

        # MKS 單位的值
        "Nb_mks": Nb,
        "h_ef_mks": h_ef_orig,
        "ca_min_mks": ca_min,
        "fc_mks": fc_orig,
        "A_Nc_mks": A_Nc,
        "A_Nco_mks": A_Nco,

        "plot_base64": plot_base64,  # [核心新增]
    }


def calculate_group_breakout_Ncbg(analysis_results, pedestal_params, anchor_params, generate_plot=False):
    # --- A. 提取参数 ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    bolt_forces = np.array(analysis_results['bolt_forces'])
    bolt_coords = np.array(analysis_results['bolt_coords'])
    h_ef_orig = anchor_params['h_ef']
    fc_orig = anchor_params['fc_psi']
    anchor_type = anchor_params['anchor_type']
    is_headed = anchor_params.get('is_headed', False)
    is_cracked = anchor_params.get('is_cracked', True)
    has_supplementary_reinf = anchor_params.get('has_supplementary_reinf', False)
    lambda_a = anchor_params.get('lambda_a')

    if has_supplementary_reinf:
        phi_cb = 0.75
    else:
        phi_cb = 0.70

    # --- B. 识别受拉锚栓群 ---
    tension_indices = np.where(bolt_forces > 0.001)[0]
    if len(tension_indices) == 0:
        return None
    tension_coords = bolt_coords[tension_indices]
    tension_forces = bolt_forces[tension_indices]

    print(f"\n  --- 群組拉破強度 (Ncbg) 計算流程 ---")
    print(f"    - 受拉錨栓數: {len(tension_coords)}")

    # --- C. [核心修改] 根據您的描述，重新計算群組邊距 (ca_min, ca_max) ---
    pedestal_shape = pedestal_params.get('shape')
    all_anchors_cas = []  # 存储每根锚栓的四个方向边距

    if pedestal_shape == 'rectangle':
        pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
        half_B, half_N = pedestal_B / 2.0, pedestal_N / 2.0
        pedestal_polygon = Polygon([(-half_B, -half_N), (half_B, -half_N), (half_B, half_N), (-half_B, half_N)])
        for x, y in tension_coords:
            ca_top = half_N - y
            ca_bottom = y - (-half_N)
            ca_right = half_B - x
            ca_left = x - (-half_B)
            all_anchors_cas.append({'top': ca_top, 'bottom': ca_bottom, 'left': ca_left, 'right': ca_right})

    elif pedestal_shape == 'circle':
        pedestal_D = pedestal_params.get('D', 0)
        R = pedestal_D / 2.0
        pedestal_polygon = Point(0, 0).buffer(R, resolution=64)

        # 遍歷每一根受拉錨栓
        for x, y in tension_coords:
            if x ** 2 + y ** 2 > R ** 2: continue  # 忽略在圆外的锚栓
            # Y方向边距
            y_boundary_dist = np.sqrt(R ** 2 - x ** 2)
            ca_top = y_boundary_dist - y
            ca_bottom = y - (-y_boundary_dist)
            # X方向边距
            x_boundary_dist = np.sqrt(R ** 2 - y ** 2)
            ca_right = x_boundary_dist - x
            ca_left = x - (-x_boundary_dist)

            all_anchors_cas.append({'top': ca_top, 'bottom': ca_bottom, 'left': ca_left, 'right': ca_right})

    if not all_anchors_cas:  # 如果所有锚栓都在墩柱外
        return None

    # 从所有锚栓的边距中找出群组的四个方向边距
    group_ca_top = min(anchor['top'] for anchor in all_anchors_cas)
    group_ca_bottom = min(anchor['bottom'] for anchor in all_anchors_cas)
    group_ca_left = min(anchor['left'] for anchor in all_anchors_cas)
    group_ca_right = min(anchor['right'] for anchor in all_anchors_cas)

    group_edge_distances = [group_ca_top, group_ca_bottom, group_ca_left, group_ca_right]
    ca_min = min(group_edge_distances)
    ca_max = max(group_edge_distances)
    max_spacing = np.max(pdist(tension_coords)) if len(tension_coords) > 1 else 0

    if unit_system == "mks":
        print(f"    - 群組最小/最大邊距: {ca_min:.2f} cm / {ca_max:.2f} cm")
        print(f"    - 群組最大間距: {max_spacing:.2f} cm")
    else:
        print(f"    - 群組最小/最大邊距: {ca_min:.2f} in / {ca_max:.2f} in")
        print(f"    - 群組最大間距: {max_spacing:.2f} in")

    # --- D. 修正 hef (ACI 17.6.2.1.2) ---
    h_ef_used = h_ef_orig
    critical_dist_orig = 1.5 * h_ef_orig
    num_small_edges = sum(1 for dist in group_edge_distances if dist < critical_dist_orig)

    if num_small_edges >= 3:
        h_ef_mod = 1
        h_ef_used = max(ca_max / 1.5, max_spacing / 3.0)

    # --- E. 計算基本拉破強度 Nb ---
    if unit_system == 'imperial':
        use_special_formula = (anchor_type == 'cast-in') and is_headed and (11.0 <= h_ef_used <= 25.0)
    else:
        use_special_formula = (anchor_type == 'cast-in') and is_headed and (28.0 <= h_ef_used <= 63.5)

    if unit_system == 'imperial':
        k_c = 17
        if use_special_formula:
            # 使用 ACI Eq. (17.6.2.2.3)
            Nb_lb = 16.0 * lambda_a * np.sqrt(fc_orig) * h_ef_used ** (5 / 3)
        else:
            # 使用 ACI Eq. (17.6.2.2.1)
            if anchor_type == 'cast-in':
                k_c = 24
            Nb_lb = k_c * lambda_a * np.sqrt(fc_orig) * h_ef_used ** 1.5
        Nb = Nb_lb / 1000.0
        print(f"    - 基本拉破強度 (Nb): {Nb:.2f} kips (基於 hef={h_ef_used:.2f} in)")

    else:
        k_c = 7
        if use_special_formula:
            # 使用 ACI Eq. (17.6.2.2.3)
            Nb_kgf = 5.8 * lambda_a * np.sqrt(fc_orig) * h_ef_used ** (5 / 3)
        else:
            if anchor_type == 'cast-in':
                k_c = 10
            Nb_kgf = k_c * lambda_a * np.sqrt(fc_orig) * h_ef_used ** 1.5
        Nb = Nb_kgf / 1000.0
        print(f"    - 基本拉破強度 (Nb): {Nb:.2f} kips (基於 hef={h_ef_used:.2f} in)")

    # --- F. 計算 ANc 和 ANco ---
    critical_edge_dist_mod = 1.5 * h_ef_used
    A_Nco = 9 * h_ef_used ** 2

    anchor_squares = [Polygon([(c[0] - critical_edge_dist_mod, c[1] - critical_edge_dist_mod),
                               (c[0] + critical_edge_dist_mod, c[1] - critical_edge_dist_mod),
                               (c[0] + critical_edge_dist_mod, c[1] + critical_edge_dist_mod),
                               (c[0] - critical_edge_dist_mod, c[1] + critical_edge_dist_mod)]) for c in tension_coords]

    union_of_squares = unary_union(anchor_squares) if anchor_squares else Polygon()
    A_Nc = union_of_squares.intersection(pedestal_polygon).area
    print(f"    - 投影面積 ANc/ANco: {A_Nc:.2f} in^2 / {A_Nco:.2f} in^2")

    # --- G. 計算修正系数 ---
    # G.1 偏心修正 Ψ_ec,N (ACI 17.6.2.3)
    total_tension_force = np.sum(tension_forces)
    geom_centroid_x = np.mean(tension_coords[:, 0])
    geom_centroid_y = np.mean(tension_coords[:, 1])
    force_cg_x = np.sum(
        tension_forces * tension_coords[:, 0]) / total_tension_force if total_tension_force > 0 else geom_centroid_x
    force_cg_y = np.sum(
        tension_forces * tension_coords[:, 1]) / total_tension_force if total_tension_force > 0 else geom_centroid_y
    ecc_x = abs(force_cg_x - geom_centroid_x)
    ecc_y = abs(force_cg_y - geom_centroid_y)
    psi_ec_x = 1.0 / (1 + (2 * ecc_x / (3 * h_ef_used))) if h_ef_used > 0 else 1.0
    psi_ec_y = 1.0 / (1 + (2 * ecc_y / (3 * h_ef_used))) if h_ef_used > 0 else 1.0
    psi_ec_N = psi_ec_x * psi_ec_y

    psi_ed_N = 0.7 + 0.3 * (ca_min / critical_edge_dist_mod) if ca_min < critical_edge_dist_mod else 1.0
    # G.3 開裂修正 Ψ_c,N (邏輯與單根錨栓相同)
    if not is_cracked:
        psi_c_N = 1.25
    else:
        psi_c_N = 1.0
        if anchor_type == 'post-installed' and not has_supplementary_reinf:
            psi_c_N = 0.75

    # G.4 劈裂修正 Ψ_cp,N (邏輯與單根錨栓相同)
    if anchor_type == 'cast-in':
        psi_cp_N = 1.0
    else:
        # 對於群組，只要群組的 ca_min 滿足條件即可
        if ca_min >= 3.0 * h_ef_used:
            psi_cp_N = 1.0
        else:
            psi_cp_N = 1.0  # 簡化處理
            print("    - 警告: 對於後置錨栓群組，Ψcp,N 的計算已被簡化。")

    print(f"    - 修正係數: Ψec,N={psi_ec_N:.3f}, Ψed,N={psi_ed_N:.3f}, Ψc,N={psi_c_N:.2f}, Ψcp,N={psi_cp_N:.2f}")

    # --- H. 計算 Ncbg ---
    Ncbg = (A_Nc / A_Nco) * psi_ec_N * psi_ed_N * psi_c_N * psi_cp_N * Nb if A_Nco > 0 else 0
    phi_Ncbg = phi_cb * Ncbg

    print(f"    - 標稱強度 (Ncbg): {Ncbg:.2f} kips, 設計強度 (ΦNcbg): {phi_Ncbg:.2f} kips")

    # [核心新增] 繪圖邏輯
    plot_base64 = None
    if generate_plot:
        fig, ax = plt.subplots(figsize=(8, 8))
        unit_label = 'cm' if unit_system == 'mks' else 'in'

        # 1. 繪製墩柱
        if pedestal_polygon:
            ped_x, ped_y = pedestal_polygon.exterior.xy
            ax.fill(ped_x, ped_y, color='#E9ECEF', ec='#adb5bd', lw=1.5, label='Pedestal')

        # 2. 繪製理論破壞面積 (union_of_squares) 的邊界
        clipped_theoretical_poly = union_of_squares.intersection(pedestal_polygon)
        if not clipped_theoretical_poly.is_empty:
            if clipped_theoretical_poly.geom_type == 'Polygon':
                ctp_x, ctp_y = clipped_theoretical_poly.exterior.xy
                ax.plot(ctp_x, ctp_y, color='#457b9d', linestyle='--', lw=2, label='Theoretical Area Boundary')
            elif clipped_theoretical_poly.geom_type == 'MultiPolygon':
                for i, poly in enumerate(clipped_theoretical_poly.geoms):
                    ctp_x, ctp_y = poly.exterior.xy
                    ax.plot(ctp_x, ctp_y, color='#457b9d', linestyle='--', lw=2,
                            label='Theoretical Area Boundary' if i == 0 else "")

        # 3. 繪製實際破壞面積 (ANc)
        A_Nc_poly = clipped_theoretical_poly  # For groups, clipped theoretical area is the actual area
        if not A_Nc_poly.is_empty:
            if A_Nc_poly.geom_type == 'Polygon':
                anc_x, anc_y = A_Nc_poly.exterior.xy
                ax.fill(anc_x, anc_y, color=(230 / 255, 57 / 255, 70 / 255, 0.4), ec='#e63946', lw=2,
                        label=f'Actual Area (A_Ncg)')
            elif A_Nc_poly.geom_type == 'MultiPolygon':
                for i, poly in enumerate(A_Nc_poly.geoms):
                    anc_x, anc_y = poly.exterior.xy
                    ax.fill(anc_x, anc_y, color=(230 / 255, 57 / 255, 70 / 255, 0.4), ec='#e63946', lw=2,
                            label=f'Actual Area (A_Ncg)' if i == 0 else "")

        # 4. 繪製所有錨栓，並突顯受拉錨栓
        all_bolts_np = np.array(bolt_coords)
        is_tension = np.isin(np.arange(len(all_bolts_np)), tension_indices)
        ax.plot(all_bolts_np[~is_tension, 0], all_bolts_np[~is_tension, 1], 'o', color='gray', markersize=8,
                label='Other Anchors')
        ax.plot(all_bolts_np[is_tension, 0], all_bolts_np[is_tension, 1], '*', color='#fca311', markersize=15,
                markeredgecolor='black', label='Tension Anchors in Group')

        # 5. 圖表設定
        ax.set_aspect('equal', 'box')
        ax.grid(True, linestyle=':', linewidth=0.5)
        ax.set_title(f'Concrete Breakout Area ($A_{{Ncg}}$) for Anchor Group', fontsize=14)
        ax.set_xlabel(f'X-axis ({unit_label})')
        ax.set_ylabel(f'Y-axis ({unit_label})')
        ax.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

    return {
        "phi_Ncbg": phi_Ncbg,
        "Ncbg": Ncbg,
        "ca_min": ca_min,
        "ca_max": ca_max,
        "max_spacing": max_spacing,
        "is_headed": is_headed,
        "lambda_a":lambda_a,
        "anchor_type": anchor_type,
        "is_cracked": is_cracked,
        "Nb": Nb,
        "hef_used": h_ef_used,  # h_ef 是修正後的英制值
        "A_Nc": A_Nc,
        "A_Nco": A_Nco,
        "psi_ec_N": psi_ec_N,
        "psi_ed_N": psi_ed_N,
        "psi_c_N": psi_c_N,
        "psi_cp_N": psi_cp_N,
        'use_special_formula': use_special_formula,
        'k_c': k_c,
        "phi_cb": phi_cb,
        "ecc_x": ecc_x,
        "ecc_y": ecc_y,
        'num_small_edges': num_small_edges,
        'fc_orig': fc_orig,  # 可能是 psi 或 kgf/cm2
        "plot_base64": plot_base64  # [核心新增]
    }


def calculate_side_face_blowout_for_single_anchor(anchor_coord, pedestal_params, anchor_params, bolt_params, all_bolt_coords=None, generate_plot=False):
    """[計算器] 依规范 17.6.4.1 計算 "单根" 扩头锚栓的侧向胀破设计强度 (ΦNsb)。"""
    unit_system = anchor_params.get('unit_system', 'imperial')
    lambda_a = anchor_params.get('lambda_a')

    if not (anchor_params.get('anchor_type') == 'cast-in' and anchor_params.get('is_headed')):
        return None

    Abrg = anchor_params.get('Abrg')
    if Abrg is None:
        return None

    h_ef = anchor_params['h_ef']
    x, y = anchor_coord
    pedestal_shape = pedestal_params.get('shape')

    # [核心修正] 根據您的描述，重新計算 ca1 和 ca2
    ca1, ca2 = 0, 0
    ca1_direction = None
    ca2_direction = None  # <-- 確保變數在函式頂層被初始化為 None
    ca1_direction_info = "N/A"  # 用於日誌記錄

    if pedestal_shape == 'rectangle':
        pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
        half_B, half_N = pedestal_B / 2.0, pedestal_N / 2.0

        ca_top = half_N - y
        ca_bottom = y - (-half_N)
        ca_right = half_B - x
        ca_left = x - (-half_B)

        all_cas = {'top': ca_top, 'bottom': ca_bottom, 'left': ca_left, 'right': ca_right}

        if any(v < 0 for v in all_cas.values()):
            print(f"    - 錨栓 @ ({x:.2f}, {y:.2f}) 位於墩柱外，不適用側向脹破檢核。")
            return None

        ca1_direction = min(all_cas, key=all_cas.get)
        ca1 = all_cas[ca1_direction]
        ca1_direction_info = f"矩形，方向: {ca1_direction}"

        # [核心修正] 精確判斷 ca2 及其方向
        if ca1_direction in ['top', 'bottom']:
            if ca_left < ca_right:
                ca2 = ca_left
                ca2_direction = 'left'
            else:
                ca2 = ca_right
                ca2_direction = 'right'
        else: # 'left' or 'right'
            if ca_bottom < ca_top:
                ca2 = ca_bottom
                ca2_direction = 'bottom'
            else:
                ca2 = ca_top
                ca2_direction = 'top'

    elif pedestal_shape == 'circle':
        pedestal_D = pedestal_params.get('D', 0)
        R = pedestal_D / 2.0

        # 計算錨栓到圓心的距離 d
        dist_from_center = np.sqrt(x ** 2 + y ** 2)
        if dist_from_center > R:
            return None
        ca1 = R - dist_from_center
        ca2 = np.sqrt(R ** 2 - dist_from_center ** 2) if R ** 2 >= dist_from_center ** 2 else 0

        # [核心修正] 為圓形墩柱賦值 ca1_direction 和 ca2_direction
        ca1_direction = 'radial'
        ca2_direction = 'tangential' # 給一個唯一的標記，以便繪圖邏輯可以識別

    is_deep_enough = 1
    if h_ef <= 2.5 * ca1:
        is_deep_enough = 0
        print(f"    - 錨栓 @ ({x}, {y})，符合 hef={h_ef:.2f} <= 2.5*ca1={2.5 * ca1:.2f}，不需考量側向脹破。")

    fc_orig = anchor_params['fc_psi']

    if unit_system == "imperial":
        Nsb_base = (160 * ca1 * np.sqrt(Abrg) * lambda_a * np.sqrt(fc_orig)) / 1000.0
    else:
        Nsb_base = (42.44 * ca1 * np.sqrt(Abrg) * lambda_a * np.sqrt(fc_orig)) / 1000.0

    modification_factor = 1.0
    if ca2 < 3 * ca1:
        modification_factor = (1 + ca2 / ca1) / 4.0

    Nsb = Nsb_base * modification_factor

    has_supplementary_reinf = anchor_params.get('has_supplementary_reinf', False)
    if has_supplementary_reinf:
        phi_sfb = 0.75
    else:
        phi_sfb = 0.70

    print(f"    - 錨栓 @ ({x}, {y}), 標稱強度 (Nsb): {Nsb:.2f} kips, 設計強度 (ΦNsb): {phi_sfb * Nsb:.2f} kips")

    Nsb_base_kips = Nsb_base
    if unit_system == 'mks':
        Nsb_base_kips = Nsb_base / KIP_TO_TF  # 將 tf 轉回 kips

    # [核心新增] 繪圖邏輯
    plot_base64 = None
    if generate_plot:
        fig, ax = plt.subplots(figsize=(8, 8))
        unit_label = 'cm' if unit_system == 'mks' else 'in'

        # 1. 繪製墩柱輪廓
        pedestal_shape = pedestal_params.get('shape')
        pedestal_poly = None
        if pedestal_shape == 'rectangle':
            pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
            pedestal_poly = Polygon([(-pedestal_B / 2, -pedestal_N / 2), (pedestal_B / 2, -pedestal_N / 2),
                                     (pedestal_B / 2, pedestal_N / 2), (-pedestal_B / 2, pedestal_N / 2)])
        elif pedestal_shape == 'circle':
            pedestal_D = pedestal_params.get('D', 0)
            pedestal_poly = Point(0, 0).buffer(pedestal_D / 2.0, resolution=64)

        if pedestal_poly:
            ped_x, ped_y = pedestal_poly.exterior.xy
            ax.fill(ped_x, ped_y, color='#E9ECEF', ec='#adb5bd', lw=1.5, label='Pedestal')

        # 2. 繪製所有錨栓
        if all_bolt_coords is not None and len(all_bolt_coords) > 0:
            all_bolts_np = np.array(all_bolt_coords)
            ax.plot(all_bolts_np[:, 0], all_bolts_np[:, 1], 'o', color='gray', markersize=8, label='Other Anchors')

        # 3. 突顯被檢核的錨栓
        ax.plot(anchor_coord[0], anchor_coord[1], '*', color='#fca311', markersize=15, markeredgecolor='black',
                label='Critical Anchor')

        # 4. [核心重構] 根據 ca1_direction 繪製 ca1 和 ca2 標示線
        ax_xlim = ax.get_xlim()
        ax_ylim = ax.get_ylim()
        offset_x = (ax_xlim[1] - ax_xlim[0]) * 0.02
        offset_y = (ax_ylim[1] - ax_ylim[0]) * 0.02

        if ca1_direction:
            # --- 繪製 ca1 ---
            if ca1_direction == 'right':
                ax.plot([x, x + ca1], [y, y], 'r-', lw=2.5)
                ax.text(x + ca1 / 2, y + offset_y, f'ca1={ca1:.2f}', color='red', ha='center', va='bottom')
            elif ca1_direction == 'left':
                ax.plot([x, x - ca1], [y, y], 'r-', lw=2.5)
                ax.text(x - ca1 / 2, y + offset_y, f'ca1={ca1:.2f}', color='red', ha='center', va='bottom')
            elif ca1_direction == 'top':
                ax.plot([x, x], [y, y + ca1], 'r-', lw=2.5)
                ax.text(x + offset_x, y + ca1 / 2, f'ca1={ca1:.2f}', color='red', va='center', ha='left', rotation=90)
            elif ca1_direction == 'bottom':
                ax.plot([x, x], [y, y - ca1], 'r-', lw=2.5)
                ax.text(x + offset_x, y - ca1 / 2, f'ca1={ca1:.2f}', color='red', va='center', ha='left', rotation=90)

            # --- 繪製 ca2 ---
            if ca2_direction == 'top':
                ax.plot([x, x], [y, y + ca2], 'b-', lw=2.5)
                ax.text(x - offset_x, y + ca2 / 2, f'ca2={ca2:.2f}', color='blue', va='center', ha='right', rotation=90)
            elif ca2_direction == 'bottom':
                ax.plot([x, x], [y, y - ca2], 'b-', lw=2.5)
                ax.text(x - offset_x, y - ca2 / 2, f'ca2={ca2:.2f}', color='blue', va='center', ha='right', rotation=90)
            elif ca2_direction == 'right':
                ax.plot([x, x + ca2], [y, y], 'b-', lw=2.5)
                ax.text(x + ca2 / 2, y - offset_y, f'ca2={ca2:.2f}', color='blue', ha='center', va='top')
            elif ca2_direction == 'left':
                ax.plot([x, x - ca2], [y, y], 'b-', lw=2.5)
                ax.text(x - ca2 / 2, y - offset_y, f'ca2={ca2:.2f}', color='blue', ha='center', va='top')

            # 圓形墩柱的簡化標示 (如果 ca2_direction 為 None)
            if ca1_direction == 'radial':
                # 繪製徑向的 ca1
                if dist_from_center > 1e-6:  # 避免除以零
                    unit_vec_radial = np.array([x, y]) / dist_from_center
                    end_point_ca1 = np.array([x, y]) + unit_vec_radial * ca1
                    ax.plot([x, end_point_ca1[0]], [y, end_point_ca1[1]], 'r-', lw=2.5)
                    text_pos_ca1 = np.array([x, y]) + unit_vec_radial * ca1 * 0.5
                    ax.text(text_pos_ca1[0], text_pos_ca1[1] + offset_y, f'ca1={ca1:.2f}', color='red', ha='center')

                # 繪製切向的 ca2
                if ca2 > 1e-6:
                    unit_vec_tangential = np.array([-y, x]) / dist_from_center if dist_from_center > 1e-6 else np.array(
                        [0, 1])
                    end_point_ca2 = np.array([x, y]) + unit_vec_tangential * ca2
                    ax.plot([x, end_point_ca2[0]], [y, end_point_ca2[1]], 'b-', lw=2.5)
                    text_pos_ca2 = np.array([x, y]) + unit_vec_tangential * ca2 * 0.5
                    ax.text(text_pos_ca2[0], text_pos_ca2[1], f'ca2={ca2:.2f}', color='blue', ha='center')

        # 5. 圖表設定
        ax.set_aspect('equal', 'box')
        ax.grid(True, linestyle=':', linewidth=0.5)
        ax.set_title(f'Side-Face Blowout Geometry ($N_{{sb}}$)', fontsize=14)
        ax.set_xlabel(f'X-axis ({unit_label})')
        ax.set_ylabel(f'Y-axis ({unit_label})')
        ax.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

    return {
        "phi_Nsb": phi_sfb * Nsb,
        "Nsb": Nsb,
        "ca1": ca1,
        "ca2": ca2,
        "h_ef": h_ef,
        "Abrg": Abrg,
        "lambda_a": lambda_a,
        "fc_orig": fc_orig,
        "Nsb_base": Nsb_base,
        "phi_sfb": phi_sfb,
        "modification_factor": modification_factor,
        "is_modified": ca2 < 3 * ca1,
        "is_deep_enough": is_deep_enough,
        "Nsb_base_kips": Nsb_base_kips,
        "plot_base64": plot_base64,
        "ca1_direction": ca1_direction
    }


def calculate_side_face_blowout_for_group(analysis_results, pedestal_params, anchor_params, bolt_params, generate_plot=False):
    """
    [计算器] v1.3 - 回傳參與群組檢核的錨栓索引號碼。
    """
    # --- 1. 初始檢查與參數提取 ---
    if not (anchor_params.get('anchor_type') == 'cast-in' and anchor_params.get('is_headed')):
        return {'result': 'N/A', 'message': '側向脹破僅適用於預埋式擴頭錨栓。'}

    bolt_forces = np.array(analysis_results['bolt_forces'])
    bolt_coords = np.array(analysis_results['bolt_coords'])
    tension_indices = np.where(bolt_forces > 0.001)[0]
    num_tension_bolts = len(tension_indices)
    bolt_layout_mode = anchor_params['bolt_layout_mode']
    pedestal_shape = pedestal_params.get('shape')

    if num_tension_bolts <= 1:
        return {'result': 'N/A', 'message': '受拉錨栓數不足，無需進行群組檢核。'}

    tension_coords = bolt_coords[tension_indices]

    # --- 2. 找出所有受拉錨栓的 ca1，並確定最不利的邊緣 ---
    # 這個迴圈的目的是找出是否有任何錨栓適用 Nsb 檢核，並找到全局最小的 ca1
    all_ca1_results = []
    nsb_applicable_at_all = False
    for i in tension_indices:
        anchor_coord = tuple(bolt_coords[i])
        # 我們呼叫單根檢核函式，但只為了獲取它的幾何計算結果
        single_res = calculate_side_face_blowout_for_single_anchor(anchor_coord, pedestal_params, anchor_params,
                                                                   bolt_params)
        if single_res and single_res.get('ca1') is not None:
            nsb_applicable_at_all = True

            # 在這裡同時儲存 Nsb_base 和 Nsb_base_kips
            all_ca1_results.append({
                'index': i,
                'coord': anchor_coord,
                'ca1': single_res['ca1'],
                'ca1_direction': single_res.get('ca1_direction'),  # <--- 修正點：將方向也存進來
                'Nsb_base': single_res.get('Nsb_base', 0),
                'Nsb_base_kips': single_res.get('Nsb_base_kips', 0)
            })

    if not nsb_applicable_at_all:
        return {'result': 'N/A', 'message': '所有受拉錨栓均不滿足側向脹破的幾何條件 (h_ef <= 2.5ca1)。'}

    if not all_ca1_results:
        return {'result': 'N/A', 'message': '無法計算任何受拉錨栓的邊距。'}

    # --- 3. 識別位於最不利邊緣上的錨栓群組 ---
    base_anchor_info = min(all_ca1_results, key=lambda x: x['ca1'])
    group_ca1 = base_anchor_info['ca1']
    # [核心修正] 獲取群組的最不利方向
    group_ca1_direction = base_anchor_info.get('ca1_direction')

    # 找出所有 ca1 值與最小 ca1 值非常接近的錨栓，它們被視為在同一個最不利邊緣上
    edge_group_anchors = [res for res in all_ca1_results if abs(res['ca1'] - group_ca1) < 0.1]

    if len(edge_group_anchors) <= 1:
        return {'result': 'N/A', 'message': '最不利邊緣上僅有一根受拉錨栓，無需群組檢核。'}

    # [核心新增] 計算群組的 ca2
    group_ca2 = 0
    group_ca2_direction = None
    pedestal_shape = pedestal_params.get('shape')

    if pedestal_shape == 'rectangle':
        pedestal_B = pedestal_params.get('B', 0)
        pedestal_N = pedestal_params.get('N', 0)
        group_coords_np = np.array([res['coord'] for res in edge_group_anchors])

        if group_ca1_direction in ['top', 'bottom']:
            # ca1 是垂直的，ca2 是水平的
            ca_left_vals = [pedestal_B / 2 - c[0] for c in group_coords_np]
            ca_right_vals = [c[0] - (-pedestal_B / 2) for c in group_coords_np]
            if min(ca_left_vals) < min(ca_right_vals):
                group_ca2 = min(ca_left_vals)
                group_ca2_direction = 'left'
            else:
                group_ca2 = min(ca_right_vals)
                group_ca2_direction = 'right'
        elif group_ca1_direction in ['left', 'right']:
            # ca1 是水平的，ca2 是垂直的
            ca_top_vals = [pedestal_N / 2 - c[1] for c in group_coords_np]
            ca_bottom_vals = [c[1] - (-pedestal_N / 2) for c in group_coords_np]
            if min(ca_top_vals) < min(ca_bottom_vals):
                group_ca2 = min(ca_top_vals)
                group_ca2_direction = 'top'
            else:
                group_ca2 = min(ca_bottom_vals)
                group_ca2_direction = 'bottom'

    # --- 4. [核心修正] 計算相鄰錨栓最大間距 s ---
    edge_group_coords = np.array([anchor['coord'] for anchor in edge_group_anchors])
    # [核心新增] 收集參與群組計算的錨栓索引
    edge_group_global_indices = [anchor['index'] for anchor in edge_group_anchors]

    # [核心修正] 根據 ca1 方向計算 s
    s_calculated = 0.0
    if len(edge_group_coords) > 1:
        if group_ca1_direction in ['top', 'bottom']:
            # ca1 是垂直方向，s 就是水平方向的距離
            s_calculated = np.max(edge_group_coords[:, 0]) - np.min(edge_group_coords[:, 0])
        elif group_ca1_direction in ['left', 'right']:
            # ca1 是水平方向，s 就是垂直方向的距離
            s_calculated = np.max(edge_group_coords[:, 1]) - np.min(edge_group_coords[:, 1])
        else: # Radial for circle, simplified
            s_calculated = np.max(pdist(edge_group_coords))

    special = 0
    if bolt_layout_mode == 'grid' and pedestal_shape == 'circle':
        special = 1
        s_calculated = 0.0

    critical_spacing_nsbg = 6 * group_ca1

    h_ef = anchor_params['h_ef']
    cal_type = 1
    if h_ef < 2.5 * group_ca1:
        cal_type = 2
    elif h_ef > 2.5 * group_ca1 and s_calculated > 6.0 * group_ca1:
        cal_type = 3

    # --- 5. 執行 Nsbg 計算 ---
    # 使用 ca1 最小的那根錨栓的 Nsb_base 作為計算基礎
    base_anchor_nsb_for_group_kips = base_anchor_info.get('Nsb_base_kips', 0)

    Nsbg_kips = (1 + s_calculated / (
            6 * group_ca1)) * base_anchor_nsb_for_group_kips if group_ca1 > 0 else base_anchor_nsb_for_group_kips

    

    has_supplementary_reinf = anchor_params.get('has_supplementary_reinf', False)
    phi_sfb = 0.75 if has_supplementary_reinf else 0.70
    phi_Nsbg_kips = phi_sfb * Nsbg_kips

    # --- 6. 計算群組需求力並進行檢核 ---
    total_group_force_kips = np.sum(bolt_forces[edge_group_global_indices])

    # [核心新增] 繪圖邏輯
    plot_base64 = None
    if generate_plot:
        fig, ax = plt.subplots(figsize=(8, 8))
        unit_label = 'cm' if anchor_params.get('unit_system') == 'mks' else 'in'

        # 1. 繪製墩柱
        pedestal_shape = pedestal_params.get('shape')
        pedestal_poly = None
        if pedestal_shape == 'rectangle':
            pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
            pedestal_poly = Polygon([(-pedestal_B / 2, -pedestal_N / 2), (pedestal_B / 2, -pedestal_N / 2),
                                     (pedestal_B / 2, pedestal_N / 2), (-pedestal_B / 2, pedestal_N / 2)])
        elif pedestal_shape == 'circle':
            pedestal_D = pedestal_params.get('D', 0)
            pedestal_poly = Point(0, 0).buffer(pedestal_D / 2.0, resolution=64)

        if pedestal_poly:
            ped_x, ped_y = pedestal_poly.exterior.xy
            ax.fill(ped_x, ped_y, color='#E9ECEF', ec='#adb5bd', lw=1.5, label='Pedestal')

        # 2. 繪製所有錨栓
        all_bolts_np = np.array(analysis_results['bolt_coords'])
        ax.plot(all_bolts_np[:, 0], all_bolts_np[:, 1], 'o', color='gray', markersize=8, label='All Anchors')

        # 3. 突顯參與群組檢核的錨栓
        group_coords_np = np.array([res['coord'] for res in edge_group_anchors])
        ax.plot(group_coords_np[:, 0], group_coords_np[:, 1], '*', color='#fca311', markersize=15,
                markeredgecolor='black', label='Anchors in Group')

        # 4. [核心重構] 根據 group_ca1_direction 繪製 s 和 ca1 標示線
        if group_ca1_direction and len(group_coords_np) > 0:
            ax_xlim = ax.get_xlim()
            ax_ylim = ax.get_ylim()
            offset_x = (ax_xlim[1] - ax_xlim[0]) * 0.03
            offset_y = (ax_ylim[1] - ax_ylim[0]) * 0.03

            # 找出群組的幾何中心和邊界
            min_x, max_x = np.min(group_coords_np[:, 0]), np.max(group_coords_np[:, 0])
            min_y, max_y = np.min(group_coords_np[:, 1]), np.max(group_coords_np[:, 1])
            center_x, center_y = np.mean(group_coords_np, axis=0)

            if group_ca1_direction == 'left':
                # ca1 往左, s 垂直
                ax.plot([min_x, min_x - group_ca1], [center_y, center_y], 'b-', lw=2.5)
                ax.text(min_x - group_ca1/2, center_y + offset_y, f'ca1 = {group_ca1:.2f}', color='blue', ha='center', va='bottom')
                ax.plot([min_x + offset_x, min_x + offset_x], [min_y, max_y], 'r-', lw=2.5)
                ax.text(min_x + offset_x*1.5, center_y, f's = {s_calculated:.2f}', color='red', ha='left', va='center', rotation=90)
            elif group_ca1_direction == 'right':
                # ca1 往右, s 垂直
                ax.plot([max_x, max_x + group_ca1], [center_y, center_y], 'b-', lw=2.5)
                ax.text(max_x + group_ca1/2, center_y + offset_y, f'ca1 = {group_ca1:.2f}', color='blue', ha='center', va='bottom')
                ax.plot([max_x - offset_x, max_x - offset_x], [min_y, max_y], 'r-', lw=2.5)
                ax.text(max_x - offset_x*1.5, center_y, f's = {s_calculated:.2f}', color='red', ha='right', va='center', rotation=90)
            elif group_ca1_direction == 'top':
                # ca1 往上, s 水平
                ax.plot([center_x, center_x], [max_y, max_y + group_ca1], 'b-', lw=2.5)
                ax.text(center_x - offset_x, max_y + group_ca1/2, f'ca1 = {group_ca1:.2f}', color='blue', ha='right', va='center', rotation=90)
                ax.plot([min_x, max_x], [max_y - offset_y, max_y - offset_y], 'r-', lw=2.5)
                ax.text(center_x, max_y - offset_y*1.5, f's = {s_calculated:.2f}', color='red', ha='center', va='top')
            elif group_ca1_direction == 'bottom':
                # ca1 往下, s 水平
                ax.plot([center_x, center_x], [min_y, min_y - group_ca1], 'b-', lw=2.5)
                ax.text(center_x - offset_x, min_y - group_ca1/2, f'ca1 = {group_ca1:.2f}', color='blue', ha='right', va='center', rotation=90)
                ax.plot([min_x, max_x], [min_y + offset_y, min_y + offset_y], 'r-', lw=2.5)
                ax.text(center_x, min_y + offset_y*1.5, f's = {s_calculated:.2f}', color='red', ha='center', va='bottom')

            # [核心新增] 繪製 ca2 的邏輯 (顏色與 ca1/s 區分，例如用綠色)
            if group_ca2_direction == 'top':
                ax.plot([center_x, center_x], [max_y, max_y + group_ca2], 'g-', lw=2.5)
                ax.text(center_x + offset_x, max_y + group_ca2/2, f'ca2 = {group_ca2:.2f}', color='green', ha='left', va='center', rotation=90)
            elif group_ca2_direction == 'bottom':
                ax.plot([center_x, center_x], [min_y, min_y - group_ca2], 'g-', lw=2.5)
                ax.text(center_x + offset_x, min_y - group_ca2/2, f'ca2 = {group_ca2:.2f}', color='green', ha='left', va='center', rotation=90)
            elif group_ca2_direction == 'right':
                ax.plot([max_x, max_x + group_ca2], [center_y, center_y], 'g-', lw=2.5)
                ax.text(max_x + group_ca2/2, center_y - offset_y, f'ca2 = {group_ca2:.2f}', color='green', ha='center', va='top')
            elif group_ca2_direction == 'left':
                ax.plot([min_x, min_x - group_ca2], [center_y, center_y], 'g-', lw=2.5)
                ax.text(min_x - group_ca2/2, center_y - offset_y, f'ca2 = {group_ca2:.2f}', color='green', ha='center', va='top')

        # 5. 圖表設定
        ax.set_aspect('equal', 'box')
        ax.grid(True, linestyle=':', linewidth=0.5)
        ax.set_title(f'Side-Face Blowout Geometry ($N_{{sbg}}$)', fontsize=14)
        ax.set_xlabel(f'X-axis ({unit_label})')
        ax.set_ylabel(f'Y-axis ({unit_label})')
        ax.legend()
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

    # [核心修正] 現在 dc_ratio 的計算絕對是 kips / kips
    dc_ratio = safe_dc_ratio(total_group_force_kips, phi_Nsbg_kips)

    print(f"  --- 群組側向脹破強度 (Nsbg) ---")
    print(f"    - 最不利邊緣 ca1 = {group_ca1:.2f} in, 群組間距 s = {s_calculated:.2f} in")


    unit_system = anchor_params.get('unit_system', 'imperial')
    # [核心修正] 移除在這裡的單位轉換，讓函式總是回傳 kips
    demand_to_return = total_group_force_kips
    capacity_to_return = phi_Nsbg_kips
    Nsbg_to_return = Nsbg_kips
    base_nsb_to_return = base_anchor_nsb_for_group_kips

    return {
        'demand': demand_to_return,  # <--- 永遠是 kips
        'capacity': capacity_to_return,  # <--- 永遠是 kips
        'dc_ratio': dc_ratio,
        'result': 'PASS' if dc_ratio is not None and dc_ratio <= 1.0 else 'FAIL',
        'message': f"檢核由 {len(edge_group_anchors)} 根位於最不利邊緣的錨栓控制 (s={s_calculated:.2f})。",
        'group_ca1': group_ca1,
        "s_calculated": s_calculated,
        'base_anchor_nsb': base_nsb_to_return,  # <--- 永遠是 kips
        'phi_sfb': phi_sfb,
        'Nsbg': Nsbg_to_return,  # <--- 永遠是 kips
        'cal_type': cal_type,
        'h_ef': h_ef,
        'ca1': group_ca1,
        'controlling_anchor_indices': sorted(edge_group_global_indices),
        'special': special,
        'plot_base64': plot_base64
    }

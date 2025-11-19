import numpy as np
import math
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
import pandas as pd

import matplotlib
from matplotlib.ticker import MaxNLocator
from .bpN_svg_utils import SvgPlotter

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import base64

# --- [核心新增] 將常數移到檔案頂部 ---
KIP_TO_TF = 0.453592
IN2_TO_CM2 = 2.54 ** 2
KSI_TO_KGF_CM2 = 70.307


def calculate_steel_strength_Vsa(bolt_params, anchor_params):
    """
    [计算器] 依规范 17.7.1 计算单根锚栓的钢材设计剪力强度 (ΦVsa)。
    """
    # --- A. 提取参数 (英制) ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    futa = anchor_params['futa_ksi']
    fya = anchor_params['fya_ksi']
    phi_sv = anchor_params.get('phi_sv', 0.65)
    has_grout_pad = anchor_params.get('has_grout_pad', False)  # 假設從 anchor_params 傳入
    da = bolt_params['diameter']
    nt = bolt_params.get('threads_per_inch', 1)

    Ase_V = (np.pi / 4.0) * (da - 0.9743 / nt) ** 2
    if unit_system == 'mks':
        da = da * 2.54
        nt = nt / 2.54
        Ase_V = Ase_V * IN2_TO_CM2

    # --- B. 计算 Vsa ---
    if unit_system == 'imperial':
        futa_effective = min(futa, 1.9 * fya, 125.0)
    else:
        futa_effective = min(futa, 1.9 * fya, 8750)

    # 基础的 Vsa (同样采用保守的 0.6 系数)
    Vsa_base = 0.6 * Ase_V * futa_effective
    if unit_system == 'mks':
        Vsa_base = Vsa_base / 1000

    # [核心修正] 施加灌浆垫层折减系数 (规范 17.7.1.2.1)
    Vsa = Vsa_base
    if has_grout_pad:
        Vsa *= 0.80

    # --- C. 计算设计强度并返回 ---
    phi_Vsa = phi_sv * Vsa

    # --- D. 增加详细打印 ---
    print("\n--- [檢核 D1] 鋼材剪力強度 (Vsa) ---")
    print(f"    - 單根錨栓受剪有效面積 Ase,V = {Ase_V:.3f} kips")
    print(f"    - futa = {futa_effective:.3f} kips")
    print(f"    - 基础 Vsa = {Vsa_base:.2f} kips")
    if has_grout_pad:
        print(f"    - 存在灌漿層，Vsa 乘以折减系数 0.80")
    print(f"    - 標稱强度 (Vsa): {Vsa:.2f} kips, 設計强度 (ΦVsa): {phi_Vsa:.2f} kips")

    return {
        "phi_Vsa": phi_Vsa,
        "Vsa": Vsa,
        "phi_sv": phi_sv,
        "Vsa_base": Vsa_base,
        "Ase_V": Ase_V,
        "futa_eff": futa_effective,
        "fya": fya,
        "has_grout_pad": has_grout_pad
    }


def calculate_single_anchor_shear_breakout_Vcb(anchor_coord, shear_direction_vector, pedestal_params, anchor_params,
                                               bolt_params, all_bolt_coords=None, generate_plot=False):
    """
    [计算器] v2.1 - 精確繪製 AVc 破壞錐投影
    """
    # --- A. 提取参数 ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    h_ef = anchor_params['h_ef']
    fc = anchor_params['fc_psi']
    phi_cv = anchor_params.get('phi_cv', 0.70)
    ha = pedestal_params['h']
    da = bolt_params['diameter']
    if unit_system == "mks":
        da = da * 2.54
    is_cracked = anchor_params.get('is_cracked', True)
    reinf_condition = anchor_params.get('reinf_condition_shear', 0)
    lambda_a = anchor_params.get('lambda_a')

    x, y = anchor_coord
    vx, vy = shear_direction_vector

    # --- B. 根據墩柱形狀，計算 ca1, ca2 ---
    pedestal_shape = pedestal_params.get('shape')
    ca1, ca2 = 0, float('inf')
    is_x_dominant = abs(vx) >= abs(vy)

    if pedestal_shape == 'rectangle':
        pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
        half_B, half_N = pedestal_B / 2.0, pedestal_N / 2.0

        if is_x_dominant:  # X方向為主
            ca1 = half_B - x if vx >= 0 else x - (-half_B)
            ca2 = min(half_N - y, y - (-half_N))
        else:  # Y方向為主
            ca1 = half_N - y if vy >= 0 else y - (-half_N)
            ca2 = min(half_B - x, x - (-half_B))

    elif pedestal_shape == 'circle':
        pedestal_D = pedestal_params.get('D', 0)
        R = pedestal_D / 2.0

        if is_x_dominant:  # X方向為主
            # ca1 是沿 X 方向到邊界的距離
            if R ** 2 < y ** 2:
                ca1 = -1  # y 座標在圓外
            else:
                x_boundary = np.sqrt(R ** 2 - y ** 2)
                ca1 = x_boundary - x if vx >= 0 else x - (-x_boundary)

            # ca2 是沿 Y 方向到邊界的距離
            if R ** 2 < x ** 2:
                ca2 = -1  # x 座標在圓外
            else:
                y_boundary = np.sqrt(R ** 2 - x ** 2)
                ca2 = min(y_boundary - y, y - (-y_boundary))
        else:  # Y方向為主
            # ca1 是沿 Y 方向到邊界的距離
            if R ** 2 < x ** 2:
                ca1 = -1
            else:
                y_boundary = np.sqrt(R ** 2 - x ** 2)
                ca1 = y_boundary - y if vy >= 0 else y - (-y_boundary)

            # ca2 是沿 X 方向到邊界的距離
            if R ** 2 < y ** 2:
                ca2 = -1
            else:
                x_boundary = np.sqrt(R ** 2 - y ** 2)
                ca2 = min(x_boundary - x, x - (-x_boundary))
    else:
        return None  # 不支援的形狀

    is_deep_enough = 1
    if ha < 1.5 * ca1:
        is_deep_enough = 0
    # --- C. 计算基本剪破强度 Vb (ACI 17.7.2.2.1) ---
    if ca1 < 1e-9 or ca2 < 0: return None  # 錨栓在邊緣或邊緣外，無強度

    le = min(h_ef, 8 * da)
    Vb_a = (7 * (le / da) ** 0.2 * np.sqrt(da)) * lambda_a * np.sqrt(fc) * ca1 ** 1.5
    Vb_b = 9 * lambda_a * np.sqrt(fc) * ca1 ** 1.5
    Vb = min(Vb_a, Vb_b)
    Vb = Vb / 1000.0

    if unit_system == 'mks':
        Vb_a = (1.86 * (le / da) ** 0.2 * np.sqrt(da)) * lambda_a * np.sqrt(fc) * ca1 ** 1.5
        Vb_b = 3.8 * lambda_a * np.sqrt(fc) * ca1 ** 1.5
        Vb = min(Vb_a, Vb_b)
        Vb = Vb / 1000.0

    # --- D. [核心修正] 依据“较长射线投影”模型，精确计算 AVc ---
    A_Vco = 4.5 * ca1 ** 2
    A_Vc = 0
    shear_angle = math.atan2(vy, vx)
    angle_1, angle_2 = shear_angle + math.radians(55), shear_angle - math.radians(55)

    def get_intersection(origin, direction, pedestal_info):
        ox, oy = origin;
        dx, dy = direction
        if pedestal_info['shape'] == 'circle':
            R = pedestal_info['D'] / 2.0;
            a, b, c = dx ** 2 + dy ** 2, 2 * (ox * dx + oy * dy), ox ** 2 + oy ** 2 - R ** 2
            dsc = b ** 2 - 4 * a * c
            if dsc < 0: return None
            t = ((-b + math.sqrt(dsc)) / (2 * a));
            return (ox + t * dx, oy + t * dy) if t >= -1e-9 else None
        elif pedestal_info['shape'] == 'rectangle':
            B, N = pedestal_info['B'], pedestal_info['N'];
            t_near, t_far = -float('inf'), float('inf')
            for dim_min, dim_max, o, d in [(-B / 2, B / 2, ox, dx), (-N / 2, N / 2, oy, dy)]:
                if abs(d) < 1e-9:
                    if o < dim_min or o > dim_max: return None
                else:
                    t1, t2 = (dim_min - o) / d, (dim_max - o) / d
                    if t1 > t2: t1, t2 = t2, t1
                    t_near, t_far = max(t_near, t1), min(t_far, t2)
            if t_near > t_far or t_far < -1e-9: return None
            return (ox + t_far * dx, oy + t_far * dy)

    P1 = get_intersection((x, y), [math.cos(angle_1), math.sin(angle_1)], pedestal_params)
    P2 = get_intersection((x, y), [math.cos(angle_2), math.sin(angle_2)], pedestal_params)

    if P1 and P2:
        len1 = np.linalg.norm(np.array(P1) - np.array((x, y)))
        len2 = np.linalg.norm(np.array(P2) - np.array((x, y)))
        width_avc = 0
        if math.isclose(len1, len2, rel_tol=1e-4):
            width_avc = np.linalg.norm(np.array(P1) - np.array(P2))
        else:
            P_long = P1 if len1 > len2 else P2
            line_dir = np.array([0, 1] if is_x_dominant else [1, 0])
            P_other_end = get_intersection(P_long, -line_dir, pedestal_params)
            if P_other_end:
                width_avc = np.linalg.norm(np.array(P_long) - np.array(P_other_end))

        depth_avc = min(ha, 1.5 * ca1)
        A_Vc = width_avc * depth_avc

    # --- E. 修正系数 ---
    # ca2 的计算是独立的，用于 psi_ed_V
    is_x_dominant = abs(vx) >= abs(vy)
    ca2 = 0
    if pedestal_shape == 'rectangle':
        pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
        ca2 = min(pedestal_N / 2 - y, y - (-pedestal_N / 2)) if is_x_dominant else min(pedestal_B / 2 - x,
                                                                                       x - (-pedestal_B / 2))
    elif pedestal_shape == 'circle':
        R = pedestal_params.get('D', 0) / 2.0
        if is_x_dominant:
            if R ** 2 >= x ** 2:
                y_boundary = np.sqrt(R ** 2 - x ** 2)
                ca2 = min(y_boundary - y, y - (-y_boundary))
        else:
            if R ** 2 >= y ** 2:
                x_boundary = np.sqrt(R ** 2 - y ** 2)
                ca2 = min(x_boundary - x, x - (-x_boundary))

    # 邊距修正 (psi_ed_V)
    psi_ed_V = 0.7 + 0.3 * (ca2 / (1.5 * ca1)) if ca2 < 1.5 * ca1 and ca1 > 0 else 1.0

    if not is_cracked:
        # (a) 未開裂情況，psi_c_V 固定為 1.4
        psi_c_V = 1.4
    else:
        # (b) 開裂情況，根據輔助鋼筋與縱向主筋條件判斷
        has_supp_reinf = anchor_params.get('has_supplementary_reinf', False)

        if not has_supp_reinf:
            # 情況 1: 沒有設置輔助箍筋
            # 此時需檢查縱向主筋(角隅鋼筋)尺寸
            long_rebar_size_str = anchor_params.get('longitudinal_rebar_size', 'D10')
            long_rebar_size_num = int(''.join(filter(str.isdigit, long_rebar_size_str)))
            if long_rebar_size_num < 13:
                # 縱向主筋 < D13，psi_c_V = 1.0
                psi_c_V = 1.0
            else:
                # 縱向主筋 >= D13，視同有配置鋼筋，psi_c_V = 1.2
                psi_c_V = 1.2
        else:
            # 情況 2: 有設置輔助箍筋
            # 此時需檢查輔助箍筋的尺寸與間距
            supp_rebar_size_str = anchor_params.get('supplementary_rebar_size', 'D10')
            supp_rebar_spacing = anchor_params.get('supplementary_rebar_spacing', float('inf'))
            supp_rebar_size_num = int(''.join(filter(str.isdigit, supp_rebar_size_str)))

            if supp_rebar_size_num < 13:
                # 輔助箍筋 < D13，效果等同於只有縱向主筋的情況
                # (這裡我們保守一點，如果縱向主筋尺寸也未知，則取 1.0，但實際上應該至少有 1.2)
                # 為了邏輯完整，我們再次檢查縱向主筋
                long_rebar_size_str = anchor_params.get('longitudinal_rebar_size', 'D10')
                long_rebar_size_num = int(''.join(filter(str.isdigit, long_rebar_size_str)))
                if long_rebar_size_num < 13:
                    psi_c_V = 1.0
                else:
                    psi_c_V = 1.2
            else:
                # 輔助箍筋尺寸 >= D13
                # 規範 10cm 約等於 4 in
                if supp_rebar_spacing is not None and supp_rebar_spacing <= 4.0:
                    # 情況 3: 輔助箍筋 >= D13 且間距不大於 10cm
                    psi_c_V = 1.4
                else:
                    # 情況 2: 輔助箍筋 >= D13 但間距 > 10cm
                    psi_c_V = 1.2

    psi_h_V = (1.5 * ca1 / ha) ** 0.5 if ha < 1.5 * ca1 else 1.0

    # --- F. 计算标称强度 Vcb ---
    Vcb = (A_Vc / A_Vco) * psi_ed_V * psi_c_V * psi_h_V * Vb if A_Vco > 0 else 0
    phi_Vcb = phi_cv * Vcb

    plot_base64 = None
    if generate_plot:
        plotter = SvgPlotter(width=600, height=600)
        unit_system = anchor_params.get('unit_system', 'imperial')
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
            plotter.add_shapely_polygon(pedestal_poly, fill="#E9ECEF", stroke="#adb5bd", stroke_width=1.5, opacity=1.0)

        # 2. 精確建構並繪製 AVc 破壞區域
        # 这里的 P1, P2, angle_1, angle_2 是前面计算逻辑中已經算好的
        if 'P1' in locals() and P1 and 'P2' in locals() and P2 and pedestal_poly:
            far_dist = max(pedestal_params.get('B', 0), pedestal_params.get('N', 0), pedestal_params.get('D', 0)) * 5
            ray1_end = (anchor_coord[0] + far_dist * math.cos(angle_1), anchor_coord[1] + far_dist * math.sin(angle_1))
            ray2_end = (anchor_coord[0] + far_dist * math.cos(angle_2), anchor_coord[1] + far_dist * math.sin(angle_2))

            theoretical_cone_poly = Polygon([anchor_coord, ray1_end, ray2_end])
            actual_area_poly = theoretical_cone_poly.intersection(pedestal_poly)

            if not actual_area_poly.is_empty:
                # 紅色半透明填充 (AVc)
                plotter.add_shapely_polygon(actual_area_poly, fill="#e63946", stroke="none", opacity=0.4)
                # 藍色虛線邊界
                plotter.add_shapely_polygon(actual_area_poly, fill="none", stroke="#457b9d", stroke_width=2,
                                            stroke_dasharray="5,5", opacity=1.0)

        # 3. 繪製所有錨栓
        if all_bolt_coords is not None and len(all_bolt_coords) > 0:
            for bx, by in all_bolt_coords:
                plotter.add_circle(bx, by, r=3, fill="gray", stroke="none", opacity=0.6)

        # 4. 突顯被檢核的錨栓
        plotter.add_circle(anchor_coord[0], anchor_coord[1], r=4, fill="#fca311", stroke="black", stroke_width=1.5,
                           opacity=1.0)

        # 5. 繪製主剪力方向箭頭
        arrow_len = min(pedestal_params.get('B', 10), pedestal_params.get('N', 10)) * 0.15
        end_x = anchor_coord[0] + vx * arrow_len
        end_y = anchor_coord[1] + vy * arrow_len
        plotter.add_arrow(anchor_coord[0], anchor_coord[1], end_x, end_y, color="black", width=2)

        # # 6. 文字標籤 (可選，簡單標示軸向)
        # plotter.add_text(0, pedestal_params.get('N', 0) / 2 + 5, f"Y ({unit_label})", size=10)
        # plotter.add_text(pedestal_params.get('B', 0) / 2 + 5, 0, f"X ({unit_label})", size=10)

        plot_base64 = plotter.render_to_base64()

    return {
        "phi_Vcb": phi_Vcb, "Vcb": Vcb, "ca1": ca1, "ca2": ca2, "fc": fc,
        "lambda_a": lambda_a,
        "Vb_a": Vb_a, "Vb_b": Vb_b,
        "Vb": Vb, "le": le, "h_ef": h_ef, "da": da, "ha": ha,
        "A_Vc": A_Vc, "A_Vco": A_Vco, "phi_cv": phi_cv,
        "psi_c_V": psi_c_V, "psi_ed_V": psi_ed_V, "psi_h_V": psi_h_V,
        "is_cracked": is_cracked,
        "is_deep_enough": is_deep_enough,
        "has_supplementary_reinf": anchor_params.get('has_supplementary_reinf', False),
        "longitudinal_rebar_size": anchor_params.get('longitudinal_rebar_size'),
        "supplementary_rebar_size": anchor_params.get('supplementary_rebar_size'),
        "supplementary_rebar_spacing": anchor_params.get('supplementary_rebar_spacing'),
        "plot_base64": plot_base64
    }


def calculate_group_shear_breakout_Vcbg(shear_direction_vector, pedestal_params, anchor_params, bolt_params,
                                        all_bolt_coords, bolt_shear_demands, generate_plot=False):
    """
    [计算器] 依规范 17.7.2 计算 "锚栓群" 在 "特定方向" 的混凝土剪破设计强度 (ΦVcbg)。
    此函式已升级，会逐排检核由 "第一排到当前排" 组成的锚栓群强度，并取最小值。
    """
    # --- A. 提取参数 ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    h_ef = anchor_params['h_ef']
    fc = anchor_params['fc_psi']
    phi_cv = anchor_params.get('phi_cv', 0.70)
    ha = pedestal_params['h']
    da = bolt_params['diameter']
    if unit_system == 'mks':
        da = da * 2.54
    is_cracked = anchor_params.get('is_cracked', True)
    reinf_condition = anchor_params.get('reinf_condition_shear', 0)
    lambda_a = anchor_params.get('lambda_a')
    pedestal_shape = pedestal_params.get('shape')

    # --- B. 根据剪力方向，对所有锚栓进行分组和排序 ---
    vx, vy = shear_direction_vector
    # [核心修正] 在 DataFrame 中加入原始索引
    df = pd.DataFrame(all_bolt_coords, columns=['x', 'y'])
    df['original_index'] = df.index

    grouping_axis = 'x' if abs(vx) >= abs(vy) else 'y'
    sort_ascending = (vx > 0) if grouping_axis == 'x' else (vy > 0)
    df_sorted = df.sort_values(by=grouping_axis, ascending=sort_ascending)
    row_ids, unique_coords = pd.factorize(df_sorted[grouping_axis].round(4))
    df_sorted['row_id'] = row_ids

    # 辅助函数：计算射线与边界的交点
    def get_intersection(origin, direction, pedestal_info):
        ox, oy = origin
        dx, dy = direction
        if pedestal_info['shape'] == 'circle':
            R = pedestal_info['D'] / 2.0
            a = dx ** 2 + dy ** 2
            b = 2 * (ox * dx + oy * dy)
            c = ox ** 2 + oy ** 2 - R ** 2
            discriminant = b ** 2 - 4 * a * c
            if discriminant < 0: return None
            t1 = (-b + math.sqrt(discriminant)) / (2 * a)
            t2 = (-b - math.sqrt(discriminant)) / (2 * a)
            t = t1 if t1 >= -1e-9 else (t2 if t2 >= -1e-9 else None)
            if t is None: return None
            return (ox + t * dx, oy + t * dy)
        elif pedestal_info['shape'] == 'rectangle':
            B, N = pedestal_info['B'], pedestal_info['N']
            t_near, t_far = -float('inf'), float('inf')
            if abs(dx) < 1e-9:
                if ox < -B / 2 or ox > B / 2: return None
            else:
                t1, t2 = (-B / 2 - ox) / dx, (B / 2 - ox) / dx
                if t1 > t2: t1, t2 = t2, t1
                t_near, t_far = max(t_near, t1), min(t_far, t2)
            if abs(dy) < 1e-9:
                if oy < -N / 2 or oy > N / 2: return None
            else:
                t1, t2 = (-N / 2 - oy) / dy, (N / 2 - oy) / dy
                if t1 > t2: t1, t2 = t2, t1
                t_near, t_far = max(t_near, t1), min(t_far, t2)
            if t_near > t_far or t_far < -1e-9: return None
            return (ox + t_far * dx, oy + t_far * dy)

    # --- C. 建立墩柱幾何邊界 ---
    pedestal_poly = None
    if pedestal_shape == 'rectangle':
        pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
        pedestal_poly = Polygon([(-pedestal_B / 2, -pedestal_N / 2), (pedestal_B / 2, -pedestal_N / 2),
                                 (pedestal_B / 2, pedestal_N / 2), (-pedestal_B / 2, pedestal_N / 2)])
    elif pedestal_shape == 'circle':
        pedestal_D = pedestal_params.get('D', 0)
        pedestal_poly = Point(0, 0).buffer(pedestal_D / 2.0, resolution=64)

    if not pedestal_poly: return []  # 如果沒有有效的墩柱形狀，則返回空列表

    # --- C. 遍历每一排锚栓，检核 "累加群组" 的强度 ---
    all_combinations_results = []
    shear_demand_map = {tuple(demand['coord']): demand for demand in bolt_shear_demands}

    for i in range(len(unique_coords)):
        # [核心修正] 同時提取座標和原始索引
        current_group_df = df_sorted[df_sorted['row_id'] <= i]
        current_group_coords = current_group_df[['x', 'y']].to_numpy()
        current_group_indices = current_group_df['original_index'].tolist()

        # 1. 计算 ca1, ca2, s_perp
        is_x_dominant = (grouping_axis == 'x')
        outermost_row_coords = df_sorted[df_sorted['row_id'] == i][['x', 'y']].to_numpy()
        ca1_values = [
            calculate_single_anchor_shear_breakout_Vcb(c, shear_direction_vector, pedestal_params, anchor_params,
                                                       bolt_params).get('ca1') for c in outermost_row_coords]
        ca1_values = [v for v in ca1_values if v is not None]
        if not ca1_values: continue
        group_ca1_orig = min(ca1_values)

        ca2_values = [
            calculate_single_anchor_shear_breakout_Vcb(c, shear_direction_vector, pedestal_params, anchor_params,
                                                       bolt_params).get('ca2') for c in current_group_coords]
        ca2_values = [v for v in ca2_values if v is not None]
        group_ca2_min = min(ca2_values) if ca2_values else 0
        group_ca2_max = max(ca2_values) if ca2_values else 0

        s_perp = np.max(current_group_coords[:, 1 if is_x_dominant else 0]) - np.min(
            current_group_coords[:, 1 if is_x_dominant else 0]) if len(current_group_coords) > 1 else 0

        # 2. 修正 ca1
        group_ca1 = group_ca1_orig
        ca1_is_modified = False
        ca1_modification_message = f"ca1 無需修正。"
        if group_ca2_min < 1.5 * group_ca1_orig and ha < 1.5 * group_ca1_orig:
            ca1_is_modified = True
            ca1_limit = max(group_ca2_max / 1.5, ha / 1.5, s_perp / 3.0)
            group_ca1 = min(group_ca1_orig, ca1_limit)
            ca1_modification_message = f"因滿足規範第17.7.2.1.1規定，ca1 由 {group_ca1_orig:.2f} in 修正为 {group_ca1:.2f} in。"

        # 3. 计算 Vb, AVco
        le = min(h_ef, 8 * da)
        Vb1 = (7 * (le / da) ** 0.2 * np.sqrt(da)) * lambda_a * np.sqrt(fc) * group_ca1 ** 1.5
        Vb2 = 9 * lambda_a * np.sqrt(fc) * group_ca1 ** 1.5
        Vb = min(Vb1, Vb2) / 1000

        if unit_system == "mks":
            Vb1 = (1.86 * (le / da) ** 0.2 * np.sqrt(da)) * lambda_a * np.sqrt(fc) * group_ca1 ** 1.5
            Vb2 = 3.8 * lambda_a * np.sqrt(fc) * group_ca1 ** 1.5
            Vb = min(Vb1, Vb2) / 1000

        A_Vco = 4.5 * group_ca1 ** 2

        # 4. 精确计算 AVc
        shear_angle = math.atan2(vy, vx)
        angle_1 = shear_angle + math.radians(55)
        angle_2 = shear_angle - math.radians(55)
        dir1 = np.array([math.cos(angle_1), math.sin(angle_1)])
        dir2 = np.array([math.cos(angle_2), math.sin(angle_2)])

        all_intersection_points = []
        for bolt_coord in current_group_coords:
            p1 = get_intersection(bolt_coord, dir1, pedestal_params)
            p2 = get_intersection(bolt_coord, dir2, pedestal_params)
            if p1: all_intersection_points.append(p1)
            if p2: all_intersection_points.append(p2)

        A_Vc = 0
        if len(all_intersection_points) >= 2:
            points_np = np.array(all_intersection_points)
            min_coord = np.min(points_np[:, 1 if is_x_dominant else 0])
            max_coord = np.max(points_np[:, 1 if is_x_dominant else 0])
            width_avc = max_coord - min_coord
            depth_avc = min(ha, 1.5 * group_ca1)
            A_Vc = width_avc * depth_avc

        # 4. 计算修正系数
        psi_ed_V = 0.7 + 0.3 * (
                group_ca2_min / (1.5 * group_ca1)) if group_ca2_min < 1.5 * group_ca1 and group_ca1 > 0 else 1.0

        if not is_cracked:
            # (a) 未開裂情況
            psi_c_V = 1.4
        else:
            # (b) 開裂情況，根據輔助鋼筋條件判斷
            has_supp_reinf = anchor_params.get('has_supplementary_reinf', False)

            if not is_cracked:
                # (a) 未開裂情況，psi_c_V 固定為 1.4
                psi_c_V = 1.4
            else:
                # (b) 開裂情況，根據輔助鋼筋與縱向主筋條件判斷
                has_supp_reinf = anchor_params.get('has_supplementary_reinf', False)

                if not has_supp_reinf:
                    # 情況 1: 沒有設置輔助箍筋
                    # 此時需檢查縱向主筋(角隅鋼筋)尺寸
                    long_rebar_size_str = anchor_params.get('longitudinal_rebar_size', 'D10')
                    long_rebar_size_num = int(''.join(filter(str.isdigit, long_rebar_size_str)))
                    if long_rebar_size_num < 13:
                        # 縱向主筋 < D13，psi_c_V = 1.0
                        psi_c_V = 1.0
                    else:
                        # 縱向主筋 >= D13，視同有配置鋼筋，psi_c_V = 1.2
                        psi_c_V = 1.2
                else:
                    # 情況 2: 有設置輔助箍筋
                    # 此時需檢查輔助箍筋的尺寸與間距
                    supp_rebar_size_str = anchor_params.get('supplementary_rebar_size', 'D10')
                    supp_rebar_spacing = anchor_params.get('supplementary_rebar_spacing', float('inf'))
                    supp_rebar_size_num = int(''.join(filter(str.isdigit, supp_rebar_size_str)))

                    if supp_rebar_size_num < 13:
                        # 輔助箍筋 < D13，效果等同於只有縱向主筋的情況
                        # (這裡我們保守一點，如果縱向主筋尺寸也未知，則取 1.0，但實際上應該至少有 1.2)
                        # 為了邏輯完整，我們再次檢查縱向主筋
                        long_rebar_size_str = anchor_params.get('longitudinal_rebar_size', 'D10')
                        long_rebar_size_num = int(''.join(filter(str.isdigit, long_rebar_size_str)))
                        if long_rebar_size_num < 13:
                            psi_c_V = 1.0
                        else:
                            psi_c_V = 1.2
                    else:
                        # 輔助箍筋尺寸 >= D13
                        # 規範 10cm 約等於 4 in
                        if supp_rebar_spacing is not None and supp_rebar_spacing <= 4.0:
                            # 情況 3: 輔助箍筋 >= D13 且間距不大於 10cm
                            psi_c_V = 1.4
                        else:
                            # 情況 2: 輔助箍筋 >= D13 但間距 > 10cm
                            psi_c_V = 1.2

        is_deep_enough = 1
        psi_h_V = 1.0
        if ha < 1.5 * group_ca1:
            is_deep_enough = 0
            psi_h_V = (1.5 * group_ca1 / ha) ** 0.5
            if psi_h_V < 1.0:
                psi_h_V = 1.0

        # 計算偏心修正 Ψec,V
        leading_row_coords = df_sorted[df_sorted['row_id'] == 0][['x', 'y']].to_numpy()
        centroid_g = np.mean(leading_row_coords, axis=0)

        total_v_group_vec = np.array([0.0, 0.0])
        moment_about_g = 0.0
        for coord in current_group_coords:
            demand = shear_demand_map.get(tuple(coord))
            if demand:
                force_vec = np.array([demand['v_total_x'], demand['v_total_y']])
                total_v_group_vec += force_vec
                # 力臂向量 r = (coord - centroid_g)
                r_vec = np.array(coord) - centroid_g
                # 二維外積: M = r_x*F_y - r_y*F_x
                moment_about_g += r_vec[0] * force_vec[1] - r_vec[1] * force_vec[0]

        total_v_mag = np.linalg.norm(total_v_group_vec)
        ecc_v = abs(moment_about_g / total_v_mag) if total_v_mag > 1e-9 else 0.0
        psi_ec_V = 1.0 / (1 + ecc_v / (1.5 * group_ca1)) if group_ca1 > 0 else 1.0

        # 5. 计算最终强度
        Vcbg = (A_Vc / A_Vco) * psi_ec_V * psi_ed_V * psi_c_V * psi_h_V * Vb if A_Vco > 0 else 0
        phi_Vcbg = phi_cv * Vcbg

        all_combinations_results.append({
            "rows_included_text": f"前 {i + 1} 排锚栓",
            "num_bolts_in_group": len(current_group_coords),
            "group_coords_list": current_group_coords.tolist(),
            "controlling_anchor_indices": sorted(current_group_indices),  # <--- 新增此行
            "ca1_is_modified": ca1_is_modified,
            "ca1_modification_message": ca1_modification_message,
            "lambda_a": lambda_a,
            "phi_Vcbg": phi_Vcbg,
            "Vcbg": Vcbg,
            "phi_cv": phi_cv,
            "Vb1": Vb1,
            "Vb2": Vb2,
            "Vb": Vb,
            "le": le,
            "h_ef": h_ef,
            "ha": ha,
            "da": da,
            "ca1_used": group_ca1,
            "ca2_used": group_ca2_min,
            "AVc": A_Vc,
            "AVco": A_Vco,
            "fc": fc,
            "psi_c_V": psi_c_V,
            "psi_ed_V": psi_ed_V,
            "is_deep_enough": is_deep_enough,
            "psi_h_V": psi_h_V,
            'ecc_v': ecc_v,
            "psi_ec_V": psi_ec_V,
            'is_cracked': is_cracked,
            "has_supplementary_reinf": anchor_params.get('has_supplementary_reinf', False),
            "longitudinal_rebar_size": anchor_params.get('longitudinal_rebar_size'),
            "supplementary_rebar_size": anchor_params.get('supplementary_rebar_size'),
            "supplementary_rebar_spacing": anchor_params.get('supplementary_rebar_spacing')
        })

    if generate_plot and all_combinations_results:
        critical_res = min(all_combinations_results, key=lambda x: x['phi_Vcbg'])
        group_coords_to_plot = critical_res.get('group_coords_list', [])

        # 準備相關幾何變數
        vx, vy = shear_direction_vector
        shear_angle = math.atan2(vy, vx)
        angle_1 = shear_angle + math.radians(55)
        angle_2 = shear_angle - math.radians(55)

        plotter = SvgPlotter(width=600, height=600)
        unit_system = anchor_params.get('unit_system', 'imperial')
        unit_label = 'cm' if unit_system == 'mks' else 'in'

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
            plotter.add_shapely_polygon(pedestal_poly, fill="#E9ECEF", stroke="#adb5bd", stroke_width=1.5, opacity=1.0)

        # 2. 精確建構並繪製 Vcbg 破壞區域
        all_cones = []
        far_dist = max(pedestal_params.get('B', 0), pedestal_params.get('N', 0), pedestal_params.get('D', 0)) * 5

        for bolt_coord in group_coords_to_plot:
            ray1_end = (bolt_coord[0] + far_dist * math.cos(angle_1), bolt_coord[1] + far_dist * math.sin(angle_1))
            ray2_end = (bolt_coord[0] + far_dist * math.cos(angle_2), bolt_coord[1] + far_dist * math.sin(angle_2))
            all_cones.append(Polygon([bolt_coord, ray1_end, ray2_end]))

        union_of_cones = unary_union(all_cones)
        actual_area_poly = union_of_cones.intersection(pedestal_poly)

        if not actual_area_poly.is_empty:
            # 紅色半透明填充 (AVcg)
            plotter.add_shapely_polygon(actual_area_poly, fill="#e63946", stroke="none", opacity=0.4)
            # 藍色虛線邊界
            plotter.add_shapely_polygon(actual_area_poly, fill="none", stroke="#457b9d", stroke_width=2,
                                        stroke_dasharray="5,5", opacity=1.0)

        # 3. 繪製所有錨栓，並突顯群組錨栓
        # 將 group_coords 轉為 set 以便快速查找
        group_set = set(tuple(c) for c in group_coords_to_plot)

        for coord in all_bolt_coords:
            coord_tuple = tuple(coord)
            if coord_tuple in group_set:
                # 群組錨栓 (金色星號效果用圓形代替或堆疊多邊形)
                plotter.add_circle(coord[0], coord[1], r=4, fill="#fca311", stroke="black", stroke_width=1.5,
                                   opacity=1.0)
            else:
                # 其他錨栓 (灰色)
                plotter.add_circle(coord[0], coord[1], r=3, fill="gray", stroke="none", opacity=0.6)

        critical_res['plot_base64'] = plotter.render_to_base64()

    # if generate_plot and all_combinations_results:
    #     critical_res = min(all_combinations_results, key=lambda x: x['phi_Vcbg'])
    #     group_coords_to_plot = critical_res.get('group_coords_list', [])
    #
    #     fig, ax = plt.subplots(figsize=(8, 8))
    #     unit_system = anchor_params.get('unit_system', 'imperial')
    #     unit_label = 'cm' if unit_system == 'mks' else 'in'
    #
    #     # 1. 繪製墩柱輪廓
    #     pedestal_shape = pedestal_params.get('shape')
    #     pedestal_poly = None
    #     if pedestal_shape == 'rectangle':
    #         pedestal_B, pedestal_N = pedestal_params.get('B', 0), pedestal_params.get('N', 0)
    #         pedestal_poly = Polygon([(-pedestal_B / 2, -pedestal_N / 2), (pedestal_B / 2, -pedestal_N / 2),
    #                                  (pedestal_B / 2, pedestal_N / 2), (-pedestal_B / 2, pedestal_N / 2)])
    #     elif pedestal_shape == 'circle':
    #         pedestal_D = pedestal_params.get('D', 0)
    #         pedestal_poly = Point(0, 0).buffer(pedestal_D / 2.0, resolution=64)
    #
    #     if pedestal_poly:
    #         ped_x, ped_y = pedestal_poly.exterior.xy
    #         ax.fill(ped_x, ped_y, color='#E9ECEF', ec='#adb5bd', lw=1.5, label='Pedestal')
    #
    #     # 2. 精確建構並繪製 Vcbg 破壞區域
    #     # ... (這部分的邏輯與 Vcb 的繪圖邏輯非常相似，但需要對群組中所有錨栓操作) ...
    #     # a. 為群組中的每個錨栓創建射線和理論破壞錐
    #     all_cones = []
    #     shear_angle = math.atan2(vy, vx)
    #     angle_1, angle_2 = shear_angle + math.radians(55), shear_angle - math.radians(55)
    #     far_dist = max(pedestal_params.get('B', 0), pedestal_params.get('N', 0), pedestal_params.get('D', 0)) * 5
    #
    #     for bolt_coord in group_coords_to_plot:
    #         ray1_end = (bolt_coord[0] + far_dist * math.cos(angle_1), bolt_coord[1] + far_dist * math.sin(angle_1))
    #         ray2_end = (bolt_coord[0] + far_dist * math.cos(angle_2), bolt_coord[1] + far_dist * math.sin(angle_2))
    #         all_cones.append(Polygon([bolt_coord, ray1_end, ray2_end]))
    #
    #     # b. 將所有錨栓的理論破壞錐合併成一個大的形狀
    #     union_of_cones = unary_union(all_cones)
    #
    #     # c. 計算合併後的形狀與墩柱的交集
    #     actual_area_poly = union_of_cones.intersection(pedestal_poly)
    #
    #     # d. 繪製這個精確的交集區域
    #     if not actual_area_poly.is_empty and actual_area_poly.geom_type == 'Polygon':
    #         ax_x, ax_y = actual_area_poly.exterior.xy
    #         ax.fill(ax_x, ax_y, color=(230 / 255, 57 / 255, 70 / 255, 0.4), ec='none', label='Actual Area (A_Vcg)')
    #         ax.plot(ax_x, ax_y, color='#457b9d', linestyle='--', lw=2, label='Breakout Boundary')
    #
    #     # 3. 繪製所有錨栓，並突顯群組錨栓
    #     all_bolts_np = np.array(all_bolt_coords)
    #     group_bolts_np = np.array(group_coords_to_plot)
    #     is_in_group = [tuple(row) in map(tuple, group_bolts_np) for row in all_bolts_np]
    #     ax.plot(all_bolts_np[~np.array(is_in_group), 0], all_bolts_np[~np.array(is_in_group), 1], 'o', color='gray',
    #             markersize=8, alpha=0.8, label='Other Anchors')
    #     ax.plot(group_bolts_np[:, 0], group_bolts_np[:, 1], '*', color='#fca311', markersize=18,
    #             markeredgecolor='black',
    #             label='Anchors in Group')
    #
    #     # 6. 圖表設定
    #     ax.set_aspect('equal', 'box')
    #     ax.grid(True, linestyle=':', linewidth=0.5)
    #     ax.set_title(f'Concrete Shear Breakout Area ($A_{{Vc}}$)', fontsize=14)
    #     ax.set_xlabel(f'X-axis ({unit_label})')
    #     ax.set_ylabel(f'Y-axis ({unit_label})')
    #     ax.legend()
    #
    #     # [核心新增] 手動設定刻度和範圍
    #     ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    #     ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    #     x_abs_max = np.max(np.abs(ax.get_xlim()))
    #     y_abs_max = np.max(np.abs(ax.get_ylim()))
    #     ax_max = max(x_abs_max, y_abs_max) * 1.1
    #     ax.set_xlim(-ax_max, ax_max)
    #     ax.set_ylim(-ax_max, ax_max)
    #
    #     plt.tight_layout()
    #
    #     buf = io.BytesIO()
    #     fig.savefig(buf, format='png', dpi=120)
    #     buf.seek(0)
    #     critical_res['plot_base64'] = base64.b64encode(buf.getvalue()).decode('utf-8')
    #     plt.close(fig)

    return all_combinations_results


# import bpN_AnchorTensionCheck as tension_check
from . import bpN_AnchorTensionCheck as tension_check


def calculate_single_anchor_pryout_Vcp(anchor_coord, pedestal_params, anchor_params, bolt_params):
    # --- A. 提取参数 ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    h_ef = anchor_params['h_ef']
    # 强度折减系数 Φ (根据表 17.5.3c，撬破强度)
    has_supplementary_reinf = anchor_params.get('has_supplementary_reinf', False)

    if has_supplementary_reinf:
        phi_cp = 0.75
    else:
        phi_cp = 0.70

    # --- B. 计算系数 kcp ---
    k_cp = 2.0
    if unit_system == 'imperial':
        if h_ef < 2.5:
            k_cp = 1.0
    else:
        if h_ef < 6.5:
            k_cp = 1.0

    # --- C. [核心] 计算 Ncp ---
    # 根据规范 17.7.3.1.1，对于预埋扩头锚栓，Ncp 就是 Ncb
    # 我们直接呼叫之前写好的 Ncb 计算器函式来获取标称强度
    ncb_results = tension_check.calculate_single_anchor_breakout_Ncb(
        anchor_coord, pedestal_params, anchor_params
    )

    if ncb_results is None:
        # 如果 Ncb 计算不适用，则 Vcp 也不适用
        return None

    Ncp = ncb_results['Ncb']  # 获取标称强度 Ncb

    # --- D. 计算标称强度 Vcp (式 17.7.3.1a) ---
    Vcp = k_cp * Ncp

    # --- E. 计算设计强度并返回 ---
    phi_Vcp = phi_cp * Vcp

    print(f"    - (Vcp 計算細節: kcp={k_cp}, Ncp(Ncb)={Ncp:.2f} kips)")

    return {
        "phi_Vcp": phi_Vcp,
        "Vcp": Vcp,
        "h_ef": h_ef,
        "Ncp": Ncp,
        "k_cp": k_cp,
        "phi_cp": phi_cp
    }


def calculate_group_pryout_Vcpg(analysis_results, pedestal_params, anchor_params):
    # --- A. 提取参数 ---
    unit_system = anchor_params.get('unit_system', 'imperial')
    h_ef = anchor_params['h_ef']
    has_supplementary_reinf = anchor_params.get('has_supplementary_reinf', False)

    if has_supplementary_reinf:
        phi_cp = 0.75
    else:
        phi_cp = 0.70

    # --- B. 计算系数 kcp ---
    k_cp = 2.0
    if unit_system == 'imperial':
        if h_ef < 2.5:
            k_cp = 1.0
    else:
        if h_ef < 6.5:
            k_cp = 1.0

    # --- C. [核心] 计算 Ncpg ---
    # 根据规范 17.7.3.1.2，对于预埋扩头锚栓群，Ncpg 就是 Ncbg
    # 我们直接呼叫之前写好的 Ncbg 计算器函式来获取标称强度
    ncbg_results = tension_check.calculate_group_breakout_Ncbg(
        analysis_results, pedestal_params, anchor_params
    )

    if ncbg_results is None:
        # 如果 Ncbg 计算不适用，则 Vcpg 也不适用
        return None

    Ncpg = ncbg_results['Ncbg']  # 获取标称强度 Ncbg

    # --- D. 计算标称强度 Vcpg (式 17.7.3.1b) ---
    Vcpg = k_cp * Ncpg

    # --- E. 计算设计强度并返回 ---
    phi_Vcpg = phi_cp * Vcpg

    print(f"    - (Vcpg 计算细节: kcp={k_cp}, Ncpg(Ncbg)={Ncpg:.2f} kips)")

    return {
        "phi_Vcpg": phi_Vcpg,
        "Vcpg": Vcpg,
        "h_ef": h_ef,
        "Ncpg": Ncpg,
        "k_cp": k_cp,
        "phi_cp": phi_cp
    }

import warnings
import matplotlib
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches  # 確保匯入 patches
from .bpN_svg_utils import SvgPlotter

matplotlib.use('Agg')
import numpy as np

from scipy.optimize import fsolve

import io
import base64

IN_TO_CM = 2.54
KSI_TO_KGF_CM2 = 70.307
KGF_TO_KIPS = 0.00220462
KIP_TO_TF = 0.453592
IN2_TO_CM2 = IN_TO_CM * IN_TO_CM
PSI_TO_KGF_CM2 = 0.070307

try:
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题
except:
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
    except:
        print("警告: 系统中未找到 'Microsoft JhengHei' 或 'SimHei' 字體，中文可能無法正常顯示。")


# [核心新增] 将锚栓坐标生成逻辑提取为独立的辅助函数
def get_bolt_coordinates(plate_params, bolt_params):
    """
    根据基础版和锚栓的参数，计算并返回锚栓的坐标阵列。
    """
    bolt_layout_mode = bolt_params.get('layout_mode')

    # 确定基础版的边界尺寸 x_max, y_max
    plate_shape = plate_params.get('shape', 'rectangle')
    if plate_shape == 'rectangle':
        x_max = plate_params.get('B', 0) / 2
        y_max = plate_params.get('N', 0) / 2
    else:  # Circle or Octagon
        x_max = y_max = plate_params.get('outer_radius', 0)

    if bolt_layout_mode == 'grid':
        edge_dist_X = bolt_params.get('edge_dist_X', 0)
        edge_dist_Y = bolt_params.get('edge_dist_Y', 0)
        num_ins_X = bolt_params.get('num_inserted_X', 0)
        num_ins_Y = bolt_params.get('num_inserted_Y', 0)

        blpx = x_max - edge_dist_X
        blpy = y_max - edge_dist_Y

        cs = set()
        xrc = np.linspace(-blpx, blpx, num_ins_X + 2)
        for x in xrc:
            cs.add((round(x, 5), round(blpy, 5)))
            cs.add((round(x, 5), round(-blpy, 5)))
        yci = np.linspace(-blpy, blpy, num_ins_Y + 2)[1:-1]
        for y in yci:
            cs.add((round(-blpx, 5), round(y, 5)))
            cs.add((round(blpx, 5), round(y, 5)))

        bolt_coords = np.array(list(cs))
        return bolt_coords

    elif bolt_layout_mode == 'circular':
        num_bolts = bolt_params.get('count', 8)
        bolt_radius = bolt_params.get('radius', 0)
        angle = bolt_params.get('start_angle', 0)
        angles = np.linspace(0, 2 * np.pi, num_bolts, endpoint=False) + np.deg2rad(angle)
        bolt_coords = np.array([[bolt_radius * np.cos(a), bolt_radius * np.sin(a)] for a in angles])
        return bolt_coords

    elif bolt_layout_mode == 'custom':
        # 直接使用前端傳來的座標
        bolt_coords = np.array(bolt_params.get('coordinates', []))
        return bolt_coords

    else:
        raise ValueError(f"錯誤: 未知的螺栓佈置模式 '{bolt_layout_mode}'.")


def perform_analysis(plate_shape, P_applied, Mx_applied, My_applied, Es, Ec, bolt_layout_mode, plate_params,
                     bolt_params, show_plot=False, generate_plot_data=False, unit_system='imperial'):
    My_applied = -My_applied
    print("--- 1. 開始執行主分析模組 ---")

    # =====================================================================
    # ==== START: 【核心重構】A. 基礎版與開孔幾何定義 ====
    # =====================================================================

    # --- Helper functions for geometry ---
    def get_poly_verts(r, ns=8):
        if r == 0: return np.array([])
        sa = np.pi / ns if ns % 2 == 0 else 0
        a = np.linspace(0, 2 * np.pi, ns, endpoint=False) + sa
        return np.array([[r * np.cos(i), r * np.sin(i)] for i in a])

    def get_circle_verts(r, n=100):
        if r == 0: return np.array([])
        a = np.linspace(0, 2 * np.pi, n)
        return np.array([[r * np.cos(i), r * np.sin(i)] for i in a])

    def calc_poly_props(v):
        if v.size == 0: return 0, 0, 0, 0, 0
        x, y = v[:, 0], v[:, 1]
        xs, ys = np.roll(x, -1), np.roll(y, -1)
        cp = x * ys - y * xs
        area = 0.5 * np.sum(cp)
        Ix = (1 / 12) * np.sum(cp * (y ** 2 + y * ys + ys ** 2))
        Iy = (1 / 12) * np.sum(cp * (x ** 2 + x * xs + xs ** 2))
        x_max_abs = np.max(np.abs(x))
        y_max_abs = np.max(np.abs(y))
        return area, Ix, Iy, x_max_abs, y_max_abs

    # --- 1. 計算外部形狀 (Outer Shape) 的性質 ---
    A_outer, Ix_outer, Iy_outer = 0, 0, 0
    plate_outer_verts = np.array([])
    x_max, y_max = 0, 0

    if plate_shape == 'rectangle':
        B = plate_params['B']
        N = plate_params['N']
        x_max, y_max = B / 2, N / 2
        plate_outer_verts = np.array([[-x_max, -y_max], [x_max, -y_max], [x_max, y_max], [-x_max, y_max]])
        A_outer = B * N
        Ix_outer = B * N ** 3 / 12
        Iy_outer = N * B ** 3 / 12
    elif plate_shape in ['octagon', 'circle']:
        outer_radius = plate_params.get('outer_radius', 0)
        x_max = y_max = outer_radius
        if plate_shape == 'octagon':
            plate_outer_verts = get_poly_verts(outer_radius)
            A_outer, Ix_outer, Iy_outer, _, _ = calc_poly_props(plate_outer_verts)
        else:  # Circle
            plate_outer_verts = get_circle_verts(outer_radius)
            A_outer = np.pi * outer_radius ** 2
            Ix_outer = Iy_outer = np.pi * outer_radius ** 4 / 4

    # --- 2. 計算內部開孔 (Inner Shape) 的性質 ---
    A_inner, Ix_inner, Iy_inner = 0, 0, 0
    # 【核心修正】初始化为空的 (0, 2) 阵列
    plate_inner_verts = np.empty((0, 2))
    hole_shape = plate_params.get('hole_shape')

    if hole_shape:
        if hole_shape == 'rectangle':
            b = plate_params.get('b', 0)
            n = plate_params.get('n', 0)
            if b > 0 and n > 0:
                plate_inner_verts = np.array([[-b / 2, -n / 2], [b / 2, -n / 2], [b / 2, n / 2], [-b / 2, n / 2]])
                A_inner = b * n
                Ix_inner = b * n ** 3 / 12
                Iy_inner = n * b ** 3 / 12
        elif hole_shape in ['octagon', 'circle']:
            inner_radius = plate_params.get('inner_radius', 0)
            if inner_radius > 0:
                if hole_shape == 'octagon':
                    plate_inner_verts = get_poly_verts(inner_radius)
                    A_inner, Ix_inner, Iy_inner, _, _ = calc_poly_props(plate_inner_verts)
                else:  # Circle
                    plate_inner_verts = get_circle_verts(inner_radius)
                    A_inner = np.pi * inner_radius ** 2
                    Ix_inner = Iy_inner = np.pi * inner_radius ** 4 / 4

    # --- 3. 計算最終斷面性質 ---
    A_plate = A_outer - A_inner
    Ix_plate = Ix_outer - Ix_inner
    Iy_plate = Iy_outer - Iy_inner

    # B. 螺栓佈置產生器
    bolt_diameter = bolt_params['diameter']
    bolt_area = np.pi * (bolt_diameter / 2) ** 2
    bolt_layout_mode = bolt_params['layout_mode']

    # [核心修改] 调用新的辅助函数来获取锚栓坐标
    bolt_coords = get_bolt_coordinates(plate_params, bolt_params)
    num_bolts = len(bolt_coords)
    bolt_diameter = bolt_params['diameter']
    bolt_area = np.pi * (bolt_diameter / 2) ** 2

    # (分析求解器函數 solve_... 和 判斷邏輯保持不變)
    def solve_bearing_case(grid_info):
        # gd = 1000
        # xg, yg = np.linspace(-x_max, x_max, gd), np.linspace(-y_max, y_max, gd)
        # xv, yv = np.meshgrid(xg, yg)
        # gp = np.vstack([xv.ravel(), yv.ravel()]).T
        # ca = (xg[1] - xg[0]) * (yg[1] - yg[0])
        # op = Path(plate_outer_verts)
        # iin = op.contains_points(gp)
        # # 如果有开孔，计算在开孔外的点；否则，所有点都在开孔外
        # if plate_inner_verts.size > 0:
        #     ip = Path(plate_inner_verts)
        #     iou = ~ip.contains_points(gp)
        # else:
        #     iou = np.ones_like(iin, dtype=bool)  # 创建一个全为 True 的布尔数组
        #
        # bap = gp[iin & iou]
        bap = grid_info['bap']
        ca = grid_info['ca']

        def residuals(v):
            e, ty, tx = v
            pr, mxr, myr = 0, 0, 0
            xc, yc = bap[:, 0], bap[:, 1]
            s = e + ty * xc + tx * yc
            ci = np.where(s < 0)
            f = Ec * s[ci] * ca
            pr += np.sum(f)
            mxr += np.sum(f * yc[ci])
            myr += np.sum(f * xc[ci])
            xb, yb = bolt_coords[:, 0], bolt_coords[:, 1]
            bs = e + ty * xb + tx * yb
            ti = np.where(bs > 0)
            f = Es * bolt_area * bs[ti]
            pr += np.sum(f)
            mxr += np.sum(f * yb[ti])
            myr += np.sum(f * xb[ti])
            return [P_applied - pr, Mx_applied - mxr, My_applied - myr]

        sol, _, ier, _ = fsolve(residuals, [0, 0, 0], full_output=True)
        # return (
        #     sol, "Bearing", {'xv': xv, 'yv': yv, 'is_in': iin, 'is_out': iou, 'bap': bap, 'ca': ca}) if ier == 1 else (
        #     None, "Bearing Solver Failed", None)
        return (sol, "Bearing") if ier == 1 else (None, "Bearing Solver Failed")

    def solve_tension_only_case():
        c = Es * bolt_area
        sc = num_bolts * c
        scx = np.sum(c * bolt_coords[:, 0])
        scy = np.sum(c * bolt_coords[:, 1])
        scxy = np.sum(c * bolt_coords[:, 0] * bolt_coords[:, 1])
        scx2 = np.sum(c * bolt_coords[:, 0] ** 2)
        scy2 = np.sum(c * bolt_coords[:, 1] ** 2)
        A = np.array([[sc, scx, scy], [scy, scxy, scy2], [scx, scx2, scxy]])
        b = np.array([P_applied, Mx_applied, My_applied])
        try:
            # 只回傳 solution 和 status
            return np.linalg.solve(A, b), "Tension-Only"
        except np.linalg.LinAlgError:
            # 只回傳 None 和 status
            return None, "Tension-Only Solver Failed"

    def solve_full_bearing_case():
        ec, ty, tx = P_applied / (A_plate * Ec), My_applied / (Iy_plate * Ec), Mx_applied / (Ix_plate * Ec)
        sol = np.array([ec, ty, tx])
        # gd = 400
        # xg, yg = np.linspace(-x_max, x_max, gd), np.linspace(-y_max, y_max, gd)
        # xv, yv = np.meshgrid(xg, yg)

        # # 【核心修正】确保传递给 Path 的是正确形状的空阵列
        #
        # # op (outer path) 总是存在，所以不需要修改
        # op = Path(plate_outer_verts)
        #
        # # ip (inner path)
        # if plate_inner_verts.size > 0:
        #     ip = Path(plate_inner_verts)
        # else:
        #     # 创建一个形状为 (0, 2) 的空阵列
        #     correctly_shaped_empty_array = np.empty((0, 2))
        #     ip = Path(correctly_shaped_empty_array)
        #
        # iin = op.contains_points(np.vstack([xv.ravel(), yv.ravel()]).T)
        # iou = ~ip.contains_points(np.vstack([xv.ravel(), yv.ravel()]).T)

        # return sol, "Full-Bearing", {'xv': xv, 'yv': yv, 'is_in': iin, 'is_out': iou}
        return sol, "Full-Bearing"

    vtc = np.vstack([plate_outer_verts, plate_inner_verts]) if plate_inner_verts.size > 0 else plate_outer_verts
    stresses = [(P_applied / A_plate) + (My_applied * vx / Iy_plate) + (Mx_applied * vy / Ix_plate) for vx, vy in vtc]
    min_s, max_s = min(stresses), max(stresses)

    # --- 1. [核心修正] 先根據應力預判來決定 status ---
    preliminary_status = ""
    if min_s > 1e-9:
        preliminary_status = "Tension-Only"
    elif max_s < -1e-9:
        preliminary_status = "Full-Bearing"
    else:
        preliminary_status = "Bearing"

    # --- 2. [核心修正] 根據 status 準備 grid_data (如果需要) ---
    grid_data = {}
    if preliminary_status in ["Bearing", "Full-Bearing"]:
        gd = 1000 if preliminary_status == "Bearing" else 400
        xg, yg = np.linspace(-x_max, x_max, gd), np.linspace(-y_max, y_max, gd)
        xv, yv = np.meshgrid(xg, yg)
        gp = np.vstack([xv.ravel(), yv.ravel()]).T
        ca = (xg[1] - xg[0]) * (yg[1] - yg[0]) if gd > 1 else 0

        op = Path(plate_outer_verts)
        iin = op.contains_points(gp)
        iou = ~Path(plate_inner_verts).contains_points(gp) if plate_inner_verts.size > 0 else np.ones_like(iin)

        bap = gp[iin & iou]
        grid_data = {'xv': xv, 'yv': yv, 'is_in': iin, 'is_out': iou, 'bap': bap, 'ca': ca}

    # --- 3. [核心修正] 呼叫對應的求解器 ---
    if preliminary_status == "Tension-Only":
        solution, status = solve_tension_only_case()
    elif preliminary_status == "Full-Bearing":
        solution, status = solve_full_bearing_case()
    else:  # Bearing
        solution, status = solve_bearing_case(grid_data)

    if solution is None:
        print(f"--- 分析失敗: {status} ---")
        return None

    # [核心修正] 無論哪種模式，都在這裡統一計算和打包結果
    epsilon_c, theta_y, theta_x = solution
    bolt_strains = epsilon_c + theta_y * bolt_coords[:, 0] + theta_x * bolt_coords[:, 1]
    bolt_forces = np.where(bolt_strains > 0, Es * bolt_area * bolt_strains, 0)

    max_pressure = 0.0
    concrete_force_Bu = 0.0
    grid_pressures = None

    if status in ["Bearing", "Full-Bearing"]:
        xv, yv = grid_data['xv'], grid_data['yv']
        grid_strains = epsilon_c + theta_y * xv + theta_x * yv
        grid_pressures = np.where(grid_strains < 0, -(Ec * grid_strains), np.nan)

        # ===== START: 【核心修正】 =====
        # 将 with 语句直接包裹住产生警告的行
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            max_pressure = np.nanmax(grid_pressures)
        # ===== END: 【核心修正】 =====

        if np.isnan(max_pressure) or max_pressure == -np.inf:
            max_pressure = 0.0

        if status == "Full-Bearing":
            concrete_force_Bu = abs(P_applied)
        else:  # Bearing
            s = epsilon_c + theta_y * grid_data['bap'][:, 0] + theta_x * grid_data['bap'][:, 1]
            ci = np.where(s < 0)
            concrete_force_Bu = abs(np.sum(Ec * s[ci] * grid_data['ca']))

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN slice encountered')

        if status in ["Bearing", "Full-Bearing"]:
            xv, yv = grid_data['xv'], grid_data['yv']
            grid_strains = epsilon_c + theta_y * xv + theta_x * yv
            grid_pressures = np.where(grid_strains < 0, -(Ec * grid_strains), np.nan)

            # np.nanmax 会在 grid_pressures 全为 NaN 时发出警告
            max_pressure = np.nanmax(grid_pressures)

            if np.isnan(max_pressure) or max_pressure == -np.inf:
                max_pressure = 0.0

            if status == "Full-Bearing":
                concrete_force_Bu = abs(P_applied)
            else:  # Bearing
                s = epsilon_c + theta_y * grid_data['bap'][:, 0] + theta_x * grid_data['bap'][:, 1]
                ci = np.where(s < 0)
                concrete_force_Bu = abs(np.sum(Ec * s[ci] * grid_data['ca']))
        else:  # Tension-Only
            max_pressure, concrete_force_Bu, grid_pressures = 0.0, 0.0, None

    # -------------------------------------------------------
    # SVG 繪圖邏輯 (v2.6 - 修正縮放比例與中性軸裁切)
    # -------------------------------------------------------
    plot_base64 = None
    if show_plot or generate_plot_data:
        # 1. 初始化繪圖器 (極小邊距，讓圖盡量大)
        plotter = SvgPlotter(width=600, height=680, margin_percent=0.05)

        unit_label = 'cm' if unit_system == 'mks' else 'in'
        length_conv = IN_TO_CM if unit_system == 'mks' else 1.0
        pressure_label = 'kgf/cm²' if unit_system == 'mks' else 'ksi'
        pressure_conv = KSI_TO_KGF_CM2 if unit_system == 'mks' else 1.0

        # 2. 繪製基礎版
        e_x, e_y = plate_params.get('e_x', 0) * length_conv, plate_params.get('e_y', 0) * length_conv
        plate_style = {'fill': "none", 'stroke': "black", 'stroke_width': 2}

        # 記錄基礎版邊界，用於裁切中性軸
        bounds_x = 0
        bounds_y = 0

        if plate_shape == 'rectangle':
            B_plot = plate_params['B'] * length_conv
            N_plot = plate_params['N'] * length_conv
            plotter.add_rect(e_x, e_y, B_plot, N_plot, **plate_style)
            bounds_x = B_plot / 2
            bounds_y = N_plot / 2
        elif plate_shape == 'circle':
            R_plot = plate_params.get('outer_radius', 0) * length_conv
            plotter.add_circle(e_x, e_y, R_plot, **plate_style)
            bounds_x = R_plot
            bounds_y = R_plot
        elif plate_shape == 'octagon':
            R_plot = plate_params.get('outer_radius', 0) * length_conv
            angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 9, endpoint=True)
            verts = [[R_plot * np.cos(a) + e_x, R_plot * np.sin(a) + e_y] for a in angles]
            plotter.add_polygon(verts, **plate_style)
            bounds_x = R_plot
            bounds_y = R_plot

        # 3. 繪製應力分佈 (Heatmap)
        if status in ["Bearing", "Full-Bearing"] and max_pressure > 1e-6 and 'xv' in grid_data:
            orig_xv = grid_data['xv']
            orig_yv = grid_data['yv']
            rows, cols = orig_xv.shape
            is_in_2d = grid_data['is_in'].reshape(rows, cols)

            is_out_2d = None
            if plate_inner_verts.size > 0 and 'is_out' in grid_data:
                is_out_2d = grid_data['is_out'].reshape(rows, cols)

            step = max(1, int(rows / 40))
            cell_w = (orig_xv[0, 1] - orig_xv[0, 0]) * step * length_conv * 1.05
            cell_h = (orig_yv[1, 0] - orig_yv[0, 0]) * step * length_conv * 1.05
            max_p_val = max_pressure * pressure_conv
            plotter.add_colorbar(0, max_p_val, f"Pressure ({pressure_label})", base_color=(0, 110, 255))

            for r in range(0, rows, step):
                for c in range(0, cols, step):
                    is_valid_point = is_in_2d[r, c]
                    if is_out_2d is not None:
                        is_valid_point = is_valid_point and is_out_2d[r, c]
                    if is_valid_point:
                        strain = epsilon_c + theta_y * orig_xv[r, c] + theta_x * orig_yv[r, c]
                        if strain < 0:
                            pressure = -strain * Ec * pressure_conv
                            color = plotter.get_color_for_value(pressure, max_p_val, base_color=(0, 110, 255))
                            px = orig_xv[r, c] * length_conv + e_x
                            py = orig_yv[r, c] * length_conv + e_y
                            plotter.add_rect(px, py, cell_w, cell_h, fill=color, stroke="none")

        # 4. 繪製中性軸 (Neutral Axis) - [核心修正：限制繪製範圍]
        if status == "Bearing" and (abs(theta_x) > 1e-9 or abs(theta_y) > 1e-9):
            # 計算兩個端點
            # 1.2 倍邊界是為了讓線稍微超出基礎版，好看一點
            limit_x = bounds_x * 1.2
            limit_y = bounds_y * 1.2

            p1_x, p1_y, p2_x, p2_y = 0, 0, 0, 0

            if abs(theta_x) > abs(theta_y):
                x1, x2 = -limit_x, limit_x
                y1 = (-theta_y * (x1 / length_conv) - epsilon_c) / theta_x * length_conv
                y2 = (-theta_y * (x2 / length_conv) - epsilon_c) / theta_x * length_conv
                p1_x, p1_y, p2_x, p2_y = x1, y1, x2, y2
            else:
                y1, y2 = -limit_y, limit_y
                x1 = (-theta_x * (y1 / length_conv) - epsilon_c) / theta_y * length_conv
                x2 = (-theta_x * (y2 / length_conv) - epsilon_c) / theta_y * length_conv
                p1_x, p1_y, p2_x, p2_y = x1, y1, x2, y2

            # [裁切] 確保座標不會超出繪圖範圍太多
            # 這是關鍵：如果 y1 太大，SvgPlotter 會縮小整個圖來容納這個點
            p1_x = max(-limit_x * 1.5, min(limit_x * 1.5, p1_x))
            p2_x = max(-limit_x * 1.5, min(limit_x * 1.5, p2_x))
            p1_y = max(-limit_y * 1.5, min(limit_y * 1.5, p1_y))
            p2_y = max(-limit_y * 1.5, min(limit_y * 1.5, p2_y))

            plotter.add_line(p1_x + e_x, p1_y + e_y, p2_x + e_x, p2_y + e_y, color="red", width=2,
                             stroke_dasharray="5,5")

        # 5. 繪製開孔
        if plate_inner_verts.size > 0:
            if hole_shape == 'rectangle':
                hb = plate_params.get('b', 0) * length_conv
                hn = plate_params.get('n', 0) * length_conv
                plotter.add_rect(e_x, e_y, hb, hn, fill="white", stroke="black", stroke_width=1)
            elif hole_shape in ['circle', 'octagon']:
                hr = plate_params.get('inner_radius', 0) * length_conv
                plotter.add_circle(e_x, e_y, hr, fill="white", stroke="black", stroke_width=1)

        # 6. 繪製錨栓
        bolt_coords_plot = bolt_coords * length_conv
        bolt_radius = (bolt_params.get('diameter', 1.0) * length_conv) / 2.0
        min_radius = 0.2 if unit_system == 'mks' else 0.08
        display_radius = max(bolt_radius, min_radius)

        for i, (bx, by) in enumerate(bolt_coords_plot):
            is_tension = bolt_forces[i] > 0.001
            color = "#d9534f" if is_tension else "#5bc0de"

            plotter.add_circle(bx + e_x, by + e_y, r=display_radius, fill=color, stroke="black", stroke_width=1)

            # 編號 (稍微偏移)
            text_offset = display_radius * 2.5
            plotter.add_text(bx + e_x + text_offset, by + e_y - text_offset, str(i), size=18, weight="bold", bg="white")

        # 7. 圖例
        plotter.add_legend_item("受拉錨栓", "circle", fill="#d9534f", stroke="black")
        plotter.add_legend_item("受壓錨栓", "circle", fill="#5bc0de", stroke="black")
        if status != "Tension-Only":
            max_color = plotter.get_color_for_value(1, 1, base_color=(0, 110, 255))
            plotter.add_legend_item("最大壓力", "rect", fill=max_color, stroke="none")
            plotter.add_legend_item("中性軸", "line", stroke="red", stroke_width=2, stroke_dasharray="5,5")

        plot_base64 = plotter.render_to_base64()

    return {
        "status": status,
        "plate_shape": plate_shape,
        "A_plate": A_plate,
        "plate_N": plate_params.get('N', 0),
        "plate_B": plate_params.get('B', 0),
        "max_pressure": max_pressure,
        "concrete_force_Bu": concrete_force_Bu,
        "bolt_forces": bolt_forces.tolist(),
        "bolt_coords": bolt_coords.tolist(),
        "num_bolts": num_bolts,
        "grid_pressures": grid_pressures,
        "grid_data": grid_data,
        "plot_base64": plot_base64,  # 回傳 SVG Base64
        "solution": solution.tolist()
    }


# bpN_mainAnalysis.py

# bpN_mainAnalysis.py

def generate_shear_vector_plot(
        bolt_coords_imperial,
        bolt_shear_demands_imperial,
        plate_params,
        pedestal_params,
        column_params,
        bolt_params,           # <--- [核心修正] 新增此參數
        critical_bolt_index=None,
        highlight_indices=None,
        title="錨栓剪力分布圖",
        vector_type='components',
        unit_system='imperial',
        show_background_geometry=True,
        display_direction=None
):
    """
    使用 SVG 生成錨栓剪力向量圖，速度極快。
    """
    plotter = SvgPlotter(width=600, height=600)

    unit_label = 'cm' if unit_system == 'mks' else 'in'
    conv = IN_TO_CM if unit_system == 'mks' else 1.0

    # --- 1. 繪製墩柱 (Pedestal) ---
    if show_background_geometry and pedestal_params:
        pedestal_shape = pedestal_params.get('shape', 'rectangle')
        if pedestal_shape == 'rectangle':
            ped_B = pedestal_params.get('B', 0) * conv
            ped_N = pedestal_params.get('N', 0) * conv
            plotter.add_rect(0, 0, ped_B, ped_N, fill="#E9ECEF", stroke="#adb5bd", stroke_width=1.5)
        else:
            ped_D = pedestal_params.get('D', 0) * conv
            plotter.add_circle(0, 0, ped_D / 2, fill="#E9ECEF", stroke="#adb5bd", stroke_width=1.5)

    # --- 2. 繪製基礎版 (Base Plate) ---
    e_x, e_y = plate_params.get('e_x', 0) * conv, plate_params.get('e_y', 0) * conv
    plate_shape = plate_params.get('shape', 'rectangle')
    plate_fill = "rgba(2, 117, 216, 0.1)"
    plate_stroke = "#0275d8"

    if plate_shape == 'rectangle':
        plate_B = plate_params.get('B', 0) * conv
        plate_N = plate_params.get('N', 0) * conv
        plotter.add_rect(e_x, e_y, plate_B, plate_N, fill=plate_fill, stroke=plate_stroke, stroke_width=2)
    else:
        outer_radius = plate_params.get('outer_radius', 0) * conv
        if plate_shape == 'circle':
            plotter.add_circle(e_x, e_y, outer_radius, fill=plate_fill, stroke=plate_stroke, stroke_width=2)
        else:  # Octagon
            angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 9, endpoint=True)
            verts = [[outer_radius * np.cos(a) + e_x, outer_radius * np.sin(a) + e_y] for a in angles]
            plotter.add_polygon(verts, fill=plate_fill, stroke=plate_stroke, stroke_width=2)

    # --- 3. 繪製開孔 ---
    if plate_params.get('has_hole', False):
        hole_shape = plate_params.get('hole_shape', 'rectangle')
        if hole_shape == 'rectangle':
            h_b = plate_params.get('b', 0) * conv
            h_n = plate_params.get('n', 0) * conv
            plotter.add_rect(e_x, e_y, h_b, h_n, fill="white", stroke="#adb5bd", stroke_width=1, stroke_dasharray="5,5")
        else:
            inner_radius = plate_params.get('inner_radius', 0) * conv
            if hole_shape == 'circle':
                plotter.add_circle(e_x, e_y, inner_radius, fill="white", stroke="#adb5bd", stroke_width=1,
                                   stroke_dasharray="5,5")
            else:  # Octagon hole
                angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 9, endpoint=True)
                verts = [[inner_radius * np.cos(a) + e_x, inner_radius * np.sin(a) + e_y] for a in angles]
                plotter.add_polygon(verts, fill="white", stroke="#adb5bd", stroke_width=1, stroke_dasharray="5,5")

    # --- 4. 繪製鋼柱 ---
    if show_background_geometry and column_params:
        col_type = column_params.get('type', 'H-Shape').lower()
        col_style = {'fill': 'none', 'stroke': '#343a40', 'stroke_width': 2}

        if col_type == 'h-shape':
            d, bf, tf, tw = [column_params.get(k, 0) * conv for k in ['d', 'bf', 'tf', 'tw']]
            plotter.add_rect(0, d / 2 - tf / 2, bf, tf, **col_style)
            plotter.add_rect(0, -d / 2 + tf / 2, bf, tf, **col_style)
            plotter.add_rect(0, 0, tw, d - 2 * tf, **col_style)

        elif col_type == 'tube':
            B, H = column_params.get('B', 0) * conv, column_params.get('H', 0) * conv
            plotter.add_rect(0, 0, B, H, **col_style)

        elif col_type == 'pipe':
            D = column_params.get('D', 0) * conv
            plotter.add_circle(0, 0, D / 2, **col_style)

    # --- 5. 繪製錨栓與剪力 ---
    if bolt_coords_imperial is not None and len(bolt_coords_imperial) > 0:
        bolt_coords_plot = np.array(bolt_coords_imperial) * conv

        # [修正] 從傳入的 bolt_params 獲取直徑
        bolt_dia = bolt_params.get('diameter')
        if bolt_dia is None: bolt_dia = 1.0  # fallback
        bolt_radius = (bolt_dia * conv) / 2.0
        min_radius = 0.2 if unit_system == 'mks' else 0.08
        display_radius = max(bolt_radius, min_radius)

        # [修正] 剪力圖：編號變大 (size=16)，位置往左上方移動
        text_offset = display_radius * 2.0

        # 先畫所有錨栓點
        for i, (x, y) in enumerate(bolt_coords_plot):
            bx, by = x + e_x, y + e_y
            plotter.add_circle(bx, by, r=display_radius, fill="cornflowerblue", stroke="black")

            # 繪製編號：左上方
            plotter.add_text(bx - text_offset, by + text_offset, str(i), size=16, bg="white")

        # 再畫剪力向量
        if bolt_shear_demands_imperial:
            max_shear_val = max([d['Vua_total'] for d in bolt_shear_demands_imperial])
            if max_shear_val < 1e-6: max_shear_val = 1.0

            # 箭頭縮放比例
            ref_dim = max(plate_params.get('B', 10), plate_params.get('N', 10)) * conv
            scale_factor = (ref_dim * 0.2) / max_shear_val

            indices_to_label = []
            if highlight_indices:
                indices_to_label = highlight_indices
            elif critical_bolt_index is not None:
                indices_to_label = [critical_bolt_index]

            for i, demand in enumerate(bolt_shear_demands_imperial):
                bx, by = bolt_coords_plot[i][0] + e_x, bolt_coords_plot[i][1] + e_y
                vx, vy = demand['Vua_x'], demand['Vua_y']

                plot_vx, plot_vy = 0, 0
                if display_direction == 'X':
                    plot_vx = vx
                elif display_direction == 'Y':
                    plot_vy = vy
                else:
                    plot_vx, plot_vy = vx, vy

                mag = np.sqrt(plot_vx ** 2 + plot_vy ** 2)
                if mag > 1e-6:
                    end_x = bx + plot_vx * scale_factor
                    end_y = by + plot_vy * scale_factor
                    plotter.add_arrow(bx, by, end_x, end_y, color="red")

                    # 如果是關鍵錨栓，添加文字標籤
                    if i in indices_to_label:
                        label = ""
                        if display_direction == 'X':
                            label = f"Vx:{demand['Vua_x']:.1f}"
                        elif display_direction == 'Y':
                            label = f"Vy:{demand['Vua_y']:.1f}"
                        else:
                            label = f"V:{demand['Vua_total']:.1f}"

                        # 文字位置：箭頭終點再往外一點
                        text_x = end_x + (plot_vx / mag) * 5
                        text_y = end_y + (plot_vy / mag) * 5

                        # [修正] 剪力數值文字變大 (size=18)
                        plotter.add_text(text_x, text_y, label, color="red", size=18, weight="bold", bg="white")

    # 回傳 Base64
    svg_base64 = plotter.render_to_base64()
    return svg_base64

def generate_geometry_plot(plate_params, pedestal_params, bolt_params, column_params, unit_system='imperial'):
    """
    使用 SVG 生成幾何示意圖 (含 H型鋼輪廓、真實錨栓尺寸、底部圖例)。
    """
    # 這裡設定的高度包含了圖例空間
    plotter = SvgPlotter(width=600, height=650, margin_percent=0.15)
    conv = IN_TO_CM if unit_system == 'mks' else 1.0

    # === 定義樣式變數 (確保主圖與圖例顏色一致) ===
    style_pedestal = {'fill': "#E9ECEF", 'stroke': "#adb5bd", 'stroke_width': 1.5}
    style_plate = {'fill': "rgba(2, 117, 216, 0.1)", 'stroke': "#0275d8", 'stroke_width': 2}
    style_column = {'fill': "none", 'stroke': "#343a40", 'stroke_width': 2}
    style_bolt = {'fill': "#f0ad4e", 'stroke': "#d9534f", 'stroke_width': 1}

    # --- 1. 繪製墩柱 (Pedestal) ---
    ped_shape = pedestal_params.get('shape', 'rectangle')
    if ped_shape == 'rectangle':
        ped_B, ped_N = pedestal_params.get('B', 0) * conv, pedestal_params.get('N', 0) * conv
        plotter.add_rect(0, 0, ped_B, ped_N, **style_pedestal)
    else:  # circle
        ped_D = pedestal_params.get('D', 0) * conv
        plotter.add_circle(0, 0, ped_D / 2, **style_pedestal)

    # --- 2. 繪製基礎版 (Base Plate) ---
    e_x, e_y = plate_params.get('e_x', 0) * conv, plate_params.get('e_y', 0) * conv
    plate_shape = plate_params.get('shape', 'rectangle')

    if plate_shape == 'rectangle':
        plate_B, plate_N = plate_params.get('B', 0) * conv, plate_params.get('N', 0) * conv
        plotter.add_rect(e_x, e_y, plate_B, plate_N, **style_plate)
    elif plate_shape == 'circle':
        R = plate_params.get('outer_radius') * conv
        plotter.add_circle(e_x, e_y, R, **style_plate)
    else:  # Octagon
        outer_radius = plate_params.get('outer_radius', 0) * conv
        angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 9, endpoint=True)
        verts = [[outer_radius * np.cos(a) + e_x, outer_radius * np.sin(a) + e_y] for a in angles]
        plotter.add_polygon(verts, **style_plate)

    # --- 3. 繪製鋼柱 (Column) ---
    col_type = column_params.get('type', 'H-Shape')
    if col_type == 'H-Shape':
        d = column_params.get('d', 0) * conv
        bf = column_params.get('bf', 0) * conv
        tf = column_params.get('tf', 0) * conv
        tw = column_params.get('tw', 0) * conv
        h_points = [
            (-bf / 2, d / 2), (bf / 2, d / 2), (bf / 2, d / 2 - tf), (tw / 2, d / 2 - tf),
            (tw / 2, -d / 2 + tf), (bf / 2, -d / 2 + tf), (bf / 2, -d / 2), (-bf / 2, -d / 2),
            (-bf / 2, -d / 2 + tf), (-tw / 2, -d / 2 + tf), (-tw / 2, d / 2 - tf), (-bf / 2, d / 2 - tf)
        ]
        plotter.add_polygon(h_points, **style_column)
    elif col_type == 'Tube':
        B, H = column_params.get('B', 0) * conv, column_params.get('H', 0) * conv
        t = column_params.get('t', 0) * conv
        plotter.add_rect(0, 0, B, H, **style_column)
        if t > 0: plotter.add_rect(0, 0, B - 2 * t, H - 2 * t, **style_column)
    elif col_type == 'Pipe':
        D = column_params.get('D', 0) * conv
        t = column_params.get('t', 0) * conv
        plotter.add_circle(0, 0, D / 2, **style_column)
        if t > 0: plotter.add_circle(0, 0, D / 2 - t, **style_column)

    # --- 4. 繪製錨栓 (Bolts) ---
    bolt_coords = get_bolt_coordinates(plate_params, bolt_params) * conv
    bolt_dia = bolt_params.get('diameter', 0) * conv
    bolt_radius = bolt_dia / 2.0
    if bolt_radius < 0.1: bolt_radius = 0.5  # 最小顯示尺寸

    if len(bolt_coords) > 0:
        for x, y in bolt_coords:
            plotter.add_circle(x + e_x, y + e_y, r=bolt_radius, **style_bolt)
            # 繪製十字線
            cross_len = bolt_radius * 1.2
            plotter.add_line(x + e_x - cross_len, y + e_y, x + e_x + cross_len, y + e_y, color=style_bolt['stroke'],
                             width=0.5)
            plotter.add_line(x + e_x, y + e_y - cross_len, x + e_x, y + e_y + cross_len, color=style_bolt['stroke'],
                             width=0.5)

    # --- 5. 加入圖例 (Legend) ---
    # 使用前面定義的樣式變數，確保圖例與實圖一致
    plotter.add_legend_item("墩柱", "rect", **style_pedestal)
    plotter.add_legend_item("基礎版", "rect", **style_plate)
    # 鋼柱在圖例中用空心矩形表示
    plotter.add_legend_item("鋼柱", "rect", fill="none", stroke=style_column['stroke'],
                            stroke_width=style_column['stroke_width'])
    plotter.add_legend_item("錨栓", "circle", **style_bolt)

    return plotter.render_to_base64()
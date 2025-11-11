import warnings
import matplotlib
from matplotlib.ticker import MaxNLocator

matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fsolve
from matplotlib.path import Path
import matplotlib.patches as patches  # 確保匯入 patches
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

    plot_base64 = None
    if show_plot or generate_plot_data:
        fig, ax = plt.subplots(figsize=(8, 8))

        pressure_unit = 'kgf/cm²' if unit_system == 'mks' else 'ksi'
        pressure_conv = KSI_TO_KGF_CM2 if unit_system == 'mks' else 1.0
        length_unit = 'cm' if unit_system == 'mks' else 'in'
        length_conv = IN_TO_CM if unit_system == 'mks' else 1.0

        # --- 1. 建立用於裁切 (clip) 的基礎版形狀 (Patch) ---
        plate_clip_patch = None
        plot_verts = plate_outer_verts * length_conv

        # 根據原始的 plate_shape 建立 Patch 物件
        if plate_shape == 'rectangle':
            B_plot, N_plot = plate_params['B'] * length_conv, plate_params['N'] * length_conv
            plate_clip_patch = patches.Rectangle((-B_plot / 2, -N_plot / 2), B_plot, N_plot, fill=False,
                                                 transform=ax.transData)
        elif plate_shape == 'circle':
            radius_plot = plate_params.get('outer_radius', 0) * length_conv
            plate_clip_patch = patches.Circle((0, 0), radius_plot, fill=False, transform=ax.transData)
        elif plate_shape == 'octagon':
            plate_clip_patch = patches.Polygon(plot_verts, fill=False, closed=True, transform=ax.transData)

        if plate_clip_patch:
            ax.add_patch(plate_clip_patch)

        # --- 2. 繪製壓力分佈圖 ---
        if status in ["Bearing", "Full-Bearing"] and max_pressure > 1e-6:
            plot_pressures = grid_pressures * pressure_conv
            plot_xv = grid_data['xv'] * length_conv
            plot_yv = grid_data['yv'] * length_conv

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                max_plot_pressure = np.nanmax(plot_pressures)

            if not (np.isnan(max_plot_pressure) or max_plot_pressure <= 0):
                levels = np.linspace(max_plot_pressure / 20, max_plot_pressure, 20)
                contour = ax.contourf(plot_xv, plot_yv, plot_pressures, cmap='Blues', levels=levels, extend='max')

                if plate_clip_patch:
                    # 應用裁切路徑到整個 contour 物件
                    contour.set_clip_path(plate_clip_patch)

                cbar = fig.colorbar(contour, ax=ax, shrink=0.8)
                cbar.set_label(f'Concrete Bearing Pressure ({pressure_unit})', size=12)

                # 標註最大壓力點
                valid_pressures_for_max = np.where(grid_data['is_in'] & grid_data['is_out'], plot_pressures.ravel(),
                                                   np.nan).reshape(plot_xv.shape)
                # 標註最大壓力點 (使用 'is_in' 遮罩來尋找)
                valid_pressures_for_max = np.where(grid_data['is_in'], plot_pressures.ravel(), np.nan).reshape(
                    plot_xv.shape)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    if not np.all(np.isnan(valid_pressures_for_max)):
                        max_idx = np.nanargmax(valid_pressures_for_max)
                        max_pressure_idx = np.unravel_index(max_idx, valid_pressures_for_max.shape)
                        max_pressure_x_plot = plot_xv[max_pressure_idx]
                        max_pressure_y_plot = plot_yv[max_pressure_idx]
                        ax.plot(max_pressure_x_plot, max_pressure_y_plot, 'X', color='red', markersize=12,
                                markeredgewidth=1.5, markeredgecolor='white',
                                label=f'Max Pressure ({max_plot_pressure:.2f} {pressure_unit})')

        if status == "Bearing":
            if abs(theta_x) > 1e-9 or abs(theta_y) > 1e-9:
                xp, yp = np.array([-x_max, x_max]) * length_conv, np.array([-y_max, y_max]) * length_conv
                if abs(theta_x) > abs(theta_y):
                    ax.plot(xp, (-theta_y * (xp / length_conv) - epsilon_c) / theta_x * length_conv, 'r--', lw=2,
                            label='Neutral Axis (NA)')
                else:
                    ax.plot((-theta_x * (yp / length_conv) - epsilon_c) / theta_y * length_conv, yp, 'r--', lw=2,
                            label='Neutral Axis (NA)')

        # --- 3. 繪製幾何輪廓 ---
        if plate_clip_patch:
            plate_clip_patch.set_fill(False)
            plate_clip_patch.set_edgecolor('black')
            plate_clip_patch.set_linewidth(2.5)
            plate_clip_patch.set_zorder(10)  # 確保邊框在最上層

        # 繪製開孔
        if plate_inner_verts.size > 0:
            ax.add_patch(
                plt.Polygon(plate_inner_verts * length_conv, fill=True, color='white', edgecolor='dimgray', lw=1.5,
                            linestyle='--', zorder=11))

        # 錨栓
        ibt = bolt_forces > 0.001
        ax.scatter(bolt_coords[ibt, 0] * length_conv, bolt_coords[ibt, 1] * length_conv, edgecolor='black',
                   facecolor='red', s=150, marker='^', label='Tension Bolts', zorder=5)
        ax.scatter(bolt_coords[~ibt, 0] * length_conv, bolt_coords[~ibt, 1] * length_conv, edgecolor='black',
                   facecolor='cornflowerblue', s=120, marker='o', label='Compression Bolts', zorder=5)
        for i, (x, y) in enumerate(bolt_coords * length_conv):
            ax.text(x + x_max * length_conv * 0.04, y, str(i), color='black', fontsize=10, ha='left', va='center')

        # 圖表設定
        ax.set_aspect('equal')
        ax.set_xlim(-x_max * 1.15 * length_conv, x_max * 1.15 * length_conv)
        ax.set_ylim(-y_max * 1.15 * length_conv, y_max * 1.15 * length_conv)
        ax.set_xlabel(f'X-axis ({length_unit})', fontsize=12)
        ax.set_ylabel(f'Y-axis ({length_unit})', fontsize=12)
        ax.set_title(f'Base Plate Analysis Result\n(Mode: {status}, Shape: {plate_shape})', fontsize=14)
        ax.grid(True, which='both', linestyle=':', linewidth=0.7)
        # fig.legend(loc='lower center', bbox_to_anchor=(0.5, 0.05), ncol=4)
        plt.subplots_adjust(bottom=0.2)
        ax.tick_params(axis='both', which='major', labelsize=10)

        # [核心修正] 將圖例放置在圖表正下方
        fig.legend(
            loc='lower center',
            bbox_to_anchor=(0.5, 0.02),  # 將 Y 座標設為 0，更貼近底部
            ncol=4,
            fontsize=12,
            frameon=True,
            edgecolor='black'
        )

        # [核心修正] 調整 bottom 邊距，為下方的圖例留出足夠空間
        plt.subplots_adjust(left=0.12, right=0.9, top=0.9, bottom=0.15)

        # 儲存圖片
        if generate_plot_data:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)
            plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
        if show_plot:
            plt.show()
        plt.close(fig)

    # 統一返回結果字典
    return {
        "status": status,
        "plate_shape": plate_shape,
        "A_plate": A_plate,
        "plate_N": plate_params.get('N', 2 * plate_params.get('outer_radius', 0)),
        "plate_B": plate_params.get('B', 2 * plate_params.get('outer_radius', 0)),
        "max_pressure": max_pressure,
        "concrete_force_Bu": concrete_force_Bu,
        "bolt_forces": bolt_forces.tolist(),  # 確保是 list
        "bolt_coords": bolt_coords.tolist(),  # 確保是 list
        "num_bolts": num_bolts,
        "grid_pressures": grid_pressures,
        "grid_data": grid_data,
        "plot_base64": plot_base64,
        "solution": solution.tolist()  # <-- [核心新增] 將求解出的應變平面參數加入回傳
    }


def generate_shear_vector_plot(bolt_coords, bolt_shear_demands, plate_params, title="錨栓剪力分布圖",
                               vector_type='resultant', unit_system='imperial'):
    """
    一个专门用于绘制锚栓剪力向量图的辅助函式。
    返回图片的 Base64 编码字符串。
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    # [核心修正] 移除 length_conv，因為傳入的數據已經是正確的單位
    length_unit = 'cm' if unit_system == 'mks' else 'in'
    force_conv = KIP_TO_TF if unit_system == 'mks' else 1.0
    length_conv = IN_TO_CM if unit_system == 'mks' else 1.0

    plate_shape = plate_params.get('shape', 'rectangle')
    if plate_shape == 'rectangle':
        B = plate_params.get('B', 0) * length_conv
        N = plate_params.get('N', 0) * length_conv
        ax.add_patch(
            patches.Polygon(np.array([[-B / 2, -N / 2], [B / 2, -N / 2], [B / 2, N / 2], [-B / 2, N / 2]]), fill=None,
                            edgecolor='black', lw=2.0))
    else:  # Circle or Octagon
        outer_radius = plate_params.get('outer_radius', 0) * length_conv
        if plate_shape == 'circle':
            ax.add_patch(patches.Circle((0, 0), outer_radius, fill=None, edgecolor='black', lw=2.0))

    # 2. 繪製錨栓位置 (現在 bolt_coords 的單位是正確的)
    bolt_coords_np = np.array(bolt_coords) * length_conv
    ax.scatter(bolt_coords_np[:, 0], bolt_coords_np[:, 1], edgecolor='black', facecolor='cornflowerblue', s=120,
               zorder=5)

    # 在每個錨栓旁邊添加編號
    ax.autoscale_view()
    x_range_plot = ax.get_xlim()[1] - ax.get_xlim()[0]
    for i, (x, y) in enumerate(bolt_coords_np):
        ax.text(x + x_range_plot * 0.02, y, str(i), color='black', fontsize=15, ha='left', va='center', weight='bold',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

    # 3. 繪製剪力向量
    max_shear_val_imperial = max(d['Vua_total'] for d in bolt_shear_demands) if bolt_shear_demands else 1.0
    if max_shear_val_imperial == 0: max_shear_val_imperial = 1.0

    ax.autoscale_view()
    x_range_plot = ax.get_xlim()[1] - ax.get_xlim()[0]
    scale_val = max_shear_val_imperial / (x_range_plot / 8.0)

    for demand in bolt_shear_demands:
        # [核心修正] demand['coord'] 已經是正確單位，直接使用
        x, y = demand['coord']
        x = x * length_conv
        y = y * length_conv

        # 剪力分量 vx, vy 仍然是英制，用於計算箭頭方向和長度比例
        vx_imperial, vy_imperial = demand['Vua_x'], demand['Vua_y']

        ax.quiver(x, y, vx_imperial, vy_imperial, angles='xy', scale_units='xy', scale=scale_val, color='r',
                  width=0.008, headwidth=4, headlength=6)

        # [核心修正] 文字標註位置計算
        norm = np.sqrt(vx_imperial ** 2 + vy_imperial ** 2)
        if norm < 1e-6: continue

        text_x = x + (vx_imperial / norm) * (x_range_plot * 0.1)
        text_y = y + (vy_imperial / norm) * (x_range_plot * 0.1)

        if vector_type == 'components':
            vx_display = demand['Vua_x']
            vy_display = demand['Vua_y']
            label = f"Vx: {vx_display:.2f}\nVy: {vy_display:.2f}"
            fontsize = 12
        else:  # 'resultant' or default
            display_val = demand['Vua_total']
            label = f"{display_val:.2f}"
            fontsize = 15

        ax.text(text_x, text_y, label, fontsize=fontsize, ha='center', va='center',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

    # 5. 圖表設定
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=14, weight='bold')
    ax.set_xlabel(f'X-axis ({length_unit})')
    ax.set_ylabel(f'Y-axis ({length_unit})')
    ax.grid(True, linestyle=':', linewidth=0.7)

    # 手動設定刻度，確保它們是 "漂亮" 的整數
    # ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    # ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))

    # 確保座標軸範圍對稱且有一定邊距
    x_abs_max = np.max(np.abs(ax.get_xlim()))
    y_abs_max = np.max(np.abs(ax.get_ylim()))
    ax_max = max(x_abs_max, y_abs_max) * 1.1
    ax.set_xlim(-ax_max, ax_max)
    ax.set_ylim(-ax_max, ax_max)

    # 將圖片保存到內存並返回 Base64
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close(fig)

    return plot_base64


# [核心新增] 新增一個專門用於繪製幾何關係圖的函式
def generate_geometry_plot(plate_params, pedestal_params, bolt_params, column_params, unit_system='imperial'):
    """
    根據輸入的幾何參數，生成一張包含墩柱、基礎版、錨栓和鋼柱的示意圖。
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    # [核心修改] 決定單位標籤和轉換係數
    unit_label = 'cm' if unit_system == 'mks' else 'in'
    conv = IN_TO_CM if unit_system == 'mks' else 1.0

    # --- 1. 繪製墩柱 (Pedestal) ---
    pedestal_shape = pedestal_params.get('shape', 'rectangle')
    if pedestal_shape == 'rectangle':
        ped_B, ped_N = pedestal_params.get('B', 0) * conv, pedestal_params.get('N', 0) * conv
        ax.add_patch(
            patches.Rectangle((-ped_B / 2, -ped_N / 2), ped_B, ped_N, fill=True, color='#E9ECEF', ec='#adb5bd', lw=1.5,
                              label='Pedestal'))
        view_width, view_height = ped_B, ped_N
    else:  # circle
        ped_D = pedestal_params.get('D', 0) * conv
        ax.add_patch(
            patches.Circle((0, 0), ped_D / 2, fill=True, color='#E9ECEF', ec='#adb5bd', lw=1.5, label='Pedestal'))
        view_width = view_height = ped_D

    # --- 2. 繪製基礎版 (Base Plate) ---
    plate_B, plate_N = plate_params.get('B', 0) * conv, plate_params.get('N', 0) * conv
    e_x, e_y = plate_params.get('e_x', 0) * conv, plate_params.get('e_y', 0) * conv
    plate_shape = plate_params.get('shape', 'rectangle')
    # [核心修改] 将 'rgba(...)' 字符串转换为 Matplotlib 可接受的元组
    base_plate_fill_color = (2 / 255, 117 / 255, 216 / 255, 0.1)

    if plate_shape == 'rectangle':
        plate_B, plate_N = plate_params.get('B', 0) * conv, plate_params.get('N', 0) * conv
        ax.add_patch(patches.Rectangle((-plate_B / 2 + e_x, -plate_N / 2 + e_y), plate_B, plate_N,
                                       fill=True, color=base_plate_fill_color, ec='#0275d8', lw=2, label='Base Plate'))
    else:  # Circle or Octagon
        outer_radius = plate_params.get('outer_radius', 0) * conv
        if plate_shape == 'circle':
            ax.add_patch(patches.Circle((e_x, e_y), outer_radius,
                                        fill=True, color=base_plate_fill_color, ec='#0275d8', lw=2, label='Base Plate'))
        else:  # Octagon
            angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 8, endpoint=False)
            verts = np.array([[outer_radius * np.cos(a) + e_x, outer_radius * np.sin(a) + e_y] for a in angles])
            ax.add_patch(patches.Polygon(verts,
                                         fill=True, color=base_plate_fill_color, ec='#0275d8', lw=2,
                                         label='Base Plate'))

    # --- 3. 繪製開孔 (Hole) ---
    if plate_params.get('has_hole', False):
        hole_shape = plate_params.get('hole_shape', 'rectangle')
        if hole_shape == 'rectangle':
            h_b, h_n = plate_params.get('b', 0) * conv, plate_params.get('n', 0) * conv
            ax.add_patch(
                patches.Rectangle((-h_b / 2 + e_x, -h_n / 2 + e_y), h_b, h_n, fill=True, color='white', ec='#adb5bd',
                                  lw=1, linestyle='--'))
        else:  # Circle or Octagon for hole
            inner_radius = plate_params.get('inner_radius', 0) * conv
            if hole_shape == 'circle':
                ax.add_patch(patches.Circle((e_x, e_y), inner_radius, fill=True, color='white', ec='#adb5bd', lw=1,
                                            linestyle='--'))
            else:  # Octagon
                angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 8, endpoint=False)
                verts = np.array([[inner_radius * np.cos(a) + e_x, inner_radius * np.sin(a) + e_y] for a in angles])
                ax.add_patch(patches.Polygon(verts, fill=True, color='white', ec='#adb5bd', lw=1, linestyle='--'))

    # --- 4. 繪製鋼柱 (Column) ---
    col_type = column_params.get('type', 'H-Shape').lower()
    col_props = {'fill': False, 'ec': '#343a40', 'lw': 2, 'zorder': 10}
    if col_type == 'h-shape':
        d, bf, tf, tw = [column_params.get(k, 0) * conv for k in ['d', 'bf', 'tf', 'tw']]
        ax.add_patch(patches.Rectangle((-bf / 2, d / 2 - tf), bf, tf, **col_props))
        ax.add_patch(patches.Rectangle((-bf / 2, -d / 2), bf, tf, **col_props))
        ax.add_patch(patches.Rectangle((-tw / 2, -d / 2 + tf), tw, d - 2 * tf, **col_props))
    elif col_type == 'tube':
        B, H = column_params.get('B', 0) * conv, column_params.get('H', 0) * conv
        ax.add_patch(patches.Rectangle((-B / 2, -H / 2), B, H, **col_props))
    elif col_type == 'pipe':
        D = column_params.get('D', 0) * conv
        ax.add_patch(patches.Circle((0, 0), D / 2, **col_props))

    # --- 5. 繪製錨栓 (Bolts) ---
    # [核心修改] 调用新的辅助函数来获取锚栓坐标
    bolt_coords = get_bolt_coordinates(plate_params, bolt_params) * conv
    if len(bolt_coords) > 0:
        bolts_np = np.array(bolt_coords)
        ax.plot(bolts_np[:, 0] + e_x, bolts_np[:, 1] + e_y, 'o', color='#f0ad4e', markersize=8,
                markeredgecolor='#d9534f', mew=1.5, label='Anchors')

    # --- 6. 設定圖表屬性 ---
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', linewidth=0.5)
    ax.set_title("幾何關係示意圖 (Geometric Layout)", fontsize=12)
    ax.set_xlabel(f'X-axis ({unit_label})')
    ax.set_ylabel(f'Y-axis ({unit_label})')
    ax.legend()

    # 設置顯示範圍
    padding = max(view_width, view_height) * 0.1
    ax.set_xlim(-view_width / 2 - padding, view_width / 2 + padding)
    ax.set_ylim(-view_height / 2 - padding, view_height / 2 + padding)

    plt.tight_layout()

    # 將圖片轉換為 Base64
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)

    return plot_base64


# [核心新增] 需要一個輔助函式來計算錨栓座標，我們可以從 perform_analysis 中提取
def get_bolt_coordinates_for_plot(plate_params, bolt_params):
    # ... (此處需要複製/貼上 perform_analysis 函式中 B. 螺栓佈置產生器 的所有邏輯) ...
    # ... 為了簡潔，這裡先省略，但在您的實際檔案中需要貼上 ...
    return []  # 暫時返回空列表

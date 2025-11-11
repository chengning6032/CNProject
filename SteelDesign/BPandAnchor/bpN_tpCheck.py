import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import base64
from .bpN_utils import safe_dc_ratio

# --- 常數定義 ---
IN_TO_CM = 2.54
KSI_TO_KGF_CM2 = 70.307


def perform_plate_bending_check(analysis_results, column_params, materials, plate_params, plate_fy_ksi, plate_tp_in,
                                phi_b=0.9, generate_plot=False, unit_system='imperial'):
    """
    執行基礎版彎曲強度檢核 (v2.5 - 修正八邊形附圖標示)。
    """
    print("\n--- 3. 開始執行基礎版彎曲檢核模組 (v2.5) ---")

    # A. 提取與驗證核心參數
    unit_system = unit_system
    analysis_status = analysis_results.get('status')
    bolt_coords = np.array(analysis_results.get('bolt_coords', []))
    bolt_forces = np.array(analysis_results.get('bolt_forces', []))
    grid_data = analysis_results.get('grid_data', {})
    grid_pressures = analysis_results.get('grid_pressures')
    fc_psi = materials.get('fc_psi', 3000)

    # [核心重構] 統一從 plate_params 提取基礎版尺寸
    plate_shape = plate_params.get('shape', 'rectangle')
    if plate_shape == 'rectangle':
        plate_B = plate_params.get('B', 0)
        plate_N = plate_params.get('N', 0)
    else:
        outer_radius = plate_params.get('outer_radius', 0)
        plate_B = plate_N = 2 * outer_radius


    has_pressure = False
    # 只有在分析模式為 Bearing 或 Full-Bearing 時，才可能存在壓力
    if analysis_status in ["Bearing", "Full-Bearing"]:
        # 再次確認 grid_pressures 確實是一個 NumPy 陣列
        if isinstance(grid_pressures, np.ndarray):
            # 使用 np.nan_to_num 將 nan 轉為 0，然後再用 np.any 判斷
            if np.any(np.nan_to_num(grid_pressures) > 1e-9):
                has_pressure = True

    has_tension = bolt_forces is not None and np.any(bolt_forces > 1e-9)

    if not has_pressure and not has_tension:
        return {'result': 'N/A', 'message': '無彎矩作用，不需檢核。'}


    # 確保 xv, yv 存在
    xv = grid_data.get('xv')
    yv = grid_data.get('yv')
    if xv is None or yv is None:
        return {'result': 'N/A', 'message': '缺少網格座標數據'}

    # cell_area 的計算也需要保護
    cell_area = 0
    if has_pressure and xv is not None and yv is not None:
         cell_area = grid_data.get('ca', (xv[0][1] - xv[0][0]) * (yv[1][0] - yv[0][0]) if len(xv) > 1 and len(yv) > 1 else 0)
    col_type = column_params.get('type', 'H-Shape').lower()
    m_crit_dist, n_crit_dist = 0, 0
    col_d, col_bf, tube_B, tube_H, pipe_D = [column_params.get(k, 0) for k in ['d', 'bf', 'B', 'H', 'D']]

    if col_type == 'h-shape':
        m_crit_dist = 0.8 * col_bf / 2.0
        n_crit_dist = 0.95 * col_d / 2.0
    elif col_type == 'tube':
        m_crit_dist = 0.95 * tube_B / 2.0
        n_crit_dist = 0.95 * tube_H / 2.0
    elif col_type == 'pipe':
        m_crit_dist = n_crit_dist = 0.8 * pipe_D / 2.0

    cantilevers = {
        'Right': {'axis': 'x', 'crit_line_pos': m_crit_dist, 'width': plate_N},
        'Left': {'axis': 'x', 'crit_line_pos': -m_crit_dist, 'width': plate_N},
        'Top': {'axis': 'y', 'crit_line_pos': n_crit_dist, 'width': plate_B},
        'Bottom': {'axis': 'y', 'crit_line_pos': -n_crit_dist, 'width': plate_B},
    }
    print("\n  計算各懸臂區域的需求彎矩 (Mu):")

    # [核心重构] 在所有情況下都計算幾何懸臂長度
    apothem = None
    if plate_shape == 'octagon':
        apothem = (plate_B / 2.0) * np.cos(np.pi / 8)
        m_geom = apothem - m_crit_dist
        n_geom = apothem - n_crit_dist
    else:
        m_geom = (plate_B / 2.0) - m_crit_dist
        n_geom = (plate_N / 2.0) - n_crit_dist

    cantilever_results = []
    max_mu_per_inch = 0.0  # <-- 初始化在這裡，是正確的
    lambda_info = {'status': 'Not Applicable'}

    if col_type == 'h-shape' and analysis_status == 'Full-Bearing':
        Pu_total = np.sum(np.array(grid_pressures)[~np.isnan(grid_pressures)]) * cell_area
        phi_c, A1 = 0.65, plate_B * plate_N
        Pp = 0.85 * (fc_psi / 1000.0) * A1
        X_geom = (4 * col_d * col_bf) / ((col_d + col_bf) ** 2) if (col_d + col_bf) > 0 else 0
        X = X_geom * (Pu_total / (phi_c * Pp) if (phi_c * Pp) > 0 else 1.0)
        lambda_val = min((2 * np.sqrt(X)) / (1 + np.sqrt(1 - X)), 1.0) if 0 <= X < 1.0 else 1.0
        n_prime = np.sqrt(col_d * col_bf) / 4.0 if (col_d * col_bf) >= 0 else 0
        lambda_info = {
            'X': X,
            'lambda': lambda_val,
            'n_prime': n_prime,
            'l_lambda': lambda_val * n_prime,
            'm_geom': m_geom, 'n_geom': n_geom,
            'Pu_calc': Pu_total,
            'phi_c_calc': phi_c,
            'Pp_calc': Pp,
            'status': 'Calculated'
        }

    # D. 遍歷四個懸臂區域，計算彎矩
    for name, params in cantilevers.items():
        axis, crit_line = params['axis'], params['crit_line_pos']
        pressure_moment_num, bolt_moment_num = 0.0, 0.0

        # 壓力彎矩
        if has_pressure:
            mask = (np.sign(xv) == np.sign(crit_line)) & (abs(np.array(xv)) >= abs(crit_line)) & (
                ~np.isnan(grid_pressures)) if axis == 'x' else (np.sign(yv) == np.sign(crit_line)) & (
                    abs(np.array(yv)) >= abs(crit_line)) & (~np.isnan(grid_pressures))
            points = np.array(xv)[mask] if axis == 'x' else np.array(yv)[mask]
            pressures = np.array(grid_pressures)[mask]
            lever_arms = np.abs(points - crit_line)
            pressure_moment_num = np.sum(pressures * cell_area * lever_arms)

        # 錨栓拉力彎矩
        for i, (bx, by) in enumerate(bolt_coords):
            if bolt_forces[i] > 1e-9:
                point, is_in_cantilever = (bx, True) if axis == 'x' and np.sign(bx) == np.sign(crit_line) and abs(
                    bx) >= abs(crit_line) else (by, True) if axis == 'y' and np.sign(by) == np.sign(crit_line) and abs(
                    by) >= abs(crit_line) else (0, False)
                if is_in_cantilever:
                    bolt_moment_num += bolt_forces[i] * abs(point - crit_line)

        total_moment_numerical = pressure_moment_num + bolt_moment_num
        mu_per_inch_numerical = total_moment_numerical / params['width'] if params['width'] > 0 else 0

        # --- D2. (僅限H型鋼) 解析法彎矩 ---
        final_mu_per_inch = mu_per_inch_numerical
        calc_method = "Numerical Integration"

        if col_type == 'h-shape' and analysis_status == 'Full-Bearing':
            l_lambda = lambda_info.get('l_lambda', 0)
            geom_cantilever_len = lambda_info['m_geom'] if axis == 'x' else lambda_info['n_geom']
            eff_cantilever_len = max(geom_cantilever_len, l_lambda)
            Pu_total = lambda_info.get('Pu_calc', 0)
            A1 = plate_B * plate_N
            avg_pressure = Pu_total / A1 if A1 > 0 else 0
            width = params['width']
            total_moment_lambda = avg_pressure * width * (eff_cantilever_len ** 2) / 2.0
            mu_per_inch_lambda = total_moment_lambda / width if width > 0 else 0

            if mu_per_inch_lambda > final_mu_per_inch:
                final_mu_per_inch = mu_per_inch_lambda
                calc_method = f"Lambda Method (l_eff={eff_cantilever_len:.3f} in)"

        if final_mu_per_inch > max_mu_per_inch: max_mu_per_inch = final_mu_per_inch
        cantilever_results.append(
            {'name': name, 'mu_per_inch': final_mu_per_inch, 'total_moment': final_mu_per_inch * params['width'],
             'calc_method': calc_method, 'crit_line_pos': crit_line, 'width': params['width']})

    # F. 繪圖
    plot_base64 = None
    if generate_plot:
        length_unit = 'cm' if unit_system == 'mks' else 'in'
        length_conv = IN_TO_CM if unit_system == 'mks' else 1.0

        fig, ax = plt.subplots(figsize=(8, 8))

        # --- 1. 建立基礎版 Patch 用於裁切和繪製邊框 ---
        plate_clip_patch = None
        if plate_shape == 'rectangle':
            B_plot, N_plot = plate_B * length_conv, plate_N * length_conv
            plate_clip_patch = patches.Rectangle((-B_plot / 2, -N_plot / 2), B_plot, N_plot, fill=False,
                                                 transform=ax.transData)
        else:
            radius_plot = (plate_B / 2.0) * length_conv
            if plate_shape == 'circle':
                plate_clip_patch = patches.Circle((0, 0), radius_plot, fill=False, transform=ax.transData)
            elif plate_shape == 'octagon':
                angles = np.linspace(np.pi / 8, 2 * np.pi + np.pi / 8, 9)
                octagon_verts = np.array([[radius_plot * np.cos(a), radius_plot * np.sin(a)] for a in angles])
                plate_clip_patch = patches.Polygon(octagon_verts, fill=False, closed=True, transform=ax.transData)

        if plate_clip_patch:
            ax.add_patch(plate_clip_patch)

        # --- 2. 繪製壓應力分佈 ---
        if has_pressure:
            plot_pressures = np.array(grid_pressures)
            plot_xv = np.array(xv) * length_conv
            plot_yv = np.array(yv) * length_conv
            levels = np.linspace(np.nanmax(plot_pressures) / 20, np.nanmax(plot_pressures), 20)
            contour = ax.contourf(plot_xv, plot_yv, plot_pressures, cmap='Blues', levels=levels, extend='max')
            if plate_clip_patch:
                contour.set_clip_path(plate_clip_patch)

        # --- 3. 繪製鋼柱形狀 ---
        col_props = {'fill': False, 'edgecolor': '#343a40', 'linewidth': 2, 'zorder': 10}
        if col_type == 'h-shape':
            d, bf, tf, tw = [c * length_conv for c in
                             [col_d, col_bf, column_params.get('tf', 0), column_params.get('tw', 0)]]
            ax.add_patch(patches.Rectangle((-bf / 2, d / 2 - tf), bf, tf, **col_props))
            ax.add_patch(patches.Rectangle((-bf / 2, -d / 2), bf, tf, **col_props))
            ax.add_patch(patches.Rectangle((-tw / 2, -d / 2 + tf), tw, d - 2 * tf, **col_props))
        elif col_type == 'tube':
            B, H = tube_B * length_conv, tube_H * length_conv
            ax.add_patch(patches.Rectangle((-B / 2, -H / 2), B, H, **col_props))
        elif col_type == 'pipe':
            D = pipe_D * length_conv
            ax.add_patch(patches.Circle((0, 0), D / 2, **col_props))

        # --- 4. 繪製基礎版邊框 ---
        if plate_clip_patch:
            plate_clip_patch.set_fill(False);
            plate_clip_patch.set_edgecolor('black');
            plate_clip_patch.set_linewidth(1.5);
            plate_clip_patch.set_zorder(5)

        # --- 5. 繪製錨栓 ---
        if bolt_coords.size > 0:
            plot_bolt_coords = bolt_coords * length_conv
            ax.scatter(plot_bolt_coords[:, 0], plot_bolt_coords[:, 1], edgecolor='black', facecolor='gray', s=80,
                       alpha=0.7, zorder=12)

        # --- 6. 繪製中性軸 ---
        solution = analysis_results.get('solution')
        if solution and analysis_status == 'Bearing':
            epsilon_c, theta_y, theta_x = solution
            if abs(theta_x) > 1e-9 or abs(theta_y) > 1e-9:
                x_lim_plot = np.array(ax.get_xlim())
                y_lim_plot = np.array(ax.get_ylim())
                if abs(theta_x) > abs(theta_y):
                    y_na = (-theta_y * (x_lim_plot / length_conv) - epsilon_c) / theta_x * length_conv
                    ax.plot(x_lim_plot, y_na, 'k--', lw=1.5, label='Neutral Axis (NA)', zorder=20)
                else:
                    x_na = (-theta_x * (y_lim_plot / length_conv) - epsilon_c) / theta_y * length_conv
                    ax.plot(x_na, y_lim_plot, 'k--', lw=1.5, label='Neutral Axis (NA)', zorder=20)

        # --- 7. 繪製臨界斷面線 ---
        if m_crit_dist > 0:
            ax.axvline(x=m_crit_dist * length_conv, color='r', linestyle='--', lw=2,
                       label=f'm-m (x={m_crit_dist * length_conv:.2f} {length_unit})')
            ax.axvline(x=-m_crit_dist * length_conv, color='r', linestyle='--', lw=2)
        if n_crit_dist > 0:
            ax.axhline(y=n_crit_dist * length_conv, color='g', linestyle='-.', lw=2,
                       label=f'n-n (y={n_crit_dist * length_conv:.2f} {length_unit})')
            ax.axhline(y=-n_crit_dist * length_conv, color='g', linestyle='-.', lw=2)

        # --- 8. 設定圖形屬性 ---
        ax.set_aspect('equal')
        ax.set_title("Bending Check Critical Sections", fontsize=14)
        ax.set_xlabel(f'X-axis ({length_unit})')
        ax.set_ylabel(f'Y-axis ({length_unit})')
        ax.legend(fontsize=12)
        ax.grid(True, linestyle=':', linewidth=0.5)

        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120)
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

    # G. 進行檢核並回傳

    Mn_per_inch = plate_fy_ksi * (plate_tp_in ** 2) / 4.0
    phi_Mn_per_inch = phi_b * Mn_per_inch
    dc_ratio = max_mu_per_inch / phi_Mn_per_inch if phi_Mn_per_inch > 0 else float('inf')

    plate_tp = plate_tp_in
    plate_fy = plate_fy_ksi
    Mn = Mn_per_inch
    phi_Mn = phi_Mn_per_inch
    if unit_system == "mks":
        plate_tp = plate_tp_in * IN_TO_CM
        plate_fy = plate_fy_ksi * KSI_TO_KGF_CM2
        Mn = plate_fy * (plate_tp ** 2) / 4.0 / 1000
        phi_Mn = phi_b * Mn





    radius = plate_B / 2.0 if plate_shape in ['circle', 'octagon'] else None
    return {"result": "PASS" if dc_ratio <= 1.0 else "FAIL", "dc_ratio": dc_ratio, "max_Mu": max_mu_per_inch,
            "phi_Mn": phi_Mn_per_inch, "cantilever_calcs": cantilever_results, "m_crit_dist": m_crit_dist,
            "n_crit_dist": n_crit_dist, "m_geom": m_geom, "n_geom": n_geom, "apothem": apothem,
            "lambda_info": lambda_info, "col_params": column_params, "plate_params": plate_params, "plate_B": plate_B,
            "plate_N": plate_N, "phi_b": phi_b,
            "Fy": plate_fy,
            "tp": plate_tp,
            "radius": radius,
            "plot_base64": plot_base64}

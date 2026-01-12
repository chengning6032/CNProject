from django.shortcuts import render
import math
import numpy as np
from scipy.interpolate import RectBivariateSpline
import traceback


# ==========================================
# 1. 工具類別與力學輔助函式 (保持不變)
# ==========================================

class CaquotKeriselCalculator:
    def __init__(self):
        self.phis = np.array([10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60])
        self.ratios = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        raw_table = [
            [1.000, 0.991, 0.989, 0.978, 0.962, 0.946, 0.929, 0.912, 0.898, 0.881, 0.864],
            [1.000, 0.986, 0.979, 0.961, 0.934, 0.907, 0.881, 0.854, 0.830, 0.803, 0.775],
            [1.000, 0.983, 0.968, 0.939, 0.901, 0.862, 0.824, 0.787, 0.752, 0.716, 0.678],
            [1.000, 0.980, 0.954, 0.912, 0.860, 0.808, 0.759, 0.711, 0.666, 0.620, 0.574],
            [1.000, 0.980, 0.937, 0.878, 0.811, 0.746, 0.686, 0.627, 0.574, 0.520, 0.467],
            [1.000, 0.980, 0.916, 0.836, 0.752, 0.674, 0.603, 0.536, 0.475, 0.417, 0.362],
            [1.000, 0.980, 0.886, 0.783, 0.682, 0.592, 0.512, 0.439, 0.375, 0.316, 0.262],
            [1.000, 0.979, 0.848, 0.718, 0.600, 0.500, 0.414, 0.339, 0.276, 0.221, 0.174],
            [1.000, 0.975, 0.797, 0.638, 0.506, 0.399, 0.313, 0.242, 0.185, 0.138, 0.102],
            [1.000, 0.966, 0.731, 0.543, 0.401, 0.295, 0.215, 0.153, 0.108, 0.0737, 0.0492],
            [1.000, 0.948, 0.647, 0.434, 0.290, 0.193, 0.127, 0.0809, 0.0505, 0.0301, 0.0178]
        ]
        self.Rp_grid = np.array([row[::-1] for row in raw_table])
        self.spline = RectBivariateSpline(self.phis, self.ratios, self.Rp_grid, kx=3, ky=3)

    def calculate_Kp(self, phi_deg, delta_deg):
        phi, delta = math.radians(phi_deg), math.radians(delta_deg)
        num = math.pow(math.cos(phi), 2)
        den = math.cos(delta) * math.pow(
            1 - math.sqrt(max(0, math.sin(phi + delta) * math.sin(phi) / (math.cos(delta)))), 2)
        kp_c = num / den if den != 0 else 1.0
        ratio = delta_deg / phi_deg if phi_deg != 0 else 0
        Rp = float(self.spline(max(10, min(60, phi_deg)), max(0, min(1, ratio)), grid=False))
        return kp_c * Rp


def calculate_Mononobe_Okabe_Kae(phi_deg, delta_deg, alpha_deg, theta_rad, kh, kv):
    phi, delta, alpha = math.radians(phi_deg), math.radians(delta_deg), math.radians(alpha_deg)
    psi = math.atan(kh / (1 - kv)) if (1 - kv) != 0 else 0
    num = math.pow(math.cos(phi - theta_rad - psi), 2)
    den = math.cos(psi) * math.pow(math.cos(theta_rad), 2) * math.cos(delta + theta_rad + psi)
    sqrt_v = math.sqrt(max(0, math.sin(phi + delta) * math.sin(phi - psi - alpha) / (
            math.cos(delta + theta_rad + psi) * math.cos(theta_rad - alpha))))
    return num / (den * math.pow(1 + sqrt_v, 2)) if den != 0 else 1.0


def calculate_Mononobe_Okabe_Kpe(phi_deg, delta_deg, alpha_deg, theta_rad, kh, kv):
    phi, delta, alpha = math.radians(phi_deg), math.radians(delta_deg), math.radians(alpha_deg)
    psi = math.atan(kh / (1 - kv)) if (1 - kv) != 0 else 0
    num = math.pow(math.cos(phi + theta_rad - psi), 2)
    den = math.cos(psi) * math.pow(math.cos(theta_rad), 2) * math.cos(delta - theta_rad + psi)
    sqrt_v = math.sqrt(max(0, math.sin(phi + delta) * math.sin(phi - psi + alpha) / (
            math.cos(delta - theta_rad + psi) * math.cos(alpha - theta_rad))))
    return num / (den * math.pow(1 - sqrt_v, 2)) if den != 0 else 1.0


def calculate_spec_integrated_surcharge_with_moment(load_type, q_val, X_start, Hs, D_load, B_width=0):
    if q_val <= 0 or Hs <= 0: return 0.0, 0.0
    num_z_slices = 100
    start_z = max(0, D_load)
    dz = (Hs - start_z) / num_z_slices
    total_Ph, total_Mo = 0, 0
    num_x_slices = 20 if B_width > 0 else 1
    dx = B_width / num_x_slices
    for i in range(num_z_slices):
        z_abs = start_z + (i + 0.5) * dz
        n = z_abs / Hs
        sig_h_at_z = 0
        for j in range(num_x_slices):
            curr_x = X_start + (j + 0.5) * dx if B_width > 0 else X_start
            m = curr_x / Hs
            dq = (q_val * dx) if B_width > 0 else q_val
            if load_type == 'line_or_strip':
                if m <= 0.4:
                    sig_seg = (dq / Hs) * (0.2 * n) / ((0.16 + n ** 2) ** 2)
                else:
                    sig_seg = (dq / Hs) * (1.28 * m ** 2 * n) / (((m ** 2) + (n ** 2)) ** 2)
            else:
                if m <= 0.4:
                    sig_seg = (dq / Hs ** 2) * (0.28 * n ** 2) / ((0.16 + n ** 2) ** 3)
                else:
                    sig_seg = (dq / Hs ** 2) * (1.77 * m ** 2 * n ** 2) / ((m ** 2 + n ** 2) ** 3)
            sig_h_at_z += sig_seg
        force_inc = sig_h_at_z * dz
        total_Ph += force_inc
        total_Mo += force_inc * (Hs - z_abs)
    return total_Ph, total_Mo


def get_float(val, default=0.0):
    try:
        return float(val) if val and str(val).strip() else default
    except:
        return default


# ==========================================
# 2. 核心計算引擎 (Engine)
# ==========================================

def calculate_retaining_wall_core(p):
    """
    執行所有物理與土力學計算，返回包含所有數字結果的 engine 字典。
    """
    ck_calc = CaquotKeriselCalculator()

    # 確保轉換為公尺 (因 p 傳進來可能是公分)
    h_s = p['H_stem'] / 100.0
    h_bp = p['H_bp'] / 100.0
    l_f = p['L_bp_front'] / 100.0
    l_h = p['L_bp_back'] / 100.0
    t_top = p['t_stem_top'] / 100.0
    w_f = p['w_stem_front'] / 100.0
    w_b = p['w_stem_back'] / 100.0
    gamma_c = p['gamma_c']

    alpha_deg = p['alpha_soil']

    # 幾何定義
    B_total = l_f + (w_f + t_top + w_b) + l_h
    Hs = h_s + h_bp + (l_h + w_b) * math.tan(math.radians(p['alpha_soil']))
    theta_rad = math.atan(p['w_stem_back'] / p['H_stem']) if p['H_stem'] > 0 else 0
    omega_s_rad = math.radians(p['delta_wall']) + theta_rad
    omega_s_deg = math.degrees(omega_s_rad)
    psi_rad = math.atan(p['kh'] / (1 - p['kv'])) if (1 - p['kv']) != 0 else 0

    # 係數計算
    Ka = calculate_Mononobe_Okabe_Kae(p['phi_soil'], p['delta_wall'], p['alpha_soil'], theta_rad, 0, 0)
    Kae = calculate_Mononobe_Okabe_Kae(p['phi_soil'], p['delta_wall'], p['alpha_soil'], theta_rad, p['kh'], p['kv'])

    # 3. 被動側係數 (核心修正：補足 Kpe_f)
    Kp_f = ck_calc.calculate_Kp(p['phi_soil_front'], p['phi_soil_front'] / 2.0)
    Kpe_f = calculate_Mononobe_Okabe_Kpe(p['phi_soil_front'], p['phi_soil_front'] / 2.0, 0, 0, p['kh'], p['kv'])

    Kp_base = ck_calc.calculate_Kp(p['phi_soil_base'], p['phi_soil_base'] * 0.67)
    Kpe_base = calculate_Mononobe_Okabe_Kpe(p['phi_soil_base'], p['phi_soil_base'] * 0.67, 0, 0, p['kh'], p['kv'])

    # 垂直力與土重 (考量水位)
    H_water_input = p['H_water'] / 100.0
    h_w_s = max(0, min(h_s + h_bp, H_water_input))
    h_dry = Hs - h_w_s

    # [計算 Page 7 中間值]
    sig_v_wat_val = p['gamma_soil'] * h_dry
    sig_v_bot_val = sig_v_wat_val + (p['gamma_sat'] - 1.0) * h_w_s if h_w_s > 0 else p['gamma_soil'] * Hs
    pa_top_val = 0.0
    pa_wat_val = Ka * sig_v_wat_val
    pa_bot_val = Ka * sig_v_bot_val
    p1_area = 0.5 * (pa_top_val + pa_wat_val) * h_dry
    p2_area = 0.5 * (pa_wat_val + pa_bot_val) * h_w_s if h_w_s > 0 else 0
    P_total_area_sum = p1_area + p2_area

    Pa_H = P_total_area_sum * math.cos(omega_s_rad)  # (假設 P_total_area_sum 已算好)
    Pa_V = P_total_area_sum * math.sin(omega_s_rad)
    Pw_total = 0.5 * 1.0 * h_w_s ** 2
    Pw_H = Pw_total * math.cos(theta_rad)

    # 垂直力與 Mr (為 Page 9 準備清單)
    # =========================================================================
    # [A] 結構自重明細詳算 (考慮變斷面)
    # =========================================================================
    struct_blocks = []
    # 1. 牆身主體 (矩形部分)
    val1 = t_top * h_s * gamma_c
    struct_blocks.append({
        'name': '牆身主體 (矩形)',
        'formula': f"{t_top:.2f} \\times {h_s:.2f} \\times {gamma_c}",
        'val': val1
    })
    # 2. 牆前傾斜部分 (三角形)
    val2 = 0.5 * w_f * h_s * gamma_c
    struct_blocks.append({
        'name': '牆前傾斜部 (三角形)',
        'formula': f"0.5 \\times {w_f:.2f} \\times {h_s:.2f} \\times {gamma_c}",
        'val': val2
    })
    # 3. 牆背傾斜部分 (三角形)
    val3 = 0.5 * w_b * h_s * gamma_c
    struct_blocks.append({
        'name': '牆背傾斜部 (三角形)',
        'formula': f"0.5 \\times {w_b:.2f} \\times {h_s:.2f} \\times {gamma_c}",
        'val': val3
    })
    # 4. 基礎底版 (矩形)
    val4 = B_total * h_bp * gamma_c
    struct_blocks.append({
        'name': '基礎底版',
        'formula': f"{B_total:.2f} \\times {h_bp:.2f} \\times {gamma_c}",
        'val': val4
    })
    N_weight_sum = sum(b['val'] for b in struct_blocks)

    # =========================================================================
    # [B] 回填土重明細詳算 (考慮水位分層與楔形幾何)
    # =========================================================================
    soil_layers = []
    # 輔助變數
    h_ws = max(0, min(h_s, H_water_input - h_bp))  # 版頂起算之水位高
    h_ds = h_s - h_ws  # 乾土高度

    # 1. 牆踵上方主土體 (矩形 L_h 範圍)
    if h_ds > 0:
        val_s1 = l_h * h_ds * p['gamma_soil']
        soil_layers.append(
            {'name': '牆踵回填土 (乾)', 'val': val_s1,
             'formula': f"{l_h:.2f} \\times {h_ds:.2f} \\times {p['gamma_soil']}"})
    if h_ws > 0:
        val_s2 = l_h * h_ws * p['gamma_sat']
        soil_layers.append(
            {'name': '牆踵回填土 (淹)', 'val': val_s2,
             'formula': f"{l_h:.2f} \\times {h_ws:.2f} \\times {p['gamma_sat']}"})

    # 2. 牆背傾斜上方楔形土 (w_b 範圍)
    # 由於牆身通常是下寬上窄，牆背上方土體在牆身底部寬為 0, 牆頂寬為 w_b
    if w_b > 0:
        # 計算水位處的楔形寬度 (相似三角形)
        # 此處假設三角形頂寬 w_b, 底尖 0 (依照您 SVG 的幾何)
        w_at_wat = w_b * (h_ws / h_s) if h_s > 0 else 0

        # 地下水位面以下 (底部尖端三角形)
        if h_ws > 0:
            val_s3_sub = (0.5 * w_at_wat * h_ws) * p['gamma_sat']
            soil_layers.append({
                'name': '牆背楔形土 (淹-三)',
                'formula': f"0.5 \\times {w_at_wat:.2f} \\times {h_ws:.2f} \\times {p['gamma_sat']}",
                'val': val_s3_sub
            })
        # 地下水位面以上 (頂部梯形)
        if h_ds > 0:
            val_s3_dry = (0.5 * (w_b + w_at_wat) * h_ds) * p['gamma_soil']
            soil_layers.append({
                'name': '牆背楔形土 (乾-梯)',
                'formula': f"0.5 \\times ({w_b:.2f} + {w_at_wat:.2f}) \\times {h_ds:.2f} \\times {p['gamma_soil']}",
                'val': val_s3_dry
            })

    # 3. 地表傾斜部分回填土 (Alpha 坡度)
    # 總投影寬度 W = L_h + w_b
    W_slope = l_h + w_b
    if alpha_deg > 0:
        h_alpha = W_slope * math.tan(math.radians(alpha_deg))
        # 判斷水位是否影響地表楔形 (通常水位在牆頂以下，坡度區全乾)
        # 如果水位高於牆頂 H_stem
        h_water_above_stem = max(0, (H_water_input - h_bp) - h_s)

        if h_water_above_stem > 0:
            # 坡度區下部梯形(淹), 上部三角形(乾)
            w_cut = W_slope * (1 - h_water_above_stem / h_alpha) if h_alpha > 0 else 0
            val_s4_sub = 0.5 * (W_slope + w_cut) * h_water_above_stem * p['gamma_sat']
            val_s4_dry = 0.5 * w_cut * (h_alpha - h_water_above_stem) * p['gamma_soil']
            soil_layers.append(
                {'name': '地表坡度土 (淹-梯)', 'val': val_s4_sub, 'formula': f"梯形幾何積分 \\times {p['gamma_sat']}"})
            soil_layers.append(
                {'name': '地表坡度土 (乾-三)', 'val': val_s4_dry,
                 'formula': f"三角形幾何積分 \\times {p['gamma_soil']}"})
        else:
            # 全乾三角形
            val_s4 = 0.5 * W_slope * h_alpha * p['gamma_soil']
            soil_layers.append({'name': '地表坡度土 (乾-三)',
                                'formula': f"0.5 \\times {W_slope:.2f} \\times {h_alpha:.2f} \\times {p['gamma_soil']}",
                                'val': val_s4})

    # 4. 主動側力垂直分量 (納入土重明細合計)
    soil_layers.append({
        'name': '主動側力垂直分量 (Pav)',
        'formula': f"{P_total_area_sum:.2f} \\times \\sin({omega_s_deg:.2f}^\\circ)",
        'val': Pa_V
    })

    N_soil_sum = sum(s['val'] for s in soil_layers)

    # --- [D] 超載詳算 (垂直與水平) ---
    is_uni = p.get('enable_uniform') == 'on'
    is_point = p.get('enable_point') == 'on'
    is_strip = p.get('enable_strip') == 'on'

    qu_total = p['q_uniform_dead'] + p['q_uniform_live']
    W_q_width = l_h + w_b
    V_uni = qu_total * W_q_width if is_uni else 0
    qp_total = p['q_point_dead'] + p['q_point_live']
    V_point = (qp_total) if (is_point and p['point_x'] <= l_h) else 0
    qs_total = p['q_strip_dead'] + p['q_strip_live']
    V_strip = (qs_total) * p['strip_width'] if (is_strip and p['strip_x'] <= l_h) else 0

    V_ext_total_sum = V_uni + V_point + V_strip

    # 水平推力
    Pqh_ASD = (Ka * qu_total * Hs) * math.cos(omega_s_rad) if is_uni else 0
    Pph_ASD, Mph_ASD = calculate_spec_integrated_surcharge_with_moment('point', (p['q_point_dead'] + p['q_point_live']),
                                                                       p['point_x'], Hs,
                                                                       p['point_depth'] / 100) if is_point else (0, 0)
    Psh_ASD, Msh_ASD = calculate_spec_integrated_surcharge_with_moment('line_or_strip',
                                                                       (p['q_strip_dead'] + p['q_strip_live']),
                                                                       p['strip_x'], Hs, p['strip_depth'] / 100,
                                                                       p['strip_width']) if is_strip else (0, 0)

    # --- [E] 穩定性總結 ---
    PwH_val = 0.5 * 1.0 * h_w_s ** 2 * math.cos(theta_rad)
    F_driving_static = Pa_H + PwH_val + Pqh_ASD + Pph_ASD + Psh_ASD
    U_uplift = 1.0 * h_w_s * B_total
    N_prime = N_weight_sum + N_soil_sum + V_ext_total_sum - U_uplift

    # 被動抗力 (Page 10)
    h_eff_f = h_bp if p['ignore_h_front'] == 'on' else (p['H_soil_front'] / 100.0 + h_bp)
    Pp_f = 0.5 * p['gamma_soil_front'] * (
        h_bp ** 2 if p['ignore_h_front'] == 'on' else (p['H_soil_front'] / 100 + h_bp) ** 2) * Kp_f
    F_resist_static = N_prime * p['friction_coeff'] + Pp_f
    FS_slide = F_resist_static / F_driving_static if F_driving_static > 0 else 0

    # --- [F] 地震工況 ---
    kh = p['kh']
    kv = p['kv']
    Fiw = round(N_weight_sum * kh, 2)

    # 1. 地震土壓力增量 (依照規範 7.3.4 分層)
    # 使用 (1-kv) 折減垂直重，KaE 使用 Kae
    sig_v_mid_dyn = (p['gamma_soil'] * h_dry) * (1 - p['kv'])
    sig_v_bot_dyn = sig_v_mid_dyn + (p['gamma_sat'] - 1.0) * h_w_s * (1 - p['kv'])

    pae_mid_dyn = Kae * sig_v_mid_dyn
    pae_bot_dyn = Kae * sig_v_bot_dyn

    P_AE_dry = 0.5 * pae_mid_dyn * h_dry
    P_AE_sub = 0.5 * (pae_mid_dyn + pae_bot_dyn) * h_w_s
    P_AE_total = P_AE_dry + P_AE_sub

    Delta_Pae = P_AE_total - P_total_area_sum
    Delta_Pae_H = Delta_Pae * math.cos(omega_s_rad)
    Delta_Pae_V = Delta_Pae * math.sin(omega_s_rad)

    # 2. 動態水壓力增量 (Westergaard) - 規範 7.3.6
    Delta_Pwe = (7 / 12) * p['kh'] * 1.0 * (h_w_s ** 2)

    F_driving_dyn = F_driving_static + Delta_Pae_H + Delta_Pwe + Fiw
    N_prime_dyn = (N_weight_sum + N_soil_sum + V_ext_total_sum - Pa_V) * (1 - p['kv']) + Pa_V + Delta_Pae_V - U_uplift
    FS_slide_dyn = (N_prime_dyn * p['friction_coeff'] + (
                F_resist_static - N_prime * p['friction_coeff']) * 0.8) / F_driving_dyn

    sig_p_top, sig_p_bot, Pp_sk = 0, 0, 0
    if p['H_sk'] > 0:
        H_sk_m = p['H_sk'] / 100.0
        q_base = p['gamma_soil_front'] * h_eff_f
        sig_p_top = Kp_base * q_base
        sig_p_bot = Kp_base * (q_base + p['gamma_soil_base'] * H_sk_m)
        Pp_sk = 0.5 * (sig_p_top + sig_p_bot) * H_sk_m



    # (暫時模擬穩定性分析結果)
    # 之後你完成第 4-6 章的邏輯也請放在這裡算出數字
    stability_results = {
        'fs_slide_static': 1.65,
        'fs_slide_dyn': 1.25,
        'fs_over_static': 2.10,
        'fs_over_dyn': 1.55,
        'ecc_static': 0.12,
        'ecc_dyn': 0.25,
        'q_toe_static': 12.5,
        'q_toe_dyn': 18.2
    }

    return {
        'Hs': Hs, 'h_w_s': h_w_s, 'h_dry': h_dry, 'B_total': B_total, 'H_sk_m': H_sk_m,
        'sig_v_wat_val': sig_v_wat_val, 'sig_v_bot_val': sig_v_bot_val,
        'pa_top_val': pa_top_val, 'pa_wat_val': pa_wat_val, 'pa_bot_val': pa_bot_val,
        'p1_area': p1_area, 'p2_area': p2_area, 'P_total_area_sum': P_total_area_sum,
        'omega_s_deg': math.degrees(omega_s_rad), 'Pa_H': Pa_H, 'Pa_V': Pa_V,
        'PwH_val': Pw_H, 'Pw_total_ASD': Pw_total,
        'Pqh_ASD': Pqh_ASD,
        'Pph_ASD': Pph_ASD,
        'Psh_ASD': Psh_ASD,
        'F_driving_static': F_driving_static,
        'N_weight_sum': N_weight_sum,
        'N_soil_sum': N_soil_sum,
        'V_ext_total_sum': V_ext_total_sum,
        'N_prime': N_prime,
        'U_uplift': U_uplift,
        'F_resist_static': F_resist_static,
        'Pp_f': Pp_f, 'Pp_sk': Pp_sk, 'Pp_total': Pp_f + Pp_sk, 'h_eff_f': h_eff_f,
        'sig_p_top': sig_p_top, 'sig_p_bot': sig_p_bot,
        'Ka': Ka,
        'Kae': Kae,
        'Kp_f': Kp_f,
        'Kpe_f': Kpe_f,  # 修正 KeyError 的關鍵點
        'Kp_base': Kp_base,
        'Kpe_base': Kpe_base,
        'phi_soil_front': p['phi_soil_front'],  # 供格式化器使用
        'phi_soil_base': p['phi_soil_base'],  # 供格式化器使用
        'q_uniform': qu_total,
        'W_q_width': W_q_width,
        'V_uni': V_uni,
        'point_m': p.get('point_x', 0) / Hs if Hs > 0 else 0,
        'qp_total': qp_total,
        'V_point': V_point,
        'V_strip': V_strip,
        'strip_x_end': 0,
        'qs_total': qs_total,
        'struct_blocks': struct_blocks, 'soil_layers': soil_layers, 'v_ext_items': [],
        # ASD 穩定性與係數 (延續之前)
        'theta_deg': math.degrees(theta_rad), 'psi_deg': math.degrees(psi_rad),
        'FS_slide': F_resist_static / F_driving_static,
        'FS_over': 2.1, 'ecc': 0.1,
        'FS_slide_dyn': 1.25,
        'kh': kh, 'kv': kv,
        "Fiw": Fiw,
        'F_driving_dyn': F_driving_static * 1.2,
        'N_prime_dyn': N_prime, 'F_iw': 1.0, 'Delta_Pae_H': 0.5, 'Delta_Pae_V': 0.1, 'F_resist_dyn': F_resist_static,
        'N_soil_only': N_soil_sum - Pa_V,
        'mu': p['friction_coeff'],
        **stability_results
    }


# ==========================================
# 2. 章節 Context 生成器 (Chapter Handlers)
# ==========================================

def get_ch1_summary_context(engine):
    """第 1 章：總覽與檢核摘要"""
    return {
        'Hs_m': round(engine['Hs'], 2),  # 公尺顯示 (3.91)
        'B_total_cm': round(engine['B_total'] * 100, 2),  # 轉回公分顯示 (360.00)
        'Ka': round(engine['Ka'], 4),
        'Kae': round(engine['Kae'], 4),
        'Kp_f': round(engine['Kp_f'], 4),
        'Kp_base': round(engine['Kp_base'], 4),
        'stability': {
            'FS_slide': engine['fs_slide_static'],
            'FS_over': engine['fs_over_static'],
            'Eccentricity': round(engine['ecc_static'], 3),
        },
        'seismic_details': {
            'FS_slide_dyn': engine['fs_slide_dyn'],
            'is_safe_dyn': engine['fs_slide_dyn'] >= 1.2
        },
        'seismic_over_details': {
            'FS_over_dyn': engine['fs_over_dyn'],
            'is_safe_over_dyn': engine['fs_over_dyn'] >= 1.5
        },
        'bearing_details': {
            'FS_bearing': 3.20,  # 暫定
            'is_safe_e': engine['ecc_static'] <= engine['B_total'] / 6
        },
        'bearing_dyn_details': {
            'FS_bearing_dyn': 2.15,  # 暫定
            'ecc_dyn': engine['fs_over_dyn'],
            'is_safe_q_dyn': True
        }
    }


def get_ch2_properties_context(engine, post_dict):
    """第 2 章：基本性質與模型 (包含 SVG 數據)"""
    return {
        'input_data': post_dict,
        'B_total_cm': f"{engine['B_total'] * 100:.1f}",  # 同步修正為 360.0
    }


def get_ch3_coefficients_context(engine):
    """第 3 章：設計參數詳細計算"""
    return {
        'theta_deg': round(engine['theta_deg'], 2),
        'psi_deg': round(engine['psi_deg'], 2),
        'Ka': round(engine['Ka'], 4),
        'Kae': round(engine['Kae'], 4),
        'Kp_f': round(engine['Kp_f'], 4),
        'Kpe_f': round(engine['Kpe_f'], 4),
        'Kp_base': round(engine['Kp_base'], 4),
        'Kpe_base': round(engine['Kpe_base'], 4),
        # 強制修正：傳遞 MathJax 代值所需的細部參數
        'phi_f_half': round(engine['phi_soil_front'] / 2.0, 1),
        'phi_b_corr': round(engine['phi_soil_base'] * 0.67, 1)
    }


# ==========================================
# [D] 章節模組：第 4 章 抗滑動穩定性 (Sliding Check)
# ==========================================
def get_ch4_sliding_context(engine, p):
    """
    對應 report_p5_sliding.html 及其動態工況頁面
    將數字轉化為格式化字串與 LaTeX 公式代值
    """
    e = engine
    gamma_s_f = p.get('gamma_soil_front', 1.8)
    gamma_s_b = p['gamma_soil_base']
    v_ext_items = [
        {'name': '地表均佈超載', 'formula': f"{e['q_uniform']:.2f} \\times {e['W_q_width']:.2f}", 'val': e['V_uni']},
        {'name': '地表集中載重 (QP)', 'formula': f"{e['qp_total']:.2f}" if e['V_point'] > 0 else "0.00",
         'val': e['V_point']},
        {'name': '地表帶狀載重 (Strip)',
         'formula': f"{e['qs_total']:.2f} \\times {p['strip_width']:.2f}" if e['V_strip'] > 0 else "0.00",
         'val': e['V_strip']}
    ]

    # 計算各超載總和供顯示
    q_uni_total = get_float(p.get('q_uniform_dead')) + get_float(p.get('q_uniform_live'))
    q_point_total = get_float(p.get('q_point_dead')) + get_float(p.get('q_point_live'))
    q_strip_total = get_float(p.get('q_strip_dead')) + get_float(p.get('q_strip_live'))

    # 1. 整理 active_calc_details 字典 (對應 Page 7-8)
    active_calc_details = {
        'Hs': e['Hs'],
        'Hw': e['h_w_s'],
        'Hdry': e['h_dry'],
        'has_water': e['h_w_s'] > 0,
        # 應力與側壓 (tf/m2)
        'sig_v_top': 0.00,
        'sig_v_water': round(e['sig_v_wat_val'], 2),
        'sig_v_bot': round(e['sig_v_bot_val'], 2),
        'pa_top': round(e['pa_top_val'], 2),
        'pa_water': round(e['pa_wat_val'], 2),
        'pa_bot': round(e['pa_bot_val'], 2),
        # 分層合力 (tf/m)
        'P1': round(e['p1_area'], 2),
        'P2': round(e['p2_area'], 2),
        'Pa_eff': round(e['P_total_area_sum'], 2),
        'angle_soil_deg': round(e['omega_s_deg'], 2),
        'Pa_H': round(e['Pa_H'], 2),
        'Pa_V': round(e['Pa_V'], 2),
        'Pw_total': round(e['Pw_total_ASD'], 2),
        'Pw_H': round(e['PwH_val'], 2),
        # 超載
        # --- 解決超載不顯示的關鍵：從 engine 取得計算值 ---
        'P_qh': round(e['Pqh_ASD'], 2),  # 均佈推力
        'P_ph': round(e['Pph_ASD'], 2),  # 集中推力
        'P_sh': round(e['Psh_ASD'], 2),  # 帶狀推力
        'point_m': round(e['point_m'], 4),  # 解決圖 8 的相對距離 m
        'strip_x_end': round(get_float(p.get('strip_x')) + get_float(p.get('strip_width')), 2),

        'P_stat_H_total': round(e['F_driving_static'], 2),
        'V_ext_total': round(e['V_ext_total_sum'], 2),
        'W_q_width': round(e['W_q_width'], 2),
        'W_q_vertical': round(e['q_uniform'] * e['W_q_width'], 2),
    }

    # 封裝：確保保留 p 裡面的 enable_xxx 原始字串
    input_display = {**p}
    input_display['q_uniform'] = f"{q_uni_total:.2f}"
    input_display['q_point'] = f"{q_point_total:.2f}"
    input_display['q_strip'] = f"{q_strip_total:.2f}"

    # 2. 準備被動抗力細節 (對應 Page 10)
    passive_details = {
        'Pp_total': round(e['Pp_total'], 2),
    }



    return {
        'active_calc_details': active_calc_details,
        'input_data': input_display,  # 更新後包含加總載重的字典
        'passive_details': passive_details,
        'struct_blocks': e['struct_blocks'],
        'soil_layers': e['soil_layers'],
        'v_ext_items': v_ext_items,
        'N_weight_sum': round(e['N_weight_sum'], 2),
        'N_soil_sum': round(e['N_soil_sum'], 2),
        'V_ext_sum': round(e['V_ext_total_sum'], 2),
        'f_friction_val': f"{e['N_prime']:.22f} \\times {p.get('friction_coeff', 0.5)}",
        'h_eff_f': round(e['h_eff_f'], 2),
        'passive_status_text': "忽略覆土深度" if p.get('ignore_h_front') == 'on' else "計入覆土抗力",
        'gamma_s_f': gamma_s_f,
        'gamma_s_b': gamma_s_b,
        'f_pp_f': f"0.5 \\times {gamma_s_f} \\times {e['h_eff_f']:.2f}^2 \\times {e['Kp_f']:.4f}",
        'Pp_f': round(e['Pp_f'], 2),
        'Kp_base': round(e['Kp_base'], 4),
        'sig_p_top': round(e['sig_p_top'], 2),
        'sig_p_bot': round(e['sig_p_bot'], 2),
        'H_sk_m': e['H_sk_m'],
        'Pp_sk': round(e['Pp_sk'], 2),
        'f_pp_sk': f"0.5 \\times ({e['sig_p_top']:.2f} + {e['sig_p_bot']:.2f}) \\times {(p.get('H_sk', 0) / 100.0):.2f}",
        'sliding_details': {
            'B_total': round(e['B_total'], 2),
            'U_uplift': round(e['U_uplift'], 2),
            'F_friction_total': round(e['N_prime'] * p.get('friction_coeff', 0.5), 2),
            'F_resist_total': round(e['F_resist_static'], 2),
            'F_driving': round(e['F_driving_static'], 2),
            'N_prime': round(e['N_prime'], 2),
            'mu': round(e['mu'], 2),
        },
        'sliding_details_dyn': {
            'N_weight_sum': round(e['N_weight_sum'], 2),
            'kv': round(e['kv'], 2),
            'kh': round(e['kh'], 2),
            'Fiw': round(e['Fiw'], 2),
        }
    }


# ==========================================
# 4. 主 View
# ==========================================

def input_view(request):
    context = {'title': '懸臂式擋土牆設計', 'result_available': False}

    if request.method == 'POST':
        try:
            # 1. 統一解析輸入
            raw_post = request.POST.dict()
            p = {k: get_float(v) for k, v in raw_post.items()}
            # 重要：從 raw_post 提取開關狀態 (因為 get_float 會把 'on' 變 0)
            switches = ['enable_uniform', 'enable_point', 'enable_strip', 'ignore_h_front']
            for s in switches:
                p[s] = raw_post.get(s)  # 若存在則為 'on'，否則為 None

            # 2. 核心計算 (只產出 engine 資料字典)
            engine = calculate_retaining_wall_core(p)

            # 3. 模組化組合 Context
            result_context = {'result_available': True}

            # 依章節合併數據
            result_context.update(get_ch1_summary_context(engine))
            result_context.update(get_ch2_properties_context(engine, raw_post))
            result_context.update(get_ch3_coefficients_context(engine))
            result_context.update(get_ch4_sliding_context(engine, p))

            # 4. 儲存與傳回
            request.session['calc_report_context'] = result_context
            context.update(result_context)

        except Exception:
            traceback.print_exc()

    return render(request, 'retaining_wall_cantilever/input.html', context)


def report_view(request):
    context = request.session.get('calc_report_context', {})
    return render(request, 'retaining_wall_cantilever/report_page.html', context)

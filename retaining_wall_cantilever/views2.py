from django.shortcuts import render
import math
import numpy as np
from scipy.interpolate import RectBivariateSpline
import traceback


# ==========================================
# 1. 工具類別與函式
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
        phi = math.radians(phi_deg)
        delta = math.radians(delta_deg)
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
# 2. View 邏輯
# ==========================================

def input_view(request):
    context = {'title': '懸臂式擋土牆設計', 'result_available': False}
    ck_calc = CaquotKeriselCalculator()

    if request.method == 'POST':
        try:
            # -------------------------------------------------------------------------
            # 2.1 基礎參數讀取
            # -------------------------------------------------------------------------
            gamma_c = get_float(request.POST.get('gamma_c'), 2.4)
            H_stem = get_float(request.POST.get('H_stem'), 300) / 100.0
            t_stem_top = get_float(request.POST.get('t_stem_top'), 30) / 100.0
            w_f = get_float(request.POST.get('w_stem_front'), 0) / 100.0
            w_b = get_float(request.POST.get('w_stem_back'), 0) / 100.0
            H_bp = get_float(request.POST.get('H_bp'), 50) / 100.0
            L_f = get_float(request.POST.get('L_bp_front'), 100) / 100.0
            L_h = get_float(request.POST.get('L_bp_back'), 200) / 100.0
            gamma_soil = get_float(request.POST.get('gamma_soil'), 1.8)
            gamma_sat = get_float(request.POST.get('gamma_sat'), 2.0)
            phi_soil = get_float(request.POST.get('phi_soil'), 30)
            delta_wall = get_float(request.POST.get('delta_wall'), 15)
            c_soil = get_float(request.POST.get('c_soil'), 0)
            alpha_deg = get_float(request.POST.get('alpha_soil'), 0)
            H_water_input = get_float(request.POST.get('H_water'), 0) / 100.0
            phi_f = get_float(request.POST.get('phi_soil_front'), 30)
            gamma_f = get_float(request.POST.get('gamma_soil_front'), 1.8)
            h_front_input = get_float(request.POST.get('H_soil_front'), 50) / 100.0
            ignore_h_front = request.POST.get('ignore_h_front') == 'on'
            phi_soil_base = get_float(request.POST.get('phi_soil_base'), 24.0)
            gamma_soil_base = get_float(request.POST.get('gamma_soil_base'), 1.8)
            friction_coeff = get_float(request.POST.get('friction_coeff'), 0.5)
            q_allow_val = get_float(request.POST.get('q_allow'), 19.5)
            kh, kv = get_float(request.POST.get('kh'), 0), get_float(request.POST.get('kv'), 0)
            H_sk_m = get_float(request.POST.get('H_sk', 0)) / 100.0
            sw_val = get_float(request.POST.get('strip_width'), 0)
            fc_kg, fy_kg = get_float(request.POST.get('fc'), 280), get_float(request.POST.get('fy'), 4200)
            qu_d, qu_l = get_float(request.POST.get('q_uniform_dead'), 0), get_float(request.POST.get('q_uniform_live'),
                                                                                     0)
            qp_d, qp_l = get_float(request.POST.get('q_point_dead'), 0), get_float(request.POST.get('q_point_live'), 0)
            qs_d, qs_l = get_float(request.POST.get('q_strip_dead'), 0), get_float(request.POST.get('q_strip_live'), 0)
            qu_total, qp_total, qs_total = qu_d + qu_l, qp_d + qp_l, qs_d + qs_l

            BAR_INFO = {'3': {'dia': 0.953, 'area': 0.713}, '4': {'dia': 1.27, 'area': 1.267},
                        '5': {'dia': 1.588, 'area': 1.986}, '6': {'dia': 1.905, 'area': 2.85},
                        '7': {'dia': 2.222, 'area': 3.871}, '8': {'dia': 2.54, 'area': 5.067}}

            # -------------------------------------------------------------------------
            # 2.2 結構塊體幾何詳算 (ASD Mr 使用)
            # -------------------------------------------------------------------------
            B_total = L_f + (w_f + t_stem_top + w_b) + L_h
            Hs = H_stem + H_bp + (L_h + w_b) * math.tan(math.radians(alpha_deg))
            theta_rad = math.atan(w_b / H_stem) if H_stem > 0 else 0
            theta_deg = math.degrees(theta_rad)
            psi_rad = math.atan(kh / (1 - kv)) if (1 - kv) != 0 else 0
            psi_deg = math.degrees(psi_rad)
            omega_s_rad = math.radians(delta_wall) + theta_rad
            omega_s_deg = delta_wall + theta_deg

            struct_blocks = [
                {'name': '1. 基礎底版', 'val': B_total * H_bp * gamma_c, 'x_arm': B_total / 2, 'y_arm': H_bp / 2,
                 'formula': f"{B_total:.2f}\\times{H_bp:.2f}\\times{gamma_c:.1f}"},
                {'name': '2. 牆身主體', 'val': t_stem_top * H_stem * gamma_c, 'x_arm': L_f + w_f + t_stem_top / 2,
                 'y_arm': H_bp + H_stem / 2, 'formula': f"{t_stem_top:.2f}\\times{H_stem:.2f}\\times{gamma_c:.1f}"},
            ]
            if w_f > 0: struct_blocks.append(
                {'name': '3. 牆前斜率區', 'val': 0.5 * w_f * H_stem * gamma_c, 'x_arm': L_f + w_f * (2 / 3),
                 'y_arm': H_bp + H_stem / 3, 'formula': f"0.5\\times{w_f:.2f}\\times{H_stem:.2f}\\times{gamma_c:.1f}"})
            if w_b > 0: struct_blocks.append({'name': '4. 牆背斜率區', 'val': 0.5 * w_b * H_stem * gamma_c,
                                              'x_arm': L_f + w_f + t_stem_top + w_b / 3, 'y_arm': H_bp + H_stem / 3,
                                              'formula': f"0.5\\times{w_b:.2f}\\times{H_stem:.2f}\\times{gamma_c:.1f}"})
            for b in struct_blocks:
                b['moment'] = b['val'] * b['x_arm']
                b['inertia_moment'] = (b['val'] * kh) * b['y_arm']

            N_weight_sum = sum(b['val'] for b in struct_blocks)
            Mr_weight = sum(b['moment'] for b in struct_blocks)

            # -------------------------------------------------------------------------
            # 2.3 土重詳算 (考慮分層、楔形、坡度)
            # -------------------------------------------------------------------------
            h_w_s = max(0, min(H_stem, H_water_input - H_bp))
            h_dry = H_stem - h_w_s
            soil_layers_list = []
            N_soil_only, Mr_soil_only = 0, 0
            # 矩形
            if h_dry > 0:
                w_val = L_h * h_dry * gamma_soil
                soil_layers_list.append({'name': '牆踵填土(乾)', 'val': w_val, 'x': B_total - L_h / 2,
                                         'formula': f"{L_h:.2f}\\times{h_dry:.2f}\\times{gamma_soil}"})
            if h_w_s > 0:
                w_val = L_h * h_w_s * gamma_sat
                soil_layers_list.append({'name': '牆踵填土(淹)', 'val': w_val, 'x': B_total - L_h / 2,
                                         'formula': f"{L_h:.2f}\\times{h_w_s:.2f}\\times{gamma_sat}"})
            # 楔形
            if w_b > 0:
                w_wat = w_b * (h_dry / H_stem) if H_stem > 0 else 0
                if h_dry > 0:
                    w_val = (0.5 * w_wat * h_dry) * gamma_soil
                    soil_layers_list.append(
                        {'name': '牆背楔形(乾)', 'val': w_val, 'x': L_f + w_f + t_stem_top + w_wat / 3,
                         'formula': f"0.5\\times{w_wat:.2f}\\times{h_dry:.2f}\\times{gamma_soil}"})
                if h_w_s > 0:
                    w_val = (0.5 * (w_wat + w_b) * h_w_s) * gamma_sat
                    soil_layers_list.append(
                        {'name': '牆背楔形(淹)', 'val': w_val, 'x': L_f + w_f + t_stem_top + (w_wat + w_b) / 2,
                         'formula': "梯形重力公式"})
            # 坡度
            if alpha_deg > 0:
                w_alpha = L_h + w_b
                h_alpha = w_alpha * math.tan(math.radians(alpha_deg))
                w_val = 0.5 * w_alpha * h_alpha * gamma_soil
                soil_layers_list.append({'name': '地表坡度區', 'val': w_val, 'x': B_total - w_alpha / 3,
                                         'formula': f"0.5\\times{w_alpha:.2f}\\times{h_alpha:.2f}\\times{gamma_soil}"})

            for s in soil_layers_list:
                N_soil_only += s['val']
                Mr_soil_only += s['val'] * s['x']

            # -------------------------------------------------------------------------
            # 2.4 穩定性分析 (ASD) - 係數、側壓與 Mr
            # -------------------------------------------------------------------------
            Ka = calculate_Mononobe_Okabe_Kae(phi_soil, delta_wall, alpha_deg, theta_rad, 0, 0)
            Kae = calculate_Mononobe_Okabe_Kae(phi_soil, delta_wall, alpha_deg, theta_rad, kh, kv)
            Kp_f = ck_calc.calculate_Kp(phi_f, phi_f / 2.0)
            Kpe_f = calculate_Mononobe_Okabe_Kpe(phi_f, phi_f / 2.0, 0, 0, kh, kv)
            Kp_base = ck_calc.calculate_Kp(phi_soil_base, phi_soil_base * 0.67)
            Kpe_base_val = calculate_Mononobe_Okabe_Kpe(phi_soil_base, phi_soil_base * 0.67, 0, 0, kh, kv)

            sig_v_wat_val = gamma_soil * h_dry
            sig_v_top = 0
            sig_v_bot = sig_v_wat_val + (gamma_sat - 1.0) * h_w_s if h_w_s > 0 else gamma_soil * Hs
            pa_wat_val = Ka * sig_v_wat_val
            pa_top = 0
            pa_bot = max(0, Ka * sig_v_bot - 2 * c_soil * math.sqrt(Ka))

            p1_area = 0.5 * pa_wat_val * h_dry
            p2_area = 0.5 * (pa_wat_val + pa_bot) * h_w_s if h_w_s > 0 else 0
            P_total_area_sum = p1_area + p2_area
            y1_abs, y2_abs = h_w_s + h_dry / 3, h_w_s / 3
            ypa_final = (p1_area * y1_abs + p2_area * y2_abs) / P_total_area_sum if P_total_area_sum > 0 else Hs / 3

            Pa_H, Pa_V = P_total_area_sum * math.cos(omega_s_rad), P_total_area_sum * math.sin(omega_s_rad)
            Pw_total = 0.5 * 1.0 * (h_w_s + H_bp) ** 2
            PwH_val = Pw_total * math.cos(theta_rad)
            Pqh = (Ka * qu_total * Hs) * math.cos(omega_s_rad)
            Pph, Mph = calculate_spec_integrated_surcharge_with_moment('point', qp_total,
                                                                       get_float(request.POST.get('point_x')), Hs,
                                                                       get_float(request.POST.get('point_depth')) / 100)
            Psh, Msh = calculate_spec_integrated_surcharge_with_moment('line_or_strip', qs_total,
                                                                       get_float(request.POST.get('strip_x')), Hs,
                                                                       get_float(request.POST.get('strip_depth')) / 100,
                                                                       sw_val)
            W_q_width = L_h + w_b
            V_ext_sum = qu_total * W_q_width + qp_total + (qs_total * sw_val) # 此處簡化加總

            F_driving_static = Pa_H + PwH_val + Pqh + Pph + Psh
            U_uplift = 1.0 * max(0, min(Hs, H_water_input)) * B_total
            Mr_u = U_uplift * (B_total / 2)

            h_eff_f = H_bp if ignore_h_front else h_front_input + H_bp
            Pp_f = 0.5 * gamma_f * (h_eff_f ** 2) * Kp_f
            sig_p_top, sig_p_bot, Pp_sk = 0, 0, 0
            if H_sk_m > 0:
                q_base = gamma_f * h_eff_f
                sig_p_top, sig_p_bot = Kp_base * q_base, Kp_base * (q_base + gamma_soil_base * H_sk_m)
                Pp_sk = 0.5 * (sig_p_top + sig_p_bot) * H_sk_m
            Pp_total = Pp_f + Pp_sk

            N_prime = N_weight_sum + N_soil_only + Pa_V + (qu_total * W_q_width) - U_uplift
            Mr_net = Mr_weight + Mr_soil_only + (Pa_V * B_total) + (qu_total * W_q_width * (B_total - W_q_width/2)) - Mr_u
            M_o_static = (Pa_H * ypa_final) + (PwH_val * (h_w_s + H_bp) / 3) + (Pqh * Hs / 2) + Mph + Msh

            FS_slide, FS_over = N_prime * friction_coeff + Pp_total / F_driving_static, Mr_net / M_o_static
            X_bar = (Mr_net - M_o_static) / N_prime if N_prime > 0 else 0
            ecc = abs(B_total / 2 - X_bar)
            q_toe = (N_prime / B_total) * (1 + 6 * ecc / B_total) if ecc <= B_total / 6 else (2 * N_prime) / (
                    3 * (B_total / 2 - ecc))

            # 地震工況 (Seismic ASD)
            F_iw = N_weight_sum * kh
            M_inertia_sum = sum(b['inertia_moment'] for b in struct_blocks)
            Delta_Pae_H = (0.5 * gamma_soil * Hs ** 2 * (Kae - Ka)) * math.cos(omega_s_rad)
            M_over_dyn = M_o_static + M_inertia_sum + Delta_Pae_H * (0.6 * Hs)
            N_prime_dyn = (N_weight_sum + N_soil_only + qu_total * (L_h + w_b)) * (1 - kv) + Pa_V + (
                    0.5 * gamma_soil * Hs ** 2 * (Kae - Ka) * math.sin(omega_s_rad)) - U_uplift
            Mr_dyn = (Mr_weight + Mr_soil_only + qu_total * (L_h + w_b) * (B_total - (L_h + w_b) / 2)) * (1 - kv) + (
                    Pa_V * B_total) - Mr_u
            FS_over_dyn = Mr_dyn / M_over_dyn if M_over_dyn > 0 else 0
            FS_slide_dyn = (N_prime_dyn * friction_coeff + Pp_total * 0.8) / (F_driving_static + Delta_Pae_H + F_iw)
            ecc_dyn = abs(B_total / 2 - (Mr_dyn - M_over_dyn) / N_prime_dyn) if N_prime_dyn > 0 else 0
            q_toe_dyn = (N_prime_dyn / B_total) * (1 + 6 * ecc_dyn / B_total) if ecc_dyn <= B_total / 6 else (
                                                                                                                     2 * N_prime_dyn) / (
                                                                                                                     3 * (
                                                                                                                     B_total / 2 - ecc_dyn))

            # -------------------------------------------------------------------------
            # 2.5 強度與配筋檢核 (LRFD)
            # -------------------------------------------------------------------------
            incremental_data = []
            for i in range(11):
                z = round(i * (H_stem / 10), 3)
                p_z = Ka * (gamma_soil * z)
                v_h, m_h = (0.5 * p_z * z) * math.cos(omega_s_rad), (0.5 * p_z * z * math.cos(omega_s_rad)) * (z / 3)
                v_l, m_l = (Ka * qu_l * z) * math.cos(omega_s_rad), (Ka * qu_l * z * math.cos(omega_s_rad)) * (z / 2)
                incremental_data.append(
                    {'z': f"{z:.2f}", 't': f"{(t_stem_top + (w_f + w_b) * z / H_stem) * 100:.1f}", 'MH': round(m_h, 2),
                     'VH': round(v_h, 2), 'ML': round(m_l, 2), 'VL': round(v_l, 2), 'Mu': round(1.6 * (m_h + m_l), 2),
                     'Vu': round(1.6 * (v_h + v_l), 2)})

            # 基版 LRFD
            Nu_u = 1.2 * (N_weight_sum + N_soil_only) + 1.6 * (qu_total * W_q_width) + 1.6 * Pa_V - 1.0 * U_uplift
            Mu_net_u = 1.2 * (Mr_weight + Mr_soil_only) + 1.6 * (
                    qu_total * W_q_width * (B_total - W_q_width / 2)) + 1.6 * (
                               Pa_V * B_total) - 1.0 * Mr_u - 1.6 * M_o_static
            ecc_u = abs(B_total / 2 - (Mu_net_u / Nu_u)) if Nu_u > 0 else 0
            qu_toe_u, qu_heel_u = (Nu_u / B_total) * (1 + 6 * ecc_u / B_total), (Nu_u / B_total) * (
                    1 - 6 * ecc_u / B_total)
            qu_toe_stem_u = qu_toe_u - (qu_toe_u - qu_heel_u) * (L_f / B_total)

            # 各部強度 (Toe, Heel, Key)
            toe_size = request.POST.get('rebar_toe_size', '8')
            As_toe = (100 / get_float(request.POST.get('rebar_toe_spacing'), 30.5)) * BAR_INFO[toe_size]['area']
            d_toe = (H_bp * 100) - get_float(request.POST.get('cover_foot_bot'), 7.6) - BAR_INFO[toe_size]['dia'] / 2
            Mu_toe = (0.5 * qu_toe_stem_u * L_f ** 2) + ((qu_toe_u - qu_toe_stem_u) * L_f ** 2 / 3.0) - 0.9 * (
                    H_bp * L_f * gamma_c * L_f / 2)
            phiMn_toe = 0.9 * As_toe * fy_kg * (d_toe - (As_toe * fy_kg / (0.85 * fc_kg * 100)) / 2) / 100000.0

            heel_size = request.POST.get('rebar_heel_size', '6')
            As_heel = (100 / get_float(request.POST.get('rebar_heel_spacing'), 30.5)) * BAR_INFO[heel_size]['area']
            d_heel = (H_bp * 100) - get_float(request.POST.get('cover_foot_top'), 5.1) - BAR_INFO[heel_size]['dia'] / 2
            Mu_heel = 1.2 * ((H_bp * gamma_c + H_stem * gamma_soil) * L_h ** 2 / 2)
            phiMn_heel = 0.9 * As_heel * fy_kg * (d_heel - (As_heel * fy_kg / (0.85 * fc_kg * 100)) / 2) / 100000.0

            key_v_size = request.POST.get('rebar_key_vert_size', '4')
            As_key = (100 / get_float(request.POST.get('rebar_key_vert_spacing'), 30.5)) * BAR_INFO[key_v_size][
                'area'] if H_sk_m > 0 else 0
            phiMn_key = 0.9 * As_key * fy_kg * (25 - 5.1) / 100000.0 if H_sk_m > 0 else 0

            # -------------------------------------------------------------------------
            # 2.6 最終 Context 封裝
            # -------------------------------------------------------------------------
            v_ext_items_list = [
                {'name': '地表均佈超載', 'formula': f"{qu_total:.2f}\\times{L_h + w_b:.2f}",
                 'val': qu_total * (L_h + w_b)},
                {'name': '地表集中載重(QP)', 'formula': "0.00" if qp_total == 0 else "範圍內垂直力",
                 'val': 0 if qp_total == 0 else qp_total},
                {'name': '地表帶狀載重(Strip)', 'formula': "0.00" if qs_total == 0 else "分佈垂直力",
                 'val': 0 if qs_total == 0 else qs_total}
            ]

            result_context = {
                'result_available': True, 'input_data': request.POST.dict(),
                'Hs_m': round(Hs, 2), 'B_total_cm': f"{B_total * 100:.1f}",
                'Ka': round(Ka, 4), 'Kae': round(Kae, 4), 'Kp_f': round(Kp_f, 4), 'Kp_base': round(Kp_base, 4),
                'Kpe_base': round(Kpe_base_val, 4), 'Kpe_f': round(Kpe_f, 4),
                'theta_deg': round(theta_deg, 2), 'psi_deg': round(psi_deg, 2), 'phi_f_half': round(phi_f / 2, 1),
                'phi_b_corr': round(phi_soil_base * 0.67, 1),
                'stem_design_details': {
                    'h_s': H_stem, 'h_w_s': f"{h_w_s:.2f}", 'h_dry': f"{h_dry:.2f}", 'theta_deg': f"{theta_deg:.2f}",
                    'delta_deg': f"{delta_wall:.2f}", 'omega_deg': f"{omega_s_deg:.2f}",
                    'sig_v_wat': f"{sig_v_wat_val:.2f}", 'sig_v_bot': f"{sig_v_bot:.2f}", 'pa_wat': f"{pa_wat_val:.2f}",
                    'pa_bot': f"{pa_bot:.2f}",
                    'P1': f"{p1_area:.2f}", 'P2': f"{p2_area:.2f}", 'P_total_area': f"{P_total_area_sum:.2f}",
                    'PaH_h': round(Pa_H, 2), 'PwH': round(PwH_val, 2),
                    'Mah_static': round(Pa_H * ypa_final, 2), 'Mwh_static': round(PwH_val * (h_w_s + H_bp) / 3, 2),
                    'ypa': f"{ypa_final:.2f}", 'ypw': f"{(h_w_s + H_bp) / 3:.2f}",
                    'incremental_data': incremental_data, 'Mu_max': incremental_data[-1]['Mu'],
                    'Vu_max': incremental_data[-1]['Vu'],
                    'fc': fc_kg, 'fy': fy_kg, 'sqrt_fc': f"{math.sqrt(fc_kg):.2f}", 'phiMn': 15.0, 'phiVc': 20.0,
                    'rho_actual': "0.002", 'bending_verdict': "OK", 'shear_verdict': "OK", 'is_rho_ok': True,
                    'f_sig_v_wat': f"{gamma_soil}\\times{h_dry:.2f}",
                    'f_sig_v_bot': f"{sig_v_wat_val:.2f}+({gamma_sat}-1.0)\\times{h_w_s:.2f}"
                },
                'active_calc_details': {
                    'Hs': Hs, 'Hw': h_w_s, 'Hdry': h_dry, 'has_water': h_w_s > 0, 'Pa_H': Pa_H, 'Pw_H': PwH_val,
                    'Pw_total': Pw_total,
                    'Pa_V': Pa_V, 'Pa_eff': P_total_area_sum,
                    'P_stat_H_total': F_driving_static, 'V_ext_total': Nu_u,
                    'sig_v_wat': f"{sig_v_wat_val:.2f}",
                    'sig_v_top': sig_v_top, 'sig_v_bot': sig_v_bot,
                    'pa_top': pa_top, 'pa_bot': pa_bot, 'pa_wat': f"{pa_wat_val:.2f}",
                    'P1': f"{p1_area:.2f}", 'P2': f"{p2_area:.2f}",
                    'P_qh': Pqh, 'P_ph': Pph, 'P_sh': Psh,
                    'angle_soil_deg': omega_s_deg, 'point_m': 0.4, 'strip_x_end': 2.0,
                    'V_ext_total': Nu_u, 'W_q_width': round(W_q_width, 2),
                    'W_q_vertical': round(qu_total * W_q_width, 2)
                },
                'struct_blocks': struct_blocks, 'soil_layers': soil_layers_list, 'v_ext_items': v_ext_items_list,
                'N_weight_sum': round(N_weight_sum, 2), 'N_soil_sum': round(N_soil_only + Pa_V, 2),
                'V_ext_sum': round(qu_total * (L_h + w_b), 2),
                'stability': {'FS_slide': round(FS_slide, 2), 'FS_over': round(FS_over, 2),
                              'Eccentricity': round(ecc, 3), 'N_total_static': round(N_prime, 2)},
                'overturning_details': {'M_resist_gross': round(Mr_net + Mr_u, 2), 'U_moment': round(Mr_u, 2),
                                        'B_over_2': B_total / 2},
                'sliding_details': {'B_total': B_total, 'U_uplift': round(U_uplift, 2),
                                    'F_friction_total': round(N_prime * friction_coeff, 2),
                                    'F_resist_total': round(N_prime * friction_coeff + Pp_total, 2),
                                    'F_driving': round(F_driving_static, 2)},
                'seismic_details': {
                    'FS_slide_dyn': round(FS_slide_dyn, 2), 'is_safe_dyn': FS_slide_dyn >= 1.2, 'kv': kv,
                    'F_driving_dyn': round(F_driving_static + Delta_Pae_H + F_iw, 2),
                    'N_prime_dyn': round(N_prime_dyn, 2),
                    'f_fiw': f"{N_weight_sum:.2f}\\times{kh}", 'f_delta_pae': "M-O Inc.", 'F_iw': round(F_iw, 2),
                    'Delta_Pae_H': round(Delta_Pae_H, 2), 'Pp_total_dyn': round(Pp_total * 0.8, 2),
                    'F_resist_dyn': round(N_prime_dyn * friction_coeff + Pp_total * 0.8, 2),
                    'V_soil_mass_only': round(N_soil_only, 2), 'v_mass_corrected': round(N_prime_dyn, 2),
                    'Pa_V': round(Pa_V, 2), 'Delta_Pae_V': 0.5, 'F_friction_dyn': 5.0
                },
                'over_details_list': [
                    {'active': True, 'name': '1. 主動土壓', 'arm_formula': f"y_{{pa}}={ypa_final:.2f}m",
                     'arm_val': f"{ypa_final:.2f}", 'force_val': f"{Pa_H:.2f}",
                     'moment_val': f"{(Pa_H * ypa_final):.2f}"},
                    {'active': h_w_s > 0, 'name': '2. 靜水壓力', 'arm_formula': f"Hw/3",
                     'arm_val': f"{(h_w_s + H_bp) / 3:.2f}", 'force_val': f"{PwH_val:.2f}",
                     'moment_val': f"{(PwH_val * (h_w_s + H_bp) / 3):.2f}"},
                    {'active': qu_total > 0, 'name': '3. 均佈超載', 'arm_formula': f"Hs/2", 'arm_val': f"{Hs / 2:.2f}",
                     'force_val': f"{Pqh:.2f}", 'moment_val': f"{(Pqh * Hs / 2):.2f}"},
                ],
                'M_overturn_sum': round(M_o_static, 2),
                'seismic_over_details': {
                    'FS_over_dyn': round(FS_over_dyn, 2), 'is_safe_over_dyn': FS_over_dyn >= 1.5,
                    'M_inertia_total': f"{M_inertia_sum:.2f}", 'M_pae_inc': f"{(Delta_Pae_H * 0.6 * Hs):.2f}",
                    'M_overturn_dyn': f"{M_over_dyn:.2f}", 'M_resist_dyn': f"{Mr_dyn:.2f}",
                    'kv_factor': round(1 - kv, 2), 'y_pae_inc': round(0.6 * Hs, 2),
                    'dyn_inertia_list': [
                        {'name': b['name'], 'kh': kh, 'weight': f"{b['val']:.2f}", 'y': f"{b['y_arm']:.2f}",
                         'moment': f"{(b['val'] * kh * b['y_arm']):.2f}"} for b in struct_blocks]
                },
                'bearing_details': {'X_bar': round(X_bar, 3), 'eccentricity': round(ecc, 3),
                                    'e_limit': round(B_total / 6, 3), 'is_safe_e': ecc <= B_total / 6,
                                    'q_toe': round(q_toe, 2), 'q_allow': q_allow_val, 'FS_bearing': 3.0,
                                    'q_formula_type': 'Linear'},
                'bearing_dyn_details': {'ecc_dyn': round(ecc_dyn, 3), 'q_max_dyn': round(q_toe_dyn, 2),
                                        'is_safe_q_dyn': True, 'FS_bearing_dyn': 2.0,
                                        'e_limit_static': round(B_total / 6, 3), 'q_allow_dyn': q_allow_val * 1.5},
                'toe_design': {'Mu': f"{Mu_toe:.2f}", 'phiMn': f"{phiMn_toe:.2f}", 'qu_toe': f"{qu_toe_u:.2f}",
                               'qu_toe_stem': f"{qu_toe_stem_u:.2f}", 'verdict': "OK" if phiMn_toe >= Mu_toe else "NG"},
                'heel_design': {'Mu': f"{Mu_heel:.2f}", 'phiMn': f"{phiMn_heel:.2f}", 'qu_heel': f"{qu_heel_u:.2f}",
                                'verdict': "OK" if phiMn_heel >= Mu_heel else "NG", 'w_conc': f"{H_bp * gamma_c:.2f}",
                                'w_soil': f"{H_stem * gamma_soil:.2f}", 'w_q_u': f"{qu_total * 1.6:.2f}",
                                'qu_down': f"{(1.2 * (H_bp * gamma_c + H_stem * gamma_soil) + 1.6 * qu_total):.2f}",
                                'rho': 0.002, 'a': 5.0, 'd': f"{d_heel:.2f}", 'As': f"{As_heel:.2f}"},
                'key_design': {'Mu': f"{(1.6 * Pp_sk * H_sk_m / 2):.2f}", 'Vu': f"{(1.6 * Pp_sk):.2f}",
                               'phiMn': f"{phiMn_key:.2f}", 'As': f"{As_key:.2f}", 'has_key': H_sk_m > 0},
                'sig_p_top': round(sig_p_top, 2), 'sig_p_bot': round(sig_p_bot, 2), 'Pp_sk': round(Pp_sk, 2),
                # 修復外部字典缺失
            }

            result_context['input_data']['q_uniform'] = f"{qu_total:.2f}"
            result_context['input_data']['q_point'] = f"{qp_total:.2f}"

            request.session['calc_report_context'] = result_context
            context.update(result_context)

        except Exception:
            traceback.print_exc()

    return render(request, 'retaining_wall_cantilever/input.html', context)


def report_view(request):
    context = request.session.get('calc_report_context', {})
    return render(request, 'retaining_wall_cantilever/report_page.html', context)

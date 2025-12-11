from django.shortcuts import render
import math
import numpy as np
from scipy.interpolate import RectBivariateSpline


# ==========================================
# 1. 工具類別與函式 (Utils)
# ==========================================

class CaquotKeriselCalculator:
    """ Caquot-Kerisel 被動土壓力係數計算器 (靜態) """

    def __init__(self):
        self.phis = np.array([10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60])
        self.ratios = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        # 原始表格 (Row: Phi 10->60, Col: Ratio 1.0->0.0)
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

    def calculate_Kp(self, phi_deg, delta_deg, theta_deg, alpha_deg):
        # 邊界保護
        if phi_deg < 10: phi_deg = 10
        if phi_deg > 60: phi_deg = 60

        ratio = delta_deg / phi_deg if phi_deg != 0 else 0
        if ratio > 1.0: ratio = 1.0
        if ratio < 0.0: ratio = 0.0

        Rp = float(self.spline(phi_deg, ratio, grid=False))

        phi = math.radians(phi_deg);
        theta = math.radians(theta_deg);
        alpha = math.radians(alpha_deg)
        tan_phi = math.tan(phi);
        sin_phi = math.sin(phi);
        cos_phi = math.cos(phi)
        cos_theta = math.cos(theta);
        sin_theta = math.sin(theta)

        Phi_0 = 1.10 * tan_phi + 0.275 * math.pow(tan_phi, 5 / 3)
        Phi_1 = math.pow(cos_phi, 6)
        Phi_2 = 1.135 * math.pow(tan_phi, 9 / 8)
        Phi_3 = sin_phi / 2.0
        Phi_4 = 0.463 * sin_phi + 0.425 * math.pow(sin_phi, 6)
        Phi_5 = Phi_0 - Phi_4 - math.log10(max(math.pow(cos_phi, 2), 1e-9))
        term_phi6 = max(0, 1 - 0.7 * tan_phi)
        Phi_6 = 0.07 * tan_phi * term_phi6
        Phi_7 = (0.34 * sin_phi) / (0.10 + sin_phi + math.pow(sin_phi, 2))

        Theta_1 = -math.log10(max(abs(cos_theta), 1e-9))
        Theta_2 = sin_theta
        Theta_3 = math.pow(sin_theta, 3)
        Theta_7 = 1 - cos_theta + 0.62 * sin_theta

        ratio_ap = alpha / phi if phi != 0 else 0
        term_A4 = (19 * math.pi * ratio_ap) / 60.0
        A_4 = math.pow(math.tan(term_A4), 2)
        A_5 = 1.124 * math.sin(math.pi * ratio_ap / 4.0) + 1.16 * math.pow(math.sin(math.pi * ratio_ap / 4.0), 5)
        A_6 = math.sin(math.pi * ratio_ap)
        val_A7_inner = max(0, 1 - ratio_ap)
        A_7 = 1 - math.pow(val_A7_inner, 2.5)

        F_1 = Phi_1 * Theta_1 + Phi_2 * Theta_2 + Phi_3 * Theta_3
        term_F2_exp = 1 + ratio_ap
        F_2 = -0.422 * Phi_4 * A_4 + Phi_5 * A_5 - Phi_6 * A_6 + \
              2.5 * (1 + ratio_ap) * math.pow(10, -6 * term_F2_exp) * math.sin(2 * phi)
        term_F7_bracket = 80 + 17 * math.pow(ratio_ap, 3) - 25 * math.pow(ratio_ap, 4) - phi_deg
        F_7 = math.sin(0.5 * term_F7_bracket * (math.pi / 180.0))

        log_n = Phi_0 - F_1 + F_2 + F_7 * Phi_7 * Theta_7 * A_7
        term_log_cos_phi = math.log10(max(cos_phi, 1e-9))
        Kp_base = math.pow(10, log_n - term_log_cos_phi)

        return Rp * Kp_base


def calc_strip_load_force_moment(q, x_dist, B_width, H_wall):
    num_slices = 100
    dy = H_wall / num_slices
    P_strip = 0;
    M_strip = 0
    for i in range(num_slices):
        z = (i + 0.5) * dy
        if z < 0.001: z = 0.001
        theta1 = math.atan(x_dist / z)
        theta2 = math.atan((x_dist + B_width) / z)
        beta = theta2 - theta1
        sigma_h = (q / math.pi) * (beta - math.sin(beta) * math.cos(theta1 + theta2))
        force_slice = sigma_h * dy
        arm_slice = H_wall - z
        P_strip += force_slice
        M_strip += force_slice * arm_slice
    return P_strip, M_strip


def calculate_Mononobe_Okabe_Kae(phi_deg, delta_deg, alpha_deg, theta_deg, kh, kv):
    phi = math.radians(phi_deg);
    delta = math.radians(delta_deg)
    alpha = math.radians(alpha_deg);
    theta = math.radians(theta_deg)
    denom_k = 1 - kv
    if abs(denom_k) < 1e-6: denom_k = 1e-6
    psi = math.atan(kh / denom_k)

    term_sin = math.sin(phi + delta) * math.sin(phi - psi - alpha)
    if term_sin < 0: term_sin = 0
    sqrt_term = math.sqrt(term_sin) / math.sqrt(max(1e-6, math.cos(delta + psi + theta) * math.cos(theta - alpha)))

    numerator = math.pow(math.cos(phi - theta - psi), 2)
    denominator = math.cos(psi) * math.pow(math.cos(theta), 2) * math.cos(delta + psi + theta) * math.pow(1 + sqrt_term,
                                                                                                          2)
    return numerator / denominator if denominator != 0 else 999.0


def calculate_Mononobe_Okabe_Kpe(phi_deg, delta_deg, alpha_deg, theta_deg, kh, kv):
    phi = math.radians(phi_deg);
    delta = math.radians(delta_deg)
    alpha = math.radians(alpha_deg);
    theta = math.radians(theta_deg)
    denom_k = 1 - kv
    if abs(denom_k) < 1e-6: denom_k = 1e-6
    psi = math.atan(kh / denom_k)

    term_sin = math.sin(phi + delta) * math.sin(phi - psi + alpha)
    if term_sin < 0: term_sin = 0
    sqrt_term = math.sqrt(term_sin) / math.sqrt(max(1e-6, math.cos(delta - theta + psi) * math.cos(alpha - theta)))

    numerator = math.pow(math.cos(phi + theta - psi), 2)
    denominator = math.cos(psi) * math.pow(math.cos(theta), 2) * math.cos(delta - theta + psi) * math.pow(1 - sqrt_term,
                                                                                                          2)
    return numerator / denominator if denominator != 0 else 999.0


def calculate_Coulomb_Kp(phi_deg, delta_deg, alpha_deg, theta_deg):
    phi = math.radians(phi_deg);
    delta = math.radians(delta_deg)
    alpha = math.radians(alpha_deg);
    theta = math.radians(theta_deg)
    numerator = math.pow(math.cos(phi + theta), 2)
    denom_part = math.pow(math.cos(theta), 2) * math.cos(delta - theta)
    term_sin = math.sin(phi + delta) * math.sin(phi + alpha)
    term_cos = math.cos(delta - theta) * math.cos(alpha - theta)
    if term_cos == 0: term_cos = 1e-6
    if term_sin < 0: term_sin = 0
    sqrt_val = math.sqrt(term_sin / term_cos)
    denominator = denom_part * math.pow(1 - sqrt_val, 2)
    return numerator / denominator if denominator != 0 else 999.0


# ==========================================
# 2. View 邏輯
# ==========================================

def input_view(request):
    context = {
        'title': '懸臂式擋土牆設計 (Cantilever Retaining Wall Design)',
        'result_available': False
    }

    ck_calculator = CaquotKeriselCalculator()

    if request.method == 'POST':
        try:
            # 1. 讀取輸入 (cm -> m)
            gamma_c = float(request.POST.get('gamma_c', 2.4))

            H_stem_cm = float(request.POST.get('H_stem', 300))
            t_stem_top_cm = float(request.POST.get('t_stem_top', 30))
            w_stem_front_cm = float(request.POST.get('w_stem_front', 0))
            w_stem_back_cm = float(request.POST.get('w_stem_back', 0))
            H_bp_cm = float(request.POST.get('H_bp', 50))
            L_bp_front_cm = float(request.POST.get('L_bp_front', 100))
            L_bp_back_cm = float(request.POST.get('L_bp_back', 200))
            H_sk_cm = float(request.POST.get('H_sk', 0))
            L_sk_cm = float(request.POST.get('L_sk', 0))
            x_1_cm = float(request.POST.get('x_1', 0))

            H_stem = H_stem_cm / 100.0
            t_stem_top = t_stem_top_cm / 100.0
            w_stem_front = w_stem_front_cm / 100.0
            w_stem_back = w_stem_back_cm / 100.0
            t_stem_bot = w_stem_front + t_stem_top + w_stem_back
            H_bp = H_bp_cm / 100.0
            L_bp_front = L_bp_front_cm / 100.0
            L_bp_back = L_bp_back_cm / 100.0
            H_sk = H_sk_cm / 100.0
            L_sk = L_sk_cm / 100.0
            x_1 = x_1_cm / 100.0

            # 牆後土
            gamma_soil = float(request.POST.get('gamma_soil', 1.8))
            gamma_sat = float(request.POST.get('gamma_sat', gamma_soil))
            phi_deg = float(request.POST.get('phi_soil', 30))
            delta_deg = float(request.POST.get('delta_wall', 15))
            c_soil = float(request.POST.get('c_soil', 0))
            alpha_deg = float(request.POST.get('alpha_soil', 0))

            H_water_cm = float(request.POST.get('H_water', 0))
            H_water = H_water_cm / 100.0
            H_fill_input = request.POST.get('H_fill', '')
            if H_fill_input and float(H_fill_input) >= 0:
                H_fill_above_base = float(H_fill_input) / 100.0
            else:
                H_fill_above_base = H_stem

                # 斜坡高度修正
            H_slope_rise = 0
            if alpha_deg > 0 and alpha_deg < phi_deg:
                H_slope_rise = L_bp_back * math.tan(math.radians(alpha_deg))

            H_calc_total = H_fill_above_base + H_bp + H_slope_rise

            # 牆前土
            H_soil_front_cm = float(request.POST.get('H_soil_front', 50))
            H_soil_front = H_soil_front_cm / 100.0
            gamma_front = float(request.POST.get('gamma_soil_front', 1.8))
            gamma_sat_front = float(request.POST.get('gamma_sat_front', 2.0))
            phi_front = float(request.POST.get('phi_soil_front', 30))
            c_front = float(request.POST.get('c_soil_front', 0))
            delta_front = phi_front / 2.0
            H_pass_front = H_soil_front + H_bp

            # 版底土
            gamma_base = float(request.POST.get('gamma_soil_base', 1.9))
            gamma_sat_base = float(request.POST.get('gamma_sat_base', 2.1))
            phi_base = float(request.POST.get('phi_soil_base', 32))
            c_base = float(request.POST.get('c_soil_base', 0))
            delta_base = (2.0 / 3.0) * phi_base

            # 地震與超載
            kh = float(request.POST.get('kh', 0))
            kv = float(request.POST.get('kv', 0))
            surcharge_type = request.POST.get('surcharge_type', 'none')
            q_surcharge = 0.0;
            strip_x = 0.0;
            strip_B = 0.0
            if surcharge_type == 'uniform':
                q_surcharge = float(request.POST.get('q_uniform', 0))
            elif surcharge_type == 'strip':
                q_surcharge = float(request.POST.get('q_strip', 0))
                strip_x = float(request.POST.get('strip_x', 0))
                strip_B = float(request.POST.get('strip_B', 0))

            # --- 2. 幾何自重 ---
            blocks = []
            B_total = L_bp_front + t_stem_bot + L_bp_back

            w1 = (B_total * H_bp) * gamma_c
            blocks.append({'name': '基版 (Base)', 'weight': w1, 'moment': w1 * (B_total / 2.0)})

            stem_start_x = L_bp_front
            if w_stem_front > 0:
                w2a = 0.5 * w_stem_front * H_stem * gamma_c
                blocks.append(
                    {'name': '牆身前三角', 'weight': w2a, 'moment': w2a * (stem_start_x + 2 / 3 * w_stem_front)})
            if t_stem_top > 0:
                w2b = t_stem_top * H_stem * gamma_c
                blocks.append({'name': '牆身核心', 'weight': w2b,
                               'moment': w2b * (stem_start_x + w_stem_front + t_stem_top / 2.0)})
            if w_stem_back > 0:
                w2c = 0.5 * w_stem_back * H_stem * gamma_c
                blocks.append({'name': '牆身後三角', 'weight': w2c,
                               'moment': w2c * (stem_start_x + w_stem_front + t_stem_top + 1 / 3 * w_stem_back)})

            if H_sk > 0 and L_sk > 0:
                w3 = L_sk * H_sk * gamma_c
                blocks.append({'name': '止滑榫', 'weight': w3, 'moment': w3 * (B_total - x_1 - L_sk / 2.0)})

            total_weight = sum(b['weight'] for b in blocks)

            # --- 3. 主動土壓力 ---
            theta_rad = math.atan(w_stem_back / H_stem) if H_stem > 0 else 0
            theta_deg = math.degrees(theta_rad)
            phi = math.radians(phi_deg);
            delta = math.radians(delta_deg);
            alpha = math.radians(alpha_deg)

            # Ka
            num = math.pow(math.cos(phi - theta_rad), 2)
            den1 = math.pow(math.cos(theta_rad), 2) * math.cos(theta_rad + delta)
            sin_term = math.sin(phi - alpha) if phi_deg >= alpha_deg else 0
            sqrt_val = (math.sin(phi + delta) * sin_term) / (math.cos(delta + theta_rad) * math.cos(theta_rad - alpha))
            if sqrt_val < 0: sqrt_val = 0
            Ka = num / (den1 * math.pow(1 + math.sqrt(sqrt_val), 2))

            # Kae
            Kae = calculate_Mononobe_Okabe_Kae(phi_deg, delta_deg, alpha_deg, theta_deg, kh, kv)

            # 壓力分佈
            Y_water = H_water
            if Y_water > H_calc_total: Y_water = H_calc_total
            if Y_water < 0: Y_water = 0
            h_dry = H_calc_total - Y_water
            h_sub = Y_water
            gamma_w = 1.0

            sig_v_top = 0
            sig_v_water = sig_v_top + gamma_soil * h_dry
            gamma_eff_sub = gamma_sat - gamma_w
            sig_v_bot = sig_v_water + gamma_eff_sub * h_sub

            c_deduct_static = 2 * c_soil * math.tan(math.radians(45 + phi_deg / 2)) * Ka
            pa_top = max(0, Ka * sig_v_top - c_deduct_static)
            pa_water = max(0, Ka * sig_v_water - c_deduct_static)
            pa_bot = max(0, Ka * sig_v_bot - c_deduct_static)

            P_soil_1_slant = 0.5 * (pa_top + pa_water) * h_dry
            arm_soil_1 = Y_water + (h_dry / 3.0) * (2 * pa_top + pa_water) / (pa_top + pa_water) if (
                                                                                                                pa_top + pa_water) > 0 else 0
            P_soil_2_slant = 0.5 * (pa_water + pa_bot) * h_sub
            arm_soil_2 = (h_sub / 3.0) * (2 * pa_water + pa_bot) / (pa_water + pa_bot) if (pa_water + pa_bot) > 0 else 0

            # 地震增量
            P_AE_friction = 0.5 * gamma_soil * (H_calc_total ** 2) * (1 - kv) * Kae
            c_force_dynamic = 2 * c_soil * math.sqrt(Kae) * H_calc_total
            P_AE_total = max(0, P_AE_friction - c_force_dynamic)

            P_A_friction_ref = 0.5 * gamma_soil * (H_calc_total ** 2) * Ka
            c_force_static_ref = 2 * c_soil * math.sqrt(Ka) * H_calc_total
            P_A_ref = max(0, P_A_friction_ref - c_force_static_ref)

            Delta_P_AE_slant = max(0, P_AE_total - P_A_ref)
            arm_seismic = (2.0 / 3.0) * H_calc_total

            # 超載
            P_surcharge_slant = 0;
            M_surcharge = 0;
            surcharge_desc = "None"
            if surcharge_type == 'uniform':
                surcharge_desc = "Uniform"
                P_surcharge_slant = Ka * q_surcharge * H_calc_total
            elif surcharge_type == 'strip':
                surcharge_desc = "Strip"
                pass

                # 分解為水平與垂直分量
            angle_act = delta + theta_rad

            P_soil_1_H = P_soil_1_slant * math.cos(angle_act);
            P_soil_1_V = P_soil_1_slant * math.sin(angle_act)
            P_soil_2_H = P_soil_2_slant * math.cos(angle_act);
            P_soil_2_V = P_soil_2_slant * math.sin(angle_act)
            P_seismic_H = Delta_P_AE_slant * math.cos(angle_act);
            P_seismic_V = Delta_P_AE_slant * math.sin(angle_act)

            if surcharge_type == 'uniform':
                P_sur_H = P_surcharge_slant * math.cos(angle_act);
                P_sur_V = P_surcharge_slant * math.sin(angle_act)
                M_sur_H = P_sur_H * (H_calc_total / 2.0)
            else:
                P_sur_H, M_sur_H = calc_strip_load_force_moment(q_surcharge, strip_x, strip_B, H_calc_total)
                P_sur_V = 0

            # 水壓力
            u_bot = gamma_w * h_sub
            force_water_H = 0.5 * u_bot * h_sub
            force_water_V = force_water_H * math.tan(theta_rad)
            arm_water = h_sub / 3.0

            Delta_P_WE_H = 0;
            M_dynamic_water = 0;
            arm_dyn_water = 0
            if H_water > 0 and kh > 0:
                westergaard_factor = (7.0 / 12.0)
                Delta_P_WE_H = 0.7 * westergaard_factor * kh * gamma_w * (H_water ** 2)
                arm_dyn_water = 0.4 * H_water
                M_dynamic_water = Delta_P_WE_H * arm_dyn_water

            # 總結
            P_total_driving_H = P_soil_1_H + P_soil_2_H + force_water_H + P_sur_H + P_seismic_H + Delta_P_WE_H
            M_total_driving = (P_soil_1_H * arm_soil_1) + (P_soil_2_H * arm_soil_2) + (
                        force_water_H * arm_water) + M_sur_H + (P_seismic_H * arm_seismic) + M_dynamic_water
            y_resultant = M_total_driving / P_total_driving_H if P_total_driving_H > 0 else 0
            P_total_stabilizing_V = P_soil_1_V + P_soil_2_V + P_sur_V + P_seismic_V + force_water_V

            # --- [4] 被動土壓力 ---
            # Part A Front
            Kp_front = ck_calculator.calculate_Kp(phi_front, delta_front, 0, 0)
            Kpe_front = calculate_Mononobe_Okabe_Kpe(phi_front, delta_front, 0, 0, kh, kv)

            q_front_top = gamma_front * H_soil_front
            pp1_top = Kp_front * q_front_top + 2 * c_front * math.sqrt(Kp_front)
            pp1_bot = Kp_front * (q_front_top + gamma_front * H_bp) + 2 * c_front * math.sqrt(Kp_front)
            Pp1_static = 0.5 * (pp1_top + pp1_bot) * H_bp
            arm_Pp1 = (H_bp / 3.0) * (2 * pp1_top + pp1_bot) / (pp1_top + pp1_bot) if Pp1_static > 0 else 0

            ppe1_top = Kpe_front * q_front_top * (1 - kv) + 2 * c_front * math.sqrt(Kpe_front)
            ppe1_bot = Kpe_front * (q_front_top + gamma_front * H_bp) * (1 - kv) + 2 * c_front * math.sqrt(Kpe_front)
            Ppe1_dynamic = 0.5 * (ppe1_top + ppe1_bot) * H_bp

            # Part B Base Key
            Kp_base = 0;
            Kpe_base = 0;
            Pp2_static = 0;
            Ppe2_dynamic = 0;
            arm_Pp2 = 0
            q_base_eff = 0;
            pp2_top = 0;
            pp2_bot = 0;
            ppe2_top = 0;
            ppe2_bot = 0

            if H_sk > 0:
                Kp_base = ck_calculator.calculate_Kp(phi_base, delta_base, 0, 0)
                Kpe_MO = calculate_Mononobe_Okabe_Kpe(phi_base, delta_base, 0, 0, kh, kv)
                Kp_Coulomb = calculate_Coulomb_Kp(phi_base, delta_base, 0, 0)
                ratio = (Kpe_MO / Kp_Coulomb) if Kp_Coulomb > 0 else 1.0
                Kpe_base = min(Kp_base, Kp_base * ratio)
                if Kpe_base > Kp_base: Kpe_base = Kp_base

                # 有效超載 q'
                sigma_soil_front = 0
                if H_soil_front > 0:
                    water_level_in_soil = max(0, H_water - H_bp)
                    if water_level_in_soil >= H_soil_front:
                        sigma_soil_front = (gamma_sat_front - 1.0) * H_soil_front
                    elif water_level_in_soil > 0:
                        h_sub_front = water_level_in_soil
                        h_dry_front = H_soil_front - h_sub_front
                        sigma_soil_front = (gamma_front * h_dry_front) + ((gamma_sat_front - 1.0) * h_sub_front)
                    else:
                        sigma_soil_front = gamma_front * H_soil_front

                sigma_concrete = 0
                if H_water >= H_bp:
                    sigma_concrete = (gamma_c - 1.0) * H_bp
                elif H_water > 0:
                    h_sub_conc = H_water
                    h_dry_conc = H_bp - H_water
                    sigma_concrete = (gamma_c * h_dry_conc) + ((gamma_c - 1.0) * h_sub_conc)
                else:
                    sigma_concrete = gamma_c * H_bp

                q_base_eff = sigma_soil_front + sigma_concrete

                # [Fix] 修正止滑榫底部有效重
                gamma_base_eff = gamma_base
                if H_water > 0: gamma_base_eff = gamma_sat_base - 1.0

                pp2_top = Kp_base * q_base_eff + 2 * c_base * math.sqrt(Kp_base)
                # [Fix] 使用有效重
                pp2_bot = Kp_base * (q_base_eff + gamma_base_eff * H_sk) + 2 * c_base * math.sqrt(Kp_base)
                Pp2_static = 0.5 * (pp2_top + pp2_bot) * H_sk
                y_local = (H_sk / 3.0) * (2 * pp2_top + pp2_bot) / (pp2_top + pp2_bot)
                arm_Pp2 = -y_local

                ppe2_top = Kpe_base * q_base_eff * (1 - kv) + 2 * c_base * math.sqrt(Kpe_base)
                # [Fix] 使用有效重
                ppe2_bot = Kpe_base * (q_base_eff + gamma_base_eff * H_sk) * (1 - kv) + 2 * c_base * math.sqrt(Kpe_base)
                Ppe2_dynamic = 0.5 * (ppe2_top + ppe2_bot) * H_sk

            Pp_total = Pp1_static + Pp2_static
            Ppe_total = Ppe1_dynamic + Ppe2_dynamic
            M_Pp_total = (Pp1_static * arm_Pp1) + (Pp2_static * arm_Pp2)
            arm_Pp_total = M_Pp_total / Pp_total if Pp_total > 0 else 0

            # --- [5] 穩定性檢核 ---
            # 8.1 抗傾倒
            M_resist_weight = sum(b['moment'] for b in blocks)

            x_stem_back_bot = L_bp_front + t_stem_bot
            h_act = y_resultant - H_bp
            if h_act < 0: h_act = 0
            slope_back = w_stem_back / H_stem if H_stem > 0 else 0
            arm_Pv = x_stem_back_bot - (h_act * slope_back)

            M_resist_Pv = P_total_stabilizing_V * arm_Pv
            M_resist_total = M_resist_weight + M_resist_Pv

            # [Fix] Define M_overturn explicitly
            M_overturn = M_total_driving
            FS_over = M_resist_total / M_overturn if M_overturn > 0 else 999.0

            # 8.2 抗滑動
            N_total = total_weight + P_total_stabilizing_V
            friction_coeff = math.tan(math.radians(delta_base))
            F_friction = N_total * friction_coeff + (c_base * B_total)
            P_passive_design = Ppe_total if kh > 0 else Pp_total
            F_resist_total = F_friction + P_passive_design
            FS_slide = F_resist_total / P_total_driving_H if P_total_driving_H > 0 else 999.0

            X_bar = (M_resist_total - M_overturn) / N_total if N_total > 0 else 0
            Eccentricity = (B_total / 2.0) - X_bar

            # 8.3 承載力計算 (Bearing Capacity)
            q_max = 0;
            q_min = 0
            if B_total > 0:
                if abs(Eccentricity) <= (B_total / 6.0):
                    q_max = (N_total / B_total) * (1.0 + (6.0 * abs(Eccentricity) / B_total))
                    q_min = (N_total / B_total) * (1.0 - (6.0 * abs(Eccentricity) / B_total))
                else:
                    B_eff = 3.0 * ((B_total / 2.0) - abs(Eccentricity))
                    if B_eff > 0:
                        q_max = (2.0 * N_total) / B_eff
                    q_min = 0.0

            # 角度參數 (For Report)
            report_theta_deg = theta_deg
            denom_k = 1 - kv
            report_psi_deg = math.degrees(math.atan(kh / denom_k)) if abs(denom_k) > 1e-6 else 0

            # Pack Data
            driving_forces = [
                {'name': 'Static Soil (Upper)', 'force': P_soil_1_H, 'arm': arm_soil_1,
                 'moment': P_soil_1_H * arm_soil_1},
                {'name': 'Static Soil (Lower)', 'force': P_soil_2_H, 'arm': arm_soil_2,
                 'moment': P_soil_2_H * arm_soil_2},
                {'name': 'Static Water', 'force': force_water_H, 'arm': arm_water, 'moment': force_water_H * arm_water},
                {'name': 'Surcharge', 'force': P_sur_H, 'arm': '-', 'moment': M_sur_H},
                {'name': 'Seismic Soil', 'force': P_seismic_H, 'arm': arm_seismic, 'moment': P_seismic_H * arm_seismic},
                {'name': 'Seismic Water', 'force': Delta_P_WE_H, 'arm': arm_dyn_water, 'moment': M_dynamic_water},
            ]
            passive_forces = [
                {'name': '牆前覆土 (Front)', 'static': Pp1_static, 'dynamic': Ppe1_dynamic, 'arm': arm_Pp1},
                {'name': '版底止滑榫 (Key)', 'static': Pp2_static, 'dynamic': Ppe2_dynamic, 'arm': arm_Pp2},
            ]
            key_details = {
                'has_key': True if H_sk > 0 else False, 'H_sk': H_sk, 'q_eff': q_base_eff,
                'q_soil_part': sigma_soil_front if H_sk > 0 else 0, 'q_conc_part': sigma_concrete if H_sk > 0 else 0,
                'gamma_base_eff': gamma_base_eff if H_sk > 0 else 0,
                'pp2_top': pp2_top, 'pp2_bot': pp2_bot, 'ppe2_top': ppe2_top, 'ppe2_bot': ppe2_bot,
            }
            stability_results = {
                'FS_over': round(FS_over, 3), 'FS_slide': round(FS_slide, 3),
                'M_resist': round(M_resist_total, 3), 'M_overturn': round(M_overturn, 3),
                'M_resist_weight': round(M_resist_weight, 3),
                'M_resist_Pv': round(M_resist_Pv, 3),
                'Pv_force': round(P_total_stabilizing_V, 3),
                'arm_Pv': round(arm_Pv, 3),
                'F_resist': round(F_resist_total, 3), 'F_driving': round(P_total_driving_H, 3),
                'N_total': round(N_total, 3), 'Eccentricity': round(Eccentricity, 3), 'X_bar': round(X_bar, 3),
                'B_over_6': round(B_total / 6.0, 3),
                'q_max': round(q_max, 3), 'q_min': round(q_min, 3)
            }

            sliding_details = {
                'F_driving': round(P_total_driving_H, 3),
                'N_weight': round(total_weight, 3),
                'N_soil_v': round(P_total_stabilizing_V, 3),
                'N_total': round(N_total, 3),
                'delta_base': delta_base, 'tan_delta': round(friction_coeff, 4), 'c_base': c_base,
                'B_total': round(B_total, 3),
                'F_friction_N': round(N_total * friction_coeff, 3), 'F_friction_C': round(c_base * B_total, 3),
                'F_friction_total': round(F_friction, 3),
                'is_seismic': True if kh > 0 else False,
                'P_passive': round(P_passive_design, 3),
                'F_resist_total': round(F_resist_total, 3),
                'FS': round(FS_slide, 3)
            }

            result_context = {
                'result_available': True, 'blocks': blocks, 'input_data': request.POST.dict(),
                'Ka': round(Ka, 4), 'Kp': round(Kp_front, 4), 'Kae': round(Kae, 4), 'Kpe': round(Kpe_front, 4),
                'Kp_base': round(Kp_base, 4), 'Kpe_base': round(Kpe_base, 4),
                'P_total': round(P_total_driving_H, 3), 'M_total': round(M_total_driving, 3),
                'y_resultant': round(y_resultant, 3), 'Pv_total': round(P_total_stabilizing_V, 3),
                'Pp_total': round(Pp_total, 3), 'Ppe_total': round(Ppe_total, 3), 'arm_Pp': round(arm_Pp_total, 3),
                'surcharge_info': {'type': surcharge_desc, 'force': round(P_sur_H, 3), 'moment': round(M_sur_H, 3)},
                'driving_forces': driving_forces, 'passive_forces': passive_forces,
                'key_details': key_details, 'stability': stability_results, 'sliding_details': sliding_details,
                'theta_deg': round(report_theta_deg, 2), 'psi_deg': round(report_psi_deg, 2),
                'B_total_cm': round(B_total * 100, 1),
            }
            context.update(result_context)
            request.session['calc_report_context'] = result_context

        except ValueError:
            print("Error: Invalid input data")

    return render(request, 'retaining_wall_cantilever/input.html', context)


def report_view(request):
    context = request.session.get('calc_report_context', {})
    return render(request, 'retaining_wall_cantilever/report_page.html', context)
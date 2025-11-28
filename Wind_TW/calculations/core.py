# Wind_TW/calculations/core.py
import numpy as np
from .database import WindDatabase
from .utils import interpolate_from_table


def calculate_velocity_pressure_coeff(z: float, terrain: str) -> float:
    """
    計算風速壓地況係數 K(z) (規範式 2.7)
    """
    db = WindDatabase()
    terrain_props = db.TERRAIN_DF.loc[terrain]
    zg, alpha = terrain_props['zg'], terrain_props['alpha']

    if z <= 5: z = 5
    return 2.774 * ((z / zg) ** (2 * alpha))


def calculate_velocity_pressure(z: float, I: float, V10_C: float, terrain: str, K_zt: float) -> float:
    """
    計算設計風速壓 q(z) (規範式 2.6)
    """
    K_z = calculate_velocity_pressure_coeff(z, terrain)
    return 0.06 * K_z * K_zt * (I * V10_C) ** 2


def calculate_topography_factor(topo_params: dict, z: float) -> tuple:
    """
    計算地形係數 Kzt (規範 2.6 節)
    Returns: (Kzt, K1, K2, K3)
    """
    db = WindDatabase()

    H = topo_params.get('H', 0)
    Lh = topo_params.get('Lh', 0)
    x = topo_params.get('x', 0)
    terrain = topo_params.get('terrain', 'C')
    landform = topo_params.get('landform', None)

    if not landform or H == 0:
        return 1.0, 0, 0, 0

    h_over_lh = H / Lh if Lh > 0 else 0
    lookup_h_over_lh = min(h_over_lh, 0.5)
    effective_Lh = 2 * H if h_over_lh > 0.5 else Lh

    terrain_group = 'A_or_B' if terrain in ['A', 'B'] else 'C'
    k1_col = (terrain_group, landform)
    k2_col = '山脊或山丘' if landform in ['山脊', '山丘'] else '懸崖'

    K1 = interpolate_from_table(db.K1_DF, lookup_h_over_lh, k1_col)
    K2 = interpolate_from_table(db.K2_DF, x / effective_Lh, k2_col)
    K3 = interpolate_from_table(db.K3_DF, z / effective_Lh, landform)

    Kzt = (1 + K1 * K2 * K3) ** 2
    return Kzt, K1, K2, K3


def calculate_gust_common_params(params: dict) -> dict:
    """
    計算 G 和 Gf 所需的通用參數 (z_bar, I_z, L_z, Q)
    """
    db = WindDatabase()
    h = params['h']
    B = params.get('B', 0)
    terrain = params['terrain']

    terrain_props = db.TERRAIN_DF.loc[terrain]
    z_min = terrain_props['z_min']

    # 1. 等效高度 z_bar
    z_bar = max(0.6 * h, z_min)

    # 2. 紊流強度 I_z
    c = terrain_props['c']
    I_z = c * (10 / z_bar) ** (1 / 6)

    # 3. 紊流積分尺度 L_z
    l_lambda_val = terrain_props['l_lambda']
    epsilon_bar = terrain_props['epsilon_bar']
    L_z = l_lambda_val * (z_bar / 10) ** (epsilon_bar)

    # 4. 背景反應因子 Q
    if B + h > 0:
        Q_val = np.sqrt(1 / (1 + 0.63 * ((B + h) / L_z) ** 0.63))
    else:
        Q_val = 1.0  # 避免除以零或負數的錯誤，理論上 B+h 應 > 0

    return {
        'z_bar': z_bar,
        'I_z': I_z,
        'L_z': L_z,
        'Q': Q_val
    }


def calculate_mean_wind_speed_at_height(z: float, terrain: str, V10_C: float) -> float:
    """計算每小時平均風速 V_z (用於 Gf 計算)"""
    db = WindDatabase()
    terrain_props = db.TERRAIN_DF.loc[terrain]
    b = terrain_props['b']
    alpha = terrain_props['alpha']

    return b * ((z / 10) ** alpha) * V10_C


def calculate_G_factor(params: dict, common_gust_params: dict) -> dict:
    """計算普通建築陣風反應因子 G"""
    gQ = 3.4
    gv = 3.4
    I_z = common_gust_params['I_z']
    Q = common_gust_params['Q']

    G = 1.927 * (1 + 1.7 * gQ * I_z * Q) / (1 + 1.7 * gv * I_z)

    return {
        'final_value': G, 'type': 'G',
        'gQ': gQ, 'gv': gv,
        **common_gust_params  # 合併通用參數回傳
    }


def calculate_Gf_factor(params: dict, common_gust_params: dict) -> dict:
    """
    計算柔性建築物之陣風反應因子 Gf (規範式 2.13)
    """
    # 1. 參數提取
    gQ = 3.4
    gv = 3.4
    fn = params.get('fn', 1.0)  # 加上預設值
    beta = params.get('beta', 0.02)
    h = params['h']
    B = params['B']
    L = params['L']
    I_z = common_gust_params['I_z']
    Q = common_gust_params['Q']
    L_z = common_gust_params['L_z']
    z_bar = common_gust_params['z_bar']

    # 避免 log(0) 或負數錯誤
    if fn <= 0:
        return {'final_value': 1.88, 'type': 'Gf', 'error': 'fn <= 0'}

    # 2. 計算 gR (共振反應尖峰因子)
    ln_3600fn = np.log(3600 * fn)
    gR = np.sqrt(2 * ln_3600fn) + (0.577 / np.sqrt(2 * ln_3600fn))

    # 3. 計算平均風速 V_z_bar
    # 【修正點】：使用新的參數格式呼叫，且移除 db
    V_z_bar = calculate_mean_wind_speed_at_height(
        z_bar,
        params['terrain'],
        params['V10_C']
    )

    # 4. 計算折減頻率 N1 與共振因子 Rn
    if V_z_bar > 0:
        N1 = fn * L_z / V_z_bar
        Rn = (7.47 * N1) / ((1 + 10.3 * N1) ** (5 / 3))

        # 空氣動力導納函數 (Aerodynamic Admittance Functions)
        eta_h = 4.6 * fn * h / V_z_bar
        eta_B = 4.6 * fn * B / V_z_bar
        eta_L = 15.4 * fn * L / V_z_bar
    else:
        N1, Rn, eta_h, eta_B, eta_L = 0, 0, 0, 0, 0

    # 內部輔助函式
    def get_Rj(eta):
        if eta < 1e-6: return 1.0
        return (1 / eta) - (1 / (2 * eta ** 2)) * (1 - np.exp(-2 * eta))

    Rh = get_Rj(eta_h)
    RB = get_Rj(eta_B)
    RL = get_Rj(eta_L)

    # 5. 計算共振反應因子 R
    # 注意：規範公式 (2.15)
    if beta <= 0: beta = 0.01  # 防呆

    R_squared = (1 / beta) * Rn * Rh * RB * (0.53 + 0.47 * RL)
    R = np.sqrt(R_squared) if R_squared >= 0 else 0

    # 6. 計算 Gf
    numerator = 1 + 1.7 * I_z * np.sqrt((gQ * Q) ** 2 + (gR * R) ** 2)
    denominator = 1 + 1.7 * gv * I_z
    Gf = 1.927 * (numerator / denominator)

    return {
        'final_value': Gf,
        'type': 'Gf',
        'gQ': gQ, 'gv': gv, 'gR': gR,
        'I_z': I_z, 'Q': Q, 'R': R,
        'z_bar': z_bar,
        'eta_h': eta_h, 'eta_B': eta_B, 'eta_L': eta_L,
        'V_z_bar': V_z_bar,
        'N1': N1, 'Rn': Rn,
        'Rh': Rh, 'RB': RB, 'RL': RL,
        'beta': beta, 'L_z': L_z
    }
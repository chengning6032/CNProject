# Wind_TW/calculations/handlers/enclosed.py
import numpy as np
from .base import BaseWindCalculator
from ..core import calculate_topography_factor, calculate_velocity_pressure
from ..utils import interpolate_from_table


class EnclosedGeneralHandler(BaseWindCalculator):
    """
    處理封閉式/部分封閉式建築的【通用設計法】(規範 2.2 節)
    適用於：所有高度建築，包含高層建築。
    """

    def calculate(self) -> dict:
        """
        執行通用法計算，包含 X 向與 Y 向的順風向、橫風向、扭轉向及屋頂風壓。
        """
        try:
            # 1. 計算基礎參數 (GCpi, h)
            enclosure_status = self.params.get('enclosure_status', '封閉式建築')
            gcpi_values = self.db.GCPI_DATA.get(enclosure_status, [0.0])

            results = {
                'summary': {
                    'h': self.params['h'],
                    'gcpi': gcpi_values
                },
                'X_dir': self._calculate_direction('X'),
                'Y_dir': self._calculate_direction('Y')
            }
            return results
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'error': str(e)}

    def _calculate_direction(self, wind_dir: str) -> dict:
        """
        針對特定風向 (X 或 Y) 進行計算
        """
        # 1. 準備該方向的幾何參數
        if wind_dir == 'X':
            L, B = self.params['B_X'], self.params['B_Y']
            fn = self.params.get('fn_X', 1.0)
            # 地形參數
            is_topo = self.params.get('is_topo_site_X', False)
            topo_params = self.params.get('topo_params_X', {}) if is_topo else {}
        else:  # Y
            L, B = self.params['B_Y'], self.params['B_X']
            fn = self.params.get('fn_Y', 1.0)
            is_topo = self.params.get('is_topo_site_Y', False)
            topo_params = self.params.get('topo_params_Y', {}) if is_topo else {}

        # 2. 取得陣風反應因子 G (或 Gf)
        # 注意：這裡我們暫時傳入特定的 L, B, fn 來計算該方向的 G
        # 若要考慮橫風向頻率 fa，可能需要更複雜的參數傳遞，這裡先以順風向為主
        g_details = self._get_gust_factor(h_target=self.params['h'], B_target=B, L_target=L)
        G = g_details['final_value']

        # 3. 計算 q(h)
        # 若有地形，計算 Kzt(h)
        if is_topo:
            kzt_h, _, _, _ = calculate_topography_factor(topo_params, self.params['h'])
        else:
            kzt_h = 1.0

        q_h = calculate_velocity_pressure(
            self.params['h'], self.params['I'], self.params['V10_C'],
            self.params['terrain'], kzt_h
        )

        # 4. 計算牆面 Cp
        wall_cp = self._get_wall_cp(L, B)

        # 5. 計算屋頂 Cp
        # 注意：這裡需要將 sign 傳入嗎？通用法通常只需計算 +Cp 和 -Cp 兩種情況
        # 原本邏輯是分開計算 positive/negative，這裡我們先計算係數
        roof_cp = self._get_roof_cp(wind_dir, L, B)

        # 6. 橫風向與扭轉向 (整合 simplified 2.21/2.23 或 spectral 2.22/2.24)
        # 這裡為了簡化，先只回傳參數供前端或後端進一步處理，
        # 或者您可以將 calculate_transverse_wind_force 移入此類別

        return {
            'rigidity': g_details['rigidity'],
            'G_factor': G,
            'g_details': g_details,  # 包含細節供附錄使用
            'q_h': q_h,
            'Kzt': kzt_h,
            'L': L, 'B': B,
            'L_over_B': L / B if B > 0 else 0,
            'wall_cp': wall_cp,
            'roof_cp': roof_cp
        }

    def _get_wall_cp(self, L, B):
        """計算牆面外風壓係數 (表 2.4)"""
        cp = {'windward': 0.8, 'side': -0.7}
        leeward_df = self.db.LEEWARD_WALL_DF
        ratio = L / B if B > 0 else 0
        # 使用 numpy interp 進行線性內插
        cp['leeward'] = np.interp(ratio, leeward_df.index, leeward_df['Cp'])
        return cp

    def _get_roof_cp(self, wind_dir, L, B):
        """
        計算屋頂外風壓係數 (表 2.5, 2.6, 2.7, 2.8)
        這部分是將原 `calculate_roof_coeffs` 邏輯重構
        """
        roof_type = self.params.get('roof_type')
        h = self.params['h']
        results = {}

        # Case 1: 平屋頂
        if roof_type == "flat":
            results['Cp_flat'] = -0.7
            return results

        # Case 2: 山形屋頂 (Gable)
        if roof_type == "gable":
            theta = self.params.get('theta', 0)
            ridge_orientation = self.params.get('ridge_orientation', 'X')
            is_parallel = (wind_dir == ridge_orientation)

            if is_parallel:
                # 平行屋脊
                val = -0.8 if (h / L > 2.5 or h / B > 2.5) else -0.7
                results['Cp_parallel'] = val
            else:
                # 垂直屋脊 (需內插)
                h_over_l = h / L if L > 0 else 0
                # 判斷是否需要兩個 Case (10-15度且 h/L<=0.3)
                needs_both = (10 <= theta <= 15 and h_over_l <= 0.3)

                # 負值查表
                cp_neg = self._interpolate_roof_cp_table(self.db.ROOF_CP_DF_NEG, theta, h_over_l)

                if needs_both:
                    # 分別查正值表和負值表
                    cp_pos = self._interpolate_roof_cp_table(self.db.ROOF_CP_DF_POS, theta, h_over_l)
                    cp_neg = self._interpolate_roof_cp_table(self.db.ROOF_CP_DF_NEG, theta, h_over_l)

                    results['windward_Cp_pos'] = cp_pos  # 0.2
                    results['windward_Cp_neg'] = cp_neg  # -0.9
                else:
                    cp_val = self._interpolate_roof_cp_table(self.db.ROOF_CP_DF_NEG, theta, h_over_l)
                    results['windward_Cp'] = cp_val

                results['leeward_Cp'] = -0.7
            return results

        # Case 3: 四坡水 (Hip)
        if roof_type == "hip":
            # 簡化邏輯：四坡水通常直接查表2.5，視同斜屋頂
            # 需根據風向決定是看 theta_X 還是 theta_Y
            theta = self.params.get('theta_X') if wind_dir == 'Y' else self.params.get('theta_Y')
            # 此處邏輯需與原 wind_calculations.py 保持一致
            # ... (您可將原 hip 邏輯貼於此) ...
            # 暫時回傳預設
            results['Cp_hip'] = -0.7
            return results

        # ... 其他屋頂類型 (Shed, Sawtooth, Arched) 可依此類推加入 ...

        return results

    def _interpolate_roof_cp_table(self, df, theta, h_over_l):
        """輔助函式：雙線性內插屋頂 Cp 表"""
        # 1. 對 theta 內插 (欄)
        thetas = df.columns.astype(float).values

        # 規範規定：theta >= 60 時，Cp = 0.01 * theta
        if theta >= 60:
            return 0.01 * theta

        # 找到 theta 區間
        # 使用 numpy.searchsorted 找到插入點
        idx = np.searchsorted(thetas, theta)

        # 邊界處理
        if idx == 0:
            # theta 小於最小值 (e.g., 0)，直接取第一欄
            target_col = df[thetas[0]]
        elif idx >= len(thetas):
            # theta 大於最大值 (理論上前面 >=60 已處理，但防呆)
            target_col = df[thetas[-1]]
        else:
            # 一般內插
            t1, t2 = thetas[idx - 1], thetas[idx]
            col1 = df[t1]
            col2 = df[t2]

            if t1 == t2:
                target_col = col1
            else:
                ratio = (theta - t1) / (t2 - t1)
                target_col = col1 + (col2 - col1) * ratio

        # 2. 對 h/L 內插 (列)
        # target_col 是一個 Series, index 是 h/L [0.3, 0.5, 1.0, 1.5]

        # 規範定義：<= 0.3, >= 1.5
        # 我們將 h/L 限制在表格範圍內
        h_clamped = np.clip(h_over_l, df.index.min(), df.index.max())

        # 使用 numpy.interp 進行一維線性內插
        # target_col.index 必須是排序過的 (0.3, 0.5, 1.0, 1.5)
        return np.interp(h_clamped, target_col.index, target_col.values)


class EnclosedLowRiseHandler(BaseWindCalculator):
    """
    處理低矮建築物設計風力計算式 (規範 2.13 節)
    適用條件：h < 18m 且 h/sqrt(BL) < 3 等...
    """

    def calculate(self) -> dict:
        try:
            # 1. 驗證是否符合低矮建築條件 (這部分邏輯建議保留在 service 或這裡再檢查一次)
            # 假設已符合

            results = {
                'summary': {'h': self.params['h']},
                'X_dir': self._calculate_direction('X'),
                'Y_dir': self._calculate_direction('Y')
            }
            return results
        except Exception as e:
            return {'error': str(e)}

    def _calculate_direction(self, wind_dir: str):
        if wind_dir == 'X':
            L, B = self.params['B_X'], self.params['B_Y']
            is_topo = self.params.get('is_topo_site_X', False)
            topo_params = self.params.get('topo_params_X', {}) if is_topo else {}
        else:
            L, B = self.params['B_Y'], self.params['B_X']
            is_topo = self.params.get('is_topo_site_Y', False)
            topo_params = self.params.get('topo_params_Y', {}) if is_topo else {}

        h = self.params['h']

        # 1. 計算 Kzt(h)
        if is_topo:
            kzt_h, _, _, _ = calculate_topography_factor(topo_params, h)
        else:
            kzt_h = 1.0

        # 2. 查詢 Lambda (表 2.23) - 需在 database.py 補上 LAMBDA_DF
        lambda_val = self._get_lambda(h, self.params['terrain'])

        # 3. 計算 S_Dz (順風向牆面風力, 式 2.25)
        # S_Dz = 1.49 * (I * V10)^2 * lambda * Kzt * Az
        # 這裡 Az = B * h (假設整面牆)
        az = B * h
        base_pressure = 1.49 * (self.params['I'] * self.params['V10_C']) ** 2
        s_dz = base_pressure * lambda_val * kzt_h * az

        # 4. 計算 S_Lz (橫風向, 式 2.29)
        # S_Lz = (0.6 * L/B + 0.05) * S_Dz
        s_lz = (0.6 * (L / B) + 0.05) * s_dz if B > 0 else 0

        # 5. 計算 S_Tz (扭轉向, 式 2.30)
        # S_Tz = 0.21 * (B * S_Dz)
        s_tz = 0.21 * B * s_dz

        return {
            'Kzt': kzt_h,
            'lambda': lambda_val,
            'S_Dz': s_dz,
            'S_Lz': s_lz,
            'S_Tz': s_tz,
            # 這裡可以補上屋頂風力 S_RP, S_R, S_PL 的計算
            # ...
        }

    def _get_lambda(self, h, terrain):
        """從 LAMBDA_DF 查表"""
        df = self.db.LAMBDA_DF
        # 簡單內插
        if terrain not in df.columns: return 1.0
        col = df[terrain]
        return np.interp(h, col.index, col.values)
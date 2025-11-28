# Wind_TW/calculations/handlers/structures.py
import numpy as np
from .base import BaseWindCalculator
from ..core import calculate_velocity_pressure, calculate_topography_factor


class ChimneyHandler(BaseWindCalculator):
    def calculate(self) -> dict:
        try:
            h = float(self.geo_data.get('h', 0))
            if h <= 0: return None

            shape = self.geo_data.get('shape')
            d_top = float(self.geo_data.get('D_top', 0))
            d_bot = float(self.geo_data.get('D_bot', 0))
            d_sq = float(self.geo_data.get('D', 0))
            roughness = self.geo_data.get('roughness')

            def get_cf(diameter):
                return self._calculate_cf(h, diameter, shape, roughness)

            total_force, details, g_details = self._calculate_layer_forces(
                h, d_top, d_bot, d_sq, shape, get_cf
            )

            return {
                'total_force': total_force,
                'details': details,
                'g_factor_details': g_details,
                'main_params': {'rigidity': g_details['rigidity'], 'gust_factor': g_details['final_value']}
            }
        except Exception as e:
            print(f"Chimney calc error: {e}")
            return None

    def _calculate_cf(self, h, D, shape_en, roughness_en, h_over_d_override=None):
        if D <= 0: return 0.0
        shape_map = {'square-normal': '方形', 'square-diagonal': '方形', 'hexagonal': '六邊形或八邊形',
                     'circular': '圓形'}
        condition_map = {'square-normal': '垂直', 'square-diagonal': '對角'}
        roughness_map = {'moderate-smooth': '中度光滑', 'rough': '粗糙', 'very-rough': '極粗糙'}

        shape_zh = shape_map.get(shape_en)
        condition_zh = condition_map.get(shape_en, 'N/A')
        roughness_zh = roughness_map.get(roughness_en, '所有')

        if shape_en != 'circular':
            roughness_zh = '所有'
        else:
            q_h = self._get_velocity_pressure(h, kzt=1.0)
            d_sqrt_q = D * np.sqrt(q_h)
            condition_zh = '>1.70' if d_sqrt_q > 1.70 else '<=1.70'
            if condition_zh == '<=1.70':
                roughness_zh = '所有'

        try:
            df = self.db.CHIMNEY_CF_DF
            selected_row = df.loc[(shape_zh, condition_zh, roughness_zh)]
            h_over_d = h_over_d_override if h_over_d_override is not None else (h / D)
            x_points = selected_row.index.astype(float)
            y_points = selected_row.values
            return np.interp(h_over_d, x_points, y_points)
        except Exception as e:
            print(f"Cf lookup failed: {e}")
            return 0.5


class TrussTowerHandler(BaseWindCalculator):
    def calculate(self) -> dict:
        try:
            print("\n--- 開始計算桁架高塔單一工況風力 ---")
            # 【修正 1】使用 self.params
            geo_data = self.params.get('geometry_data', {})
            general_params = self.params
            wind_dir = self.params.get('wind_direction', 'X')

            shape = geo_data.get('shape')
            e = float(geo_data.get('solidity_ratio', 0))
            member_shape = geo_data.get('member_shape')

            cf_base = 4.0 * e ** 2 - 5.9 * e + 4.0 if shape == 'square' else 3.4 * e ** 2 - 4.7 * e + 3.4

            correction_rounded = 1.0
            if member_shape == 'rounded':
                correction_rounded = min(0.51 * e ** 2 + 0.57, 1.0)

            correction_diagonal = 1.0
            if shape == 'square':
                correction_diagonal = min(1 + 0.75 * e, 1.2)

            cf_normal = cf_base * correction_rounded
            cf_final_diagonal = cf_normal * correction_diagonal

            if wind_dir == 'X':
                manual_inputs = geo_data.get('manual_inputs_x', [])
            else:
                manual_inputs = geo_data.get('manual_inputs_y', [])

            if not manual_inputs:
                return {'status': 'error', 'message': '未提供任何有效的分段輸入。'}

            h_tower = max(item.get('height', 0) for item in manual_inputs) if manual_inputs else 0
            if h_tower <= 0:
                return {'total_force_diagonal': 0, 'details': [], 'g_factor_details': None}

            assumed_width = max(h_tower / 10, 2.0)

            # 使用 base class 方法取得 G
            g_details = self._get_gust_factor(h_target=h_tower, B_target=assumed_width, L_target=assumed_width)
            gust_factor = g_details['final_value']

            total_force_normal = 0.0
            total_force_diagonal = 0.0
            calculation_details = []

            # 【修正 2】使用 self.params
            is_topo = self.params.get('is_topo_site', False)
            topo_params = self.params.get('topo_params', {})

            for item in manual_inputs:
                name = item.get('name')
                z_eff = float(item.get('height'))
                area_af = float(item.get('area'))

                if is_topo and topo_params:
                    kzt, _, _, _ = calculate_topography_factor(topo_params, z_eff)
                else:
                    kzt = 1.0

                # 【修正 3】正確呼叫 core.py 的函式 (移除 db 參數，使用 self.params)
                q_z = calculate_velocity_pressure(
                    z_eff,
                    self.params['I'],
                    self.params['V10_C'],
                    self.params['terrain'],
                    kzt
                )

                design_pressure = q_z * gust_factor * cf_final_diagonal
                force_normal = q_z * gust_factor * cf_normal * area_af
                force_diagonal = force_normal * correction_diagonal

                total_force_normal += force_normal
                total_force_diagonal += force_diagonal

                calculation_details.append({
                    'name': name, 'z_eff': z_eff, 'area': area_af,
                    'Kzt': kzt, 'q_z': q_z,
                    'force_normal': force_normal, 'force_diagonal': force_diagonal,
                })

            return {
                'cf_normal': cf_normal,
                'cf_diagonal': cf_final_diagonal,
                'correction_factor': correction_diagonal,
                'gust_factor': gust_factor,
                'g_factor_details': g_details,
                'total_force_normal': total_force_normal,
                'total_force_diagonal': total_force_diagonal,
                'details': calculation_details
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None


class WaterTowerHandler(BaseWindCalculator):
    def calculate(self) -> dict:
        try:
            results = {}
            # 【修正 1】確保這裡使用的是 self.geo_data 和 self.params
            geo_data = self.geo_data
            is_topo = self.params.get('is_topo_site', False)
            topo_params = self.params.get('topo_params', {})

            # 1. 處理水塔本體
            body_data = geo_data.get('body', {})
            if not body_data:
                return None

            body_H = float(body_data.get('h', 0))
            if body_H > 0:
                shape_en = body_data.get('shape')
                d_top = float(body_data.get('D_top', 0))
                d_bot = float(body_data.get('D_bot', 0))
                d_sq = float(body_data.get('D', 0))
                roughness_en = body_data.get('roughness')
                base_height = float(body_data.get('C', 0))

                # 借用 ChimneyHandler 實例來算 Cf
                chimney_handler = ChimneyHandler(self.params)

                def get_cf(diameter):
                    return chimney_handler._calculate_cf(body_H, diameter, shape_en, roughness_en)

                layer_height = float(body_data.get('layer_height', 2.0))
                z_bottom = base_height
                z_top = base_height + body_H
                cut_points = np.unique(np.append(np.arange(z_bottom, z_top, layer_height), z_top))

                total_body_force = 0.0
                body_details = []

                # 取得 G 因子 (使用 Base 的方法)
                g_details = self._get_gust_factor()
                G = g_details['final_value']

                for i in range(len(cut_points) - 1):
                    z1, z2 = cut_points[i], cut_points[i + 1]
                    h_layer = z2 - z1
                    if h_layer < 1e-6: continue

                    if shape_en == 'circular':
                        d1 = np.interp(z1, [z_bottom, z_top], [d_bot, d_top])
                        d2 = np.interp(z2, [z_bottom, z_top], [d_bot, d_top])
                        layer_d = (d1 + d2) / 2
                    else:
                        layer_d = d_sq

                    layer_area = layer_d * h_layer
                    z_eff = (z1 + z2) / 2

                    # 【修正 2】使用 Base 的方法取得 q(z)，自動處理地形與參數
                    q_z = self._get_velocity_pressure(z_eff)

                    cf = get_cf(layer_d)
                    force = q_z * G * cf * layer_area
                    total_body_force += force

                    body_details.append({
                        'z_range': f"{z1:.2f}-{z2:.2f}", 'z_eff': z_eff,
                        'q_z': q_z, 'cf': cf, 'area': layer_area, 'force': force
                    })

                results['body_results'] = {
                    'cf': 0,
                    'total_force': total_body_force,
                    'details': body_details
                }

            # 2. 處理支撐結構
            support_info = geo_data.get('support', {})
            if support_info.get('type') == 'truss':
                truss_params = support_info.get('truss_params', {})

                # 建立新的 params 傳給 TrussHandler
                truss_calc_params = self.params.copy()
                # 覆蓋 geometry_data 為支撐結構的數據
                truss_calc_params['geometry_data'] = truss_params

                # 呼叫 TrussTowerHandler
                truss_handler = TrussTowerHandler(truss_calc_params)
                support_results = truss_handler.calculate()

                if support_results:
                    results['support_results'] = support_results

            return results
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
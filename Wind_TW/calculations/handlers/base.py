# Wind_TW/calculations/handlers/base.py
from abc import ABC, abstractmethod
import numpy as np
from ..database import WindDatabase
from ..core import (
    calculate_gust_common_params,
    calculate_G_factor,
    calculate_Gf_factor,
    calculate_velocity_pressure,
    calculate_topography_factor
)


class BaseWindCalculator(ABC):
    def __init__(self, params: dict):
        """
        初始化計算器
        :param params: 包含單一工況所有必要參數的字典 (L, B, h, terrain, etc.)
        """
        self.params = params
        self.db = WindDatabase()  # 取得資料庫單例
        self.geo_data = params.get('geometry_data', {})
        self.general_params = params

    @abstractmethod
    def calculate(self) -> dict:
        """
        子類別必須實作此方法，回傳計算結果字典
        """
        pass

    def _get_gust_factor(self, h_target=None, B_target=None, L_target=None):
        """
        共用的陣風反應因子計算邏輯
        允許傳入特定的 h, B, L (例如計算支撐結構時)，否則使用全域參數
        """
        h = h_target if h_target is not None else self.params['h']
        B = B_target if B_target is not None else self.params['B']
        L = L_target if L_target is not None else self.params['L']

        # 準備計算 G 所需的參數
        g_params = {
            'h': h, 'B': B, 'L': L,
            'terrain': self.params['terrain'],
            'fn': self.params.get('fn', 1.0),  # 預設剛性
            'beta': self.params.get('beta', 0.01),  # 預設阻尼比
            'V10_C': self.params['V10_C'],
            'I': self.params['I']
        }

        # 判斷剛性或柔性
        rigidity = '柔性' if g_params['fn'] < 1.0 else '普通'
        common_gust = calculate_gust_common_params(g_params)

        if rigidity == '柔性':
            g_details = calculate_Gf_factor(g_params, common_gust)
        else:
            g_details = calculate_G_factor(g_params, common_gust)

        # 將剛性資訊也加入回傳
        g_details['rigidity'] = rigidity
        return g_details

    def _get_velocity_pressure(self, z, kzt=None):
        """
        計算特定高度的風速壓 q(z)
        """
        # 如果沒有指定 Kzt，則根據地形參數計算
        if kzt is None:
            # 檢查是否有地形參數
            topo_params = self.params.get('topo_params', {})
            if self.params.get('is_topo_site') and topo_params:
                kzt, _, _, _ = calculate_topography_factor(topo_params, z)
            else:
                kzt = 1.0

        return calculate_velocity_pressure(
            z,
            self.params['I'],
            self.params['V10_C'],
            self.params['terrain'],
            kzt
        )

    def _calculate_layer_forces(self, h_total, d_top, d_bot, d_sq, shape_en, cf_func):
        """
        共用的分層計算邏輯 (適用於煙囪、水塔本體等)
        """
        layer_height = float(self.geo_data.get('layer_height', 2.0))

        # 產生切割點 (0, 5, ..., h)
        cut_points = [0.0]
        if h_total > 5.0:
            cut_points.append(5.0)
            start_h = 5.0
        else:
            start_h = 0.0

        if h_total > start_h:
            cuts = np.arange(start_h + layer_height, h_total, layer_height)
            cut_points.extend(cuts.tolist())

        if cut_points[-1] != h_total:
            cut_points.append(h_total)

        cut_points = np.unique(np.array(cut_points))

        total_force = 0.0
        details = []

        for i in range(len(cut_points) - 1):
            z1, z2 = cut_points[i], cut_points[i + 1]
            h_layer = z2 - z1
            if h_layer < 1e-6: continue

            # 計算該層平均直徑/寬度
            if shape_en == 'circular':
                d1 = np.interp(z1, [0, h_total], [d_bot, d_top])
                d2 = np.interp(z2, [0, h_total], [d_bot, d_top])
                layer_avg_d = (d1 + d2) / 2
            else:
                layer_avg_d = d_sq
                d1, d2 = d_sq, d_sq

            layer_area = layer_avg_d * h_layer

            # 計算有效高度 (形心)
            if (d1 + d2) > 0:
                zc = (h_layer / 3) * (d1 + 2 * d2) / (d1 + d2)
            else:
                zc = h_layer / 2
            z_eff = z1 + zc

            # 計算該層 q(z)
            q_z = self._get_velocity_pressure(z_eff)

            # 計算該層 Cf (呼叫傳入的 cf_func)
            cf_layer = cf_func(layer_avg_d)

            # 取得 G 因子 (通常使用整體的 G)
            g_details = self._get_gust_factor()
            G = g_details['final_value']

            layer_force = q_z * G * cf_layer * layer_area
            total_force += layer_force

            details.append({
                'z_range': f"{z1:.2f}-{z2:.2f}",
                'z_eff': z_eff,
                'q_z': q_z,
                'cf': cf_layer,
                'g_factor': G,
                'area': layer_area,
                'force': layer_force
            })

        return total_force, details, g_details
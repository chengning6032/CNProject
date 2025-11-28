# Wind_TW/calculations/database.py
import pandas as pd


class WindDatabase:
    _instance = None

    # 定義資料屬性 (Type Hinting)
    TERRAIN_DF: pd.DataFrame
    K1_DF: pd.DataFrame
    K2_DF: pd.DataFrame
    K3_DF: pd.DataFrame
    LEEWARD_WALL_DF: pd.DataFrame
    ROOF_CP_DF_POS: pd.DataFrame
    ROOF_CP_DF_NEG: pd.DataFrame
    GCPI_DATA: dict
    LAMBDA_DF: pd.DataFrame
    CPC1_DF: pd.DataFrame
    CPC2_DF: pd.DataFrame
    CPC3_VALUE: float
    CHIMNEY_CF_DF: pd.DataFrame
    SOLID_SIGN_CASE_AB_DF: pd.DataFrame
    SOLID_SIGN_CASE_C_DF: pd.DataFrame
    SOLID_SIGN_REDUCTION_DF: pd.Series
    COLUMN_CF_DATA: dict
    COLUMN_R_FACTOR_DF: pd.DataFrame
    HOLLOW_SIGN_CF_DF: pd.DataFrame
    SHED_ROOF_CN_DF: pd.DataFrame
    MONOSLOPE_CC_CN_DF: pd.DataFrame
    PITCHED_CC_CN_DF: pd.DataFrame
    THROUGHED_CC_CN_DF: pd.DataFrame
    PITCHED_ROOF_CN_DF: pd.DataFrame
    THROUGHED_ROOF_CN_DF: pd.DataFrame
    FREE_ROOF_PARALLEL_WIND_CN_DF: pd.DataFrame

    # 新增 C&C 圖表數據屬性
    CC_FIG_3_1_A: dict
    CC_FIG_3_1_B: dict
    CC_FIG_3_1_C: dict
    CC_FIG_3_1_D: dict
    CC_FIG_3_2_WALL: dict
    CC_FIG_3_2_ROOF: dict

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WindDatabase, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self):
        """
        初始化所有係數表格與 DataFrame。
        """
        # ... (保留您原有的地形、煙囪等數據加載代碼，這裡省略以節省篇幅) ...
        # ... 請確保您原有的 _load_data 內容都在 ...

        # 1. 地況參數 (Table 2.2)
        terrain_data = {
            'alpha': {'A': 0.32, 'B': 0.25, 'C': 0.15}, 'zg': {'A': 500, 'B': 400, 'C': 300},
            'z_min': {'A': 18, 'B': 9, 'C': 4.5}, 'b': {'A': 0.45, 'B': 0.62, 'C': 0.94},
            'c': {'A': 0.45, 'B': 0.30, 'C': 0.20}, 'l_lambda': {'A': 55, 'B': 98, 'C': 152},
            'epsilon_bar': {'A': 0.5, 'B': 0.33, 'C': 0.20},
        }
        self.TERRAIN_DF = pd.DataFrame(terrain_data)

        # 2. 地形因子 K1 (Table 2.3a)
        k1_data = {
            ('A_or_B', '山脊'): {0.20: 0.26, 0.25: 0.33, 0.30: 0.39, 0.35: 0.46, 0.40: 0.52, 0.45: 0.59, 0.50: 0.65},
            ('A_or_B', '懸崖'): {0.20: 0.15, 0.25: 0.19, 0.30: 0.23, 0.35: 0.26, 0.40: 0.33, 0.45: 0.34, 0.50: 0.38},
            ('A_or_B', '山丘'): {0.20: 0.19, 0.25: 0.24, 0.30: 0.29, 0.35: 0.33, 0.40: 0.38, 0.45: 0.43, 0.50: 0.48},
            ('C', '山脊'): {0.20: 0.29, 0.25: 0.36, 0.30: 0.43, 0.35: 0.51, 0.40: 0.58, 0.45: 0.65, 0.50: 0.72},
            ('C', '懸崖'): {0.20: 0.17, 0.25: 0.21, 0.30: 0.26, 0.35: 0.30, 0.40: 0.34, 0.45: 0.38, 0.50: 0.43},
            ('C', '山丘'): {0.20: 0.21, 0.25: 0.26, 0.30: 0.32, 0.35: 0.37, 0.40: 0.42, 0.45: 0.47, 0.50: 0.53}
        }
        self.K1_DF = pd.DataFrame(k1_data).sort_index();
        self.K1_DF.index.name = 'H/Lh';

        # 3. 地形因子 K2 (Table 2.3b)
        k2_data = {
            '懸崖': {-4.00: 0.00, -1.50: 0.00, -1.00: 0.33, -0.50: 0.67, 0.00: 1.00, 0.50: 0.88, 1.00: 0.75, 1.50: 0.63,
                     4.00: 0.00},
            '山脊或山丘': {-4.00: 0.00, -1.50: 0.00, -1.00: 0.33, -0.50: 0.67, 0.00: 1.00, 0.50: 0.67, 1.00: 0.33,
                           1.50: 0.00, 4.00: 0.00}
        }
        self.K2_DF = pd.DataFrame(k2_data).sort_index();
        self.K2_DF.index.name = 'x/Lh';

        # 4. 地形因子 K3 (Table 2.3c)
        k3_data = {
            '山脊': {0.00: 1.00, 0.10: 0.74, 0.50: 0.22, 1.00: 0.05, 1.50: 0.01, 2.00: 0.00},
            '懸崖': {0.00: 1.00, 0.10: 0.78, 0.50: 0.29, 1.00: 0.08, 1.50: 0.02, 2.00: 0.00},
            '山丘': {0.00: 1.00, 0.10: 0.67, 0.50: 0.14, 1.00: 0.02, 1.50: 0.00, 2.00: 0.00},
        }
        self.K3_DF = pd.DataFrame(k3_data).sort_index();
        self.K3_DF.index.name = 'z/Lh';

        # 5. 背風面牆 Cp (Table 2.4)
        leeward_wall_data = {'Cp': {0: -0.5, 1: -0.5, 2: -0.3, 4: -0.2}};
        self.LEEWARD_WALL_DF = pd.DataFrame(leeward_wall_data);
        self.LEEWARD_WALL_DF.index.name = 'L/B';

        # 6. 屋頂 Cp (Table 2.5)
        roof_cp_data_pos = {
            0.0: {0.3: -0.7, 1.5: -0.7}, 10.0: {0.3: 0.2, 1.5: -0.9}, 15.0: {0.3: 0.2, 1.5: -0.9},
            20.0: {0.3: 0.2, 1.5: -0.9}, 30.0: {0.3: 0.3, 1.5: -0.9}, 40.0: {0.3: 0.4, 1.5: -0.35},
            50.0: {0.3: 0.5, 1.5: 0.2}, 60.0: {0.3: 0.6, 1.5: 0.6},
        }
        roof_cp_data_neg = {
            0.0: {0.3: -0.7, 1.5: -0.7}, 10.0: {0.3: -0.9, 1.5: -0.9}, 15.0: {0.3: -0.9, 1.5: -0.9},
            20.0: {0.3: 0.2, 1.5: -0.9}, 30.0: {0.3: 0.3, 1.5: -0.9}, 40.0: {0.3: 0.4, 1.5: -0.35},
            50.0: {0.3: 0.5, 1.5: 0.2}, 60.0: {0.3: 0.6, 1.5: 0.6},
        }
        self.ROOF_CP_DF_POS = pd.DataFrame(roof_cp_data_pos);
        self.ROOF_CP_DF_POS.index.name = 'h/L';
        self.ROOF_CP_DF_POS.columns.name = 'theta';
        self.ROOF_CP_DF_NEG = pd.DataFrame(roof_cp_data_neg);
        self.ROOF_CP_DF_NEG.index.name = 'h/L';
        self.ROOF_CP_DF_NEG.columns.name = 'theta';

        # 7. 內風壓係數 GCpi
        self.GCPI_DATA = {'開放式建築': [0.00], '部分封閉式建築': [+1.146, -1.146], '封閉式建築': [+0.375, -0.375]}

        # 8. Lambda (Table 2.23)
        lambda_data = {
            'A': {5: 0.016, 20: 0.040}, 'B': {5: 0.035, 20: 0.072}, 'C': {5: 0.092, 20: 0.142}
        }
        self.LAMBDA_DF = pd.DataFrame(lambda_data);
        self.LAMBDA_DF.index.name = 'h(m)';

        # 9. 雙斜屋頂開放式 Cpc (Table 2.24)
        self.CPC1_DF = pd.DataFrame.from_dict({0: {'p': 0, 'n': 0}, 50: {'p': 0.715, 'n': 0.462}}, orient='index')
        self.CPC2_DF = pd.DataFrame.from_dict({0: {'p': -1.410, 'n': -1.410}, 50: {'p': 0.510, 'n': -0.860}},
                                              orient='index')
        self.CPC3_VALUE = -1.410

        # 10. 煙囪 Cf (Table 2.12)
        chimney_cf_data = {
            ('方形', '垂直', '所有'): {1: 1.3, 7: 1.4, 25: 2.0}, ('方形', '對角', '所有'): {1: 1.0, 7: 1.1, 25: 1.5},
            ('六邊形或八邊形', 'N/A', '所有'): {1: 1.0, 7: 1.2, 25: 1.4},
            ('圓形', '>1.70', '中度光滑'): {1: 0.5, 7: 0.6, 25: 0.7},
            ('圓形', '>1.70', '粗糙'): {1: 0.7, 7: 0.8, 25: 0.9},
            ('圓形', '>1.70', '極粗糙'): {1: 0.8, 7: 1.0, 25: 1.2},
            ('圓形', '<=1.70', '所有'): {1: 0.7, 7: 0.8, 25: 1.2},
        }
        chimney_cf_df = pd.DataFrame.from_dict(chimney_cf_data, orient='index')
        chimney_cf_df.columns = chimney_cf_df.columns.astype(float);
        chimney_cf_df.columns.name = 'h/D'
        chimney_cf_df.index = pd.MultiIndex.from_tuples(chimney_cf_df.index, names=['形狀', '條件', '粗糙度'])
        self.CHIMNEY_CF_DF = chimney_cf_df

        # 11. 實體標示物
        solid_sign_case_ab_data = {
            0.05: {1: 1.80, 0.9: 1.85, 0.7: 1.90, 0.5: 1.95, 0.3: 1.95, 0.2: 1.95, 0.16: 1.95},
            0.1: {1: 1.70, 0.9: 1.75, 0.7: 1.85, 0.5: 1.85, 0.3: 1.90, 0.2: 1.90, 0.16: 1.90},
            0.2: {1: 1.65, 0.9: 1.70, 0.7: 1.75, 0.5: 1.80, 0.3: 1.85, 0.2: 1.85, 0.16: 1.85},
            0.5: {1: 1.55, 0.9: 1.60, 0.7: 1.70, 0.5: 1.75, 0.3: 1.80, 0.2: 1.80, 0.16: 1.80},
            1: {1: 1.45, 0.9: 1.55, 0.7: 1.65, 0.5: 1.75, 0.3: 1.80, 0.2: 1.80, 0.16: 1.80},
            2: {1: 1.40, 0.9: 1.50, 0.7: 1.60, 0.5: 1.70, 0.3: 1.80, 0.2: 1.80, 0.16: 1.80},
            4: {1: 1.35, 0.9: 1.45, 0.7: 1.60, 0.5: 1.70, 0.3: 1.80, 0.2: 1.80, 0.16: 1.85},
            5: {1: 1.35, 0.9: 1.45, 0.7: 1.55, 0.5: 1.70, 0.3: 1.80, 0.2: 1.80, 0.16: 1.85},
            10: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.70, 0.3: 1.80, 0.2: 1.85, 0.16: 1.85},
            20: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.70, 0.3: 1.85, 0.2: 1.90, 0.16: 1.90},
            30: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.70, 0.3: 1.85, 0.2: 1.90, 0.16: 1.90},
            45: {1: 1.30, 0.9: 1.40, 0.7: 1.55, 0.5: 1.75, 0.3: 1.85, 0.2: 1.95, 0.16: 1.95}
        }
        self.SOLID_SIGN_CASE_AB_DF = pd.DataFrame(solid_sign_case_ab_data)

        solid_sign_case_c_data = {
            2: {'0-s': 2.25, 's-2s': 1.50},
            3: {'0-s': 2.60, 's-2s': 1.70, '2s-3s': 1.15},
            4: {'0-s': 2.90, 's-2s': 1.90, '2s-3s': 1.30, '3s-10s': 1.10},
            5: {'0-s': 3.10, 's-2s': 2.00, '2s-3s': 1.45, '3s-10s': 1.05},
            6: {'0-s': 3.30, 's-2s': 2.15, '2s-3s': 1.55, '3s-10s': 1.05},
            7: {'0-s': 3.40, 's-2s': 2.25, '2s-3s': 1.65, '3s-10s': 1.05},
            8: {'0-s': 3.55, 's-2s': 2.30, '2s-3s': 1.70, '3s-10s': 1.05},
            9: {'0-s': 3.65, 's-2s': 2.35, '2s-3s': 1.75, '3s-10s': 1.00},
            10: {'0-s': 3.75, 's-2s': 2.45, '2s-3s': 1.85, '3s-10s': 0.95, '3s-4s': 0.95, '4s-5s': 0.95, '5s-10s': 0.95,
                 '>10s': 0.55},
            13: {'0-s': 4.00, 's-2s': 2.60, '2s-3s': 2.00, '3s-4s': 1.50, '4s-5s': 1.35, '5s-10s': 0.90, '>10s': 0.55},
            46: {'0-s': 4.30, 's-2s': 2.55, '2s-3s': 1.95, '3s-4s': 1.85, '4s-5s': 1.85, '5s-10s': 1.10, '>10s': 0.55},
        }
        self.SOLID_SIGN_CASE_C_DF = pd.DataFrame(solid_sign_case_c_data).transpose()
        self.SOLID_SIGN_REDUCTION_DF = pd.Series({0.3: 0.90, 1.0: 0.75, 2.0: 0.60})

        # 13. 角柱體
        self.COLUMN_CF_DATA = {('長方柱', '垂直於長邊'): 2.2, ('長方柱', '垂直於短邊'): 1.4,
                               ('等邊三角柱', '循著頂點'): 1.2, ('等邊三角柱', '垂直於面'): 2.0,
                               ('直角等腰三角柱', '循著直角頂'): 1.55}
        self.COLUMN_R_FACTOR_DF = pd.DataFrame({'R': {4: 0.6, 8: 0.7, 40: 0.8}})

        # 14. 中空標示物
        hollow_sign_cf_data = {
            ('平邊構材', 'N/A'): {'<0.1': 2.0, '0.1-0.29': 1.8, '0.3-0.7': 1.6},
            ('圓形斷面構材', '<=1.70'): {'<0.1': 1.2, '0.1-0.29': 1.3, '0.3-0.7': 1.5},
            ('圓形斷面構材', '>1.70'): {'<0.1': 0.8, '0.1-0.29': 0.9, '0.3-0.7': 1.1}
        }
        self.HOLLOW_SIGN_CF_DF = pd.DataFrame.from_dict(hollow_sign_cf_data, orient='index')
        self.HOLLOW_SIGN_CF_DF.index = pd.MultiIndex.from_tuples(self.HOLLOW_SIGN_CF_DF.index,
                                                                 names=['member_type', 'condition'])

        # 15. 開放式屋頂 (Shed, Monoslope, Pitched, Troughed, Parallel)
        # ... (省略部分開放式屋頂數據初始化代碼以節省空間，請保留原有的代碼) ...
        # 為了讓程式執行，這裡需要初始化這些 DF，防止其他地方報錯
        self.SHED_ROOF_CN_DF = pd.DataFrame()
        self.MONOSLOPE_CC_CN_DF = pd.DataFrame()
        self.PITCHED_CC_CN_DF = pd.DataFrame()
        self.THROUGHED_CC_CN_DF = pd.DataFrame()
        self.PITCHED_ROOF_CN_DF = pd.DataFrame()
        self.THROUGHED_ROOF_CN_DF = pd.DataFrame()
        self.FREE_ROOF_PARALLEL_WIND_CN_DF = pd.DataFrame()

        # ★★★ 關鍵修正：載入 C&C 數據 ★★★
        self._load_cc_data()

    def _load_cc_data(self):
        """
        載入局部構材(C&C)的 GCp 圖表數據。
        """
        # 圖 3.1(a) 外牆 (h <= 18m)
        self.CC_FIG_3_1_A = {
            '4': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [1.0, 1.0, 0.7], 'gcp_neg': [-1.4, -1.4, -0.9]},  # 牆角
            '5': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [1.0, 1.0, 0.7], 'gcp_neg': [-1.1, -1.1, -0.8]}  # 一般
        }

        # 圖 3.1(b) 屋頂 (h <= 18m, theta <= 7)
        self.CC_FIG_3_1_B = {
            '1': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.3, 0.3, 0.2], 'gcp_neg': [-0.9, -0.9, -0.5]},  # 內部
            '2': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.3, 0.3, 0.2], 'gcp_neg': [-1.4, -1.4, -1.1]},  # 邊緣
            '3': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.3, 0.3, 0.2], 'gcp_neg': [-2.4, -2.4, -1.1]}  # 角落
        }

        # 圖 3.1(c) 屋頂 (h <= 18m, 7 < theta <= 27)
        self.CC_FIG_3_1_C = {
            '1': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.5, 0.5, 0.3], 'gcp_neg': [-1.5, -1.5, -0.8]},
            '2': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.5, 0.5, 0.3], 'gcp_neg': [-2.3, -2.3, -1.4]},
            '3': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.5, 0.5, 0.3], 'gcp_neg': [-3.2, -3.2, -2.3]}
        }

        # 圖 3.1(d) 屋頂 (h <= 18m, 27 < theta <= 45)
        self.CC_FIG_3_1_D = {
            '1': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.9, 0.9, 0.5], 'gcp_neg': [-1.8, -1.8, -0.8]},
            '2': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.9, 0.9, 0.5], 'gcp_neg': [-2.0, -2.0, -1.0]},
            '3': {'areas': [0.1, 1.0, 50.0], 'gcp_pos': [0.9, 0.9, 0.5], 'gcp_neg': [-3.2, -3.2, -1.0]}
        }

        # 圖 3.2 (h > 18m) 牆面與平屋頂
        self.CC_FIG_3_2_WALL = {
            '4': {'areas': [2.0, 50.0], 'gcp_pos': [0.9, 0.6], 'gcp_neg': [-0.9, -0.7]},  # 牆角
            '5': {'areas': [2.0, 50.0], 'gcp_pos': [0.9, 0.6], 'gcp_neg': [-1.8, -1.0]}  # 牆面
        }
        self.CC_FIG_3_2_ROOF = {
            '1': {'areas': [1.0, 50.0], 'gcp_pos': [0.0, 0.0], 'gcp_neg': [-1.4, -0.9]},  # 內部
            '2': {'areas': [1.0, 50.0], 'gcp_pos': [0.0, 0.0], 'gcp_neg': [-2.3, -1.6]},  # 邊緣
            '3': {'areas': [1.0, 50.0], 'gcp_pos': [0.0, 0.0], 'gcp_neg': [-3.2, -2.3]}  # 角落
        }
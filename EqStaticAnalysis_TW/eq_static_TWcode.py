import pandas as pd
import numpy as np

# --- 全域設定 ---
DISTANCE_COLUMNS = ['r<=1', 'r=3', 'r=5', 'r=7', 'r=9', 'r=11', 'r=13', 'r>=14']
DISTANCE_POINTS = [1, 3, 5, 7, 9, 11, 13, 14]


# --- 輔助函式 ---
def interpolate(x_points, y_points, x_target):
    """一維線性內插函式，處理邊界條件"""
    if x_target <= x_points[0]:
        return y_points[0]
    if x_target >= x_points[-1]:
        return y_points[-1]
    return np.interp(x_target, x_points, y_points)


def get_site_amplification_factors(Ss, S1, ground_type):
    """根據表2-4計算工址放大係數 Fa, Fv"""
    # 表 2-4(a) 短週期工址放大係數 Fa
    ss_points = [0.5, 0.6, 0.7, 0.8, 0.9]
    fa_values = {
        1: [1.0, 1.0, 1.0, 1.0, 1.0],
        2: [1.1, 1.1, 1.0, 1.0, 1.0],
        3: [1.2, 1.2, 1.1, 1.0, 1.0]
    }

    # 表 2-4(b) 一秒週期工址放大係數 Fv
    s1_points = [0.30, 0.35, 0.40, 0.45, 0.50]
    fv_values = {
        1: [1.0, 1.0, 1.0, 1.0, 1.0],
        2: [1.5, 1.4, 1.3, 1.2, 1.1],
        3: [1.8, 1.7, 1.6, 1.5, 1.4]
    }

    if ground_type not in [1, 2, 3]:
        raise ValueError("地盤種類必須為 1, 2, 或 3")

    Fa = interpolate(ss_points, fa_values[ground_type], Ss)
    Fv = interpolate(s1_points, fv_values[ground_type], S1)

    return Fa, Fv


def calculate_empirical_period(hn, structure_type):
    """根據規範2.6節計算建築物基本振動週期 T"""
    if structure_type == '1':
        # 式 (2-7) 鋼構造
        return 0.085 * hn ** 0.75
    elif structure_type == '2':
        # 式 (2-8) 鋼筋混凝土造
        return 0.070 * hn ** 0.75
    elif structure_type == '3':
        # 式 (2-9) 其他
        return 0.050 * hn ** 0.75
    else:
        # 預設為最常見的RC構造
        return 0.070 * hn ** 0.75


def calculate_Sa_general(S_short, S_one, T_period, T0_boundary):
    """依據表2-5計算一般震區的Sa值"""
    if T_period <= 0.2 * T0_boundary:
        Sa = S_short * (0.4 + 3 * T_period / T0_boundary)
    elif 0.2 * T0_boundary < T_period <= T0_boundary:
        Sa = S_short
    elif T0_boundary < T_period <= 2.5 * T0_boundary:
        Sa = S_one / T_period
    else:  # T_period > 2.5 * T0_boundary
        Sa = 0.4 * S_short
    return Sa


def calculate_Sa_taipei(S_short, T_period, T0_boundary):
    """依據表2-7計算臺北盆地的Sa值"""
    if T_period <= 0.2 * T0_boundary:
        Sa = S_short * (0.4 + 3 * T_period / T0_boundary)
    elif 0.2 * T0_boundary < T_period <= T0_boundary:
        Sa = S_short
    elif T0_boundary < T_period <= 2.5 * T0_boundary:
        # 注意：臺北盆地的公式與一般震區在此段不同
        Sa = S_short * T0_boundary / T_period
    else:  # T_period > 2.5 * T0_boundary
        Sa = 0.4 * S_short
    return Sa


def calculate_Fu(R, T, T0D, is_taipei_basin, mode=1):
    """根據規範2.9節及式(2-12)計算結構系統地震力折減係數 Fu"""
    if is_taipei_basin:
        Ra = 1 + (R - 1) / 2.0  # 式(2-11)
    else:
        Ra = 1 + (R - 1) / 1.5  # 式(2-10)

    # 根據 mode 決定是使用 Ra 還是 R
    # mode=1 (設計地震) 使用 Ra, mode=2 (最大考量地震) 使用 R
    if mode == 2:
        current_Ra = R
    else:
        current_Ra = Ra

    sqrt_2Ra_minus_1 = (2 * current_Ra - 1) ** 0.5

    # 根據式 (2-12) 的四個區段
    if T >= T0D:
        Fu = current_Ra
    elif 0.6 * T0D <= T < T0D:
        Fu = sqrt_2Ra_minus_1 + (current_Ra - sqrt_2Ra_minus_1) * (T - 0.6 * T0D) / (0.4 * T0D)
    elif 0.2 * T0D <= T < 0.6 * T0D:
        Fu = sqrt_2Ra_minus_1
    else:  # T < 0.2 * T0D
        Fu = 1 + (sqrt_2Ra_minus_1 - 1) * T / (0.2 * T0D)

    return Fu, Ra


def calculate_Sa_over_Fu_m(Sa, Fu):
    """根據式(2-2)或(2-13d)修正譜加速度與折減係數之比值"""
    ratio = Sa / Fu
    if ratio <= 0.3:
        return ratio
    elif 0.3 < ratio < 0.8:
        return 0.52 * ratio + 0.144
    else:
        return 0.70 * ratio


# --- 主要功能函式 ---
def get_seismic_params_interactive(general_csv='seismic_data_general.csv',
                                   fault_csv='seismic_data_faults.csv',
                                   taipei_csv='seismic_data_taipei_special.csv'):
    try:
        df_general = pd.read_csv(general_csv)
        df_faults = pd.read_csv(fault_csv)
        df_taipei = pd.read_csv(taipei_csv)
    except FileNotFoundError as e:
        print(f"錯誤: 找不到檔案 '{e.filename}'。請確認所有 CSV 檔案都與程式碼在同一個資料夾。")
        return

    # --- 步驟 1: 地點查詢 ---
    county = input("請輸入縣市名稱 (例如: 新北市 或 臺北市): ")
    township = input("請輸入鄉鎮市區名稱 (例如: 三重區): ")

    location_data = None
    is_taipei_special = False

    if county in ["新北市", "臺北市"]:
        taipei_township_data = df_taipei[(df_taipei['County'] == county) & (df_taipei['Township'] == township)]

        if not taipei_township_data.empty:
            is_taipei_special = True
            unique_villages = taipei_township_data['Village'].unique()
            if len(unique_villages) == 1 and unique_villages[0] == "全區所有里":
                print(f"\n找到 {county}{township} 的資料，適用於'全區所有里'。")
                location_data = taipei_township_data.iloc[0]
            else:
                village = input(f"'{township}'的地震分區依里而定，請輸入里名 (例如: 永福里): ")
                result = taipei_township_data[taipei_township_data['Village'] == village]
                if not result.empty:
                    location_data = result.iloc[0]

    if location_data is None and not is_taipei_special:
        result = df_general[(df_general['County'] == county) & (df_general['Township'] == township)]
        if not result.empty:
            location_data = result.iloc[0]

    if location_data is None:
        print("\n查無此地點資料，請檢查輸入是否正確。")
        return

    # --- 步驟 2: 參數初始化與分類處理 ---
    SDS, SMS, T0D, T0M = 0, 0, 0, 0
    SD1, SM1 = 0, 0
    is_taipei_basin = False
    is_near_fault = False

    print("\n--- 初始查詢結果 ---")
    if is_taipei_special and location_data.get('Zone_Type') == "Basin":
        is_taipei_basin = True
        village_info = location_data['Village'] if location_data['Village'] != '全區所有里' else ''
        print(f"地點: {county}{township}{village_info} (類別: 盆地區)")

        SDS = location_data['SDS']
        SMS = location_data['SMS']
        T0D = T0M = location_data['T0_sec']

        print(f"分區: {location_data['Zone_Name']}")
        print(f"  工址短週期設計譜加速度係數 SDS: {SDS}")
        print(f"  工址短週期最大考量譜加速度係數 SMS: {SMS}")
        print(f"  轉換週期 T0: {T0D} 秒")

        SD1 = SDS * T0D
        SM1 = SMS * T0M
        SDS_no_fault, SD1_no_fault, T0D_no_fault = SDS, SD1, T0D

    else:  # 一般震區 (包含台北的一般震區)
        print(location_data)

        final_Ss_params = {
            'SsD': location_data['SsD'], 'S1D': location_data['S1D'],
            'SsM': location_data['SsM'], 'S1M': location_data['S1M']
        }
        ss_params_no_fault = {
            'SsD': location_data['SsD'], 'S1D': location_data['S1D']
        }

        faults_str = location_data.get('Nearby_Faults')

        if not pd.isna(faults_str):
            is_near_fault = True
            print("\n--- 調整近斷層效應 ---")
            faults_list = [f.strip() for f in faults_str.replace('、', ',').split(',')]
            print(f"注意：此地區鄰近斷層: {', '.join(faults_list)}")

            for fault in faults_list:
                print("-" * 20)
                while True:
                    try:
                        r = float(input(f"請輸入工址至【{fault}】的最短水平距離 r (公里): "))
                        if r < 0:
                            print("距離不可為負數，請重新輸入。")
                            continue
                        break
                    except ValueError:
                        print("輸入無效，請輸入一個數字。")

                fault_rules = df_faults[df_faults['Fault_Name'] == fault]
                if fault_rules.empty:
                    print(f"警告：斷層資料庫中找不到 '{fault}' 的數據，將忽略。")
                    continue

                matched_rule_group = None
                township_rules = fault_rules[fault_rules['Region_Type'] == 'Township']
                for _, rule in township_rules.iterrows():
                    if township in rule['Affected_Regions']:
                        region_key = rule['Affected_Regions']
                        matched_rule_group = township_rules[township_rules['Affected_Regions'] == region_key]
                        break

                if matched_rule_group is None:
                    county_rules = fault_rules[fault_rules['Region_Type'] == 'County']
                    for _, rule in county_rules.iterrows():
                        if county in rule['Affected_Regions']:
                            region_key = rule['Affected_Regions']
                            matched_rule_group = county_rules[county_rules['Affected_Regions'] == region_key]
                            break

                if matched_rule_group is not None:
                    region_name = matched_rule_group.iloc[0]['Affected_Regions']
                    print(f"-> 正在計算 '{fault}' 的影響 (套用 '{region_name}' 規則)...")
                    for param in ['SsD', 'S1D', 'SsM', 'S1M']:
                        param_row = matched_rule_group[matched_rule_group['Parameter'] == param]
                        if not param_row.empty:
                            y_points = param_row[DISTANCE_COLUMNS].iloc[0].values.astype(float)
                            adjusted_val = interpolate(DISTANCE_POINTS, y_points, r)
                            final_Ss_params[param] = max(final_Ss_params[param], adjusted_val)
                            print(
                                f"  '{fault}' (r={r}km) 調整後 {param}: {adjusted_val:.4f} -> 當前最大值: {final_Ss_params[param]:.4f}")
                else:
                    print(f"警告：在 '{fault}' 的數據中找不到適用於 '{county} {township}' 的規則。")
        else:
            print("\n此地區無須考慮近斷層效應。")

        print("\n" + "=" * 40)
        print("--- 計算工址放大係數 (假設為普通地盤) ---")
        ground_type = 2

        FaD, FvD = get_site_amplification_factors(final_Ss_params['SsD'], final_Ss_params['S1D'], ground_type)
        SDS = FaD * final_Ss_params['SsD']
        SD1 = FvD * final_Ss_params['S1D']

        FaM, FvM = get_site_amplification_factors(final_Ss_params['SsM'], final_Ss_params['S1M'], ground_type)
        SMS = FaM * final_Ss_params['SsM']
        SM1 = FvM * final_Ss_params['S1M']

        FaD_no_fault, FvD_no_fault = get_site_amplification_factors(ss_params_no_fault['SsD'],
                                                                    ss_params_no_fault['S1D'], ground_type)
        SDS_no_fault = FaD_no_fault * ss_params_no_fault['SsD']
        SD1_no_fault = FvD_no_fault * ss_params_no_fault['S1D']

        print("\n[用於設計地震/最大考量地震 (考慮近斷層)]")
        print(
            f"最終震區參數: SsD={final_Ss_params['SsD']:.4f}, S1D={final_Ss_params['S1D']:.4f}, SsM={final_Ss_params['SsM']:.4f}, S1M={final_Ss_params['S1M']:.4f}")
        print(f"工址譜加速度: SDS={SDS:.4f}, SD1={SD1:.4f}, SMS={SMS:.4f}, SM1={SM1:.4f}")

        print("\n[用於中小度地震 (不考慮近斷層)]")
        print(f"原始震區參數: SsD={ss_params_no_fault['SsD']:.4f}, S1D={ss_params_no_fault['S1D']:.4f}")
        print(f"工址譜加速度: SDS_no_fault={SDS_no_fault:.4f}, SD1_no_fault={SD1_no_fault:.4f}")

        T0D = SD1 / SDS if SDS > 0 else 0
        T0M = SM1 / SMS if SMS > 0 else 0
        T0D_no_fault = SD1_no_fault / SDS_no_fault if SDS_no_fault > 0 else 0
        print(f"\n長短週期分界: T0D={T0D:.3f}s, T0M={T0M:.3f}s, T0D_no_fault={T0D_no_fault:.3f}s")

    # --- 步驟 3: 計算週期 ---
    print("\n" + "=" * 40)
    print("--- 步驟: 計算建築週期 ---")
    while True:
        try:
            hn_str = input("請輸入建築物高度 hn (公尺): ")
            hn = float(hn_str)
            structure_type_str = input("請輸入結構系統 [1]鋼構造 [2]鋼筋混凝土造 [3]其他: ")
            if hn > 0 and structure_type_str in ['1', '2', '3']:
                break
            else:
                print("輸入無效。")
        except ValueError:
            print("請輸入數字。")

    T_empirical = calculate_empirical_period(hn, structure_type_str)
    T_limit = 1.4 * T_empirical
    print(f"依規範2.6節計算之經驗週期 T = {T_empirical:.3f} 秒")
    print(f"使用者輸入之週期不得超過 {T_limit:.3f} 秒 (1.4T)")

    Tx_input_str = input("請輸入建築物X方向週期 Tx (秒) [留白則使用經驗週期]: ")
    Tx = float(Tx_input_str) if Tx_input_str else T_empirical
    if Tx > T_limit:
        print(f"Tx ({Tx:.3f}s) 超過上限，將使用 {T_limit:.3f}s 進行計算。")
        Tx = T_limit

    Ty_input_str = input("請輸入建築物Y方向週期 Ty (秒) [留白則使用經驗週期]: ")
    Ty = float(Ty_input_str) if Ty_input_str else T_empirical
    if Ty > T_limit:
        print(f"Ty ({Ty:.3f}s) 超過上限，將使用 {T_limit:.3f}s 進行計算。")
        Ty = T_limit

    print(f"\n最終用於計算之週期: Tx={Tx:.3f}s, Ty={Ty:.3f}s")

    # --- 步驟 4: 計算 SaD, SaM ---
    if is_taipei_basin:
        SaDX = calculate_Sa_taipei(SDS, Tx, T0D)
        SaDY = calculate_Sa_taipei(SDS, Ty, T0D)
        SaDX_no_fault, SaDY_no_fault = SaDX, SaDY
        SaMX = calculate_Sa_taipei(SMS, Tx, T0M)
        SaMY = calculate_Sa_taipei(SMS, Ty, T0M)
    else:
        SaDX = calculate_Sa_general(SDS, SD1, Tx, T0D)
        SaDY = calculate_Sa_general(SDS, SD1, Ty, T0D)
        SaDX_no_fault = calculate_Sa_general(SDS_no_fault, SD1_no_fault, Tx, T0D_no_fault)
        SaDY_no_fault = calculate_Sa_general(SDS_no_fault, SD1_no_fault, Ty, T0D_no_fault)
        SaMX = calculate_Sa_general(SMS, SM1, Tx, T0M)
        SaMY = calculate_Sa_general(SMS, SM1, Ty, T0M)

    # --- 步驟 5: 輸入用途與結構參數 ---
    print("\n" + "=" * 40)
    print("--- 步驟: 輸入用途、結構及設計參數 ---")
    print("请根据建筑用途选择类别 (规范 2.8 节):")
    print("  [1] 第一、二类 (I=1.5)")
    print("  [3] 第三类 (I=1.25)")
    print("  [4] 第四类 (I=1.0)")
    while True:
        choice = input("请输入类别 [1/3/4]: ")
        if choice in ['1', '2']:
            I = 1.5; break
        elif choice == '3':
            I = 1.25; break
        elif choice == '4':
            I = 1.0; break
        else:
            print("输入无效。")

    while True:
        try:
            Rx = float(input("請輸入【X方向】結構系統之韌性容量 Rx (請參考規範 表 1-3): "))
            if Rx > 0: break
        except ValueError:
            print("請輸入數字。")

    while True:
        try:
            Ry = float(input("請輸入【Y方向】結構系統之韌性容量 Ry (請參考規範 表 1-3): "))
            if Ry > 0: break
        except ValueError:
            print("請輸入數字。")

    alpha_y = 0.0
    if structure_type_str == '1':  # 鋼構造
        print("\n請選擇鋼結構之設計方法:")
        print("  [1] 容許應力設計法 (ASD)")
        print("  [2] 極限強度設計法 (極限設計法, LRFD)")
        while True:
            choice_steel = input("請輸入設計方法 [1/2]: ")
            if choice_steel == '1':
                alpha_y = 1.2; break
            elif choice_steel == '2':
                alpha_y = 1.0; break
            else:
                print("輸入無效。")
    elif structure_type_str == '2':  # 鋼筋混凝土造
        print("\n請選擇鋼筋混凝土構造之極限強度設計法類型:")
        print("  [1] 一般情況 (地震力載重因子非1.0)")
        print("  [2] 地震力載重因子取 1.0 設計者")
        while True:
            choice_rc = input("請輸入設計類型 [1/2]: ")
            if choice_rc == '1':
                alpha_y = 1.5; break
            elif choice_rc == '2':
                alpha_y = 1.0; break
            else:
                print("輸入無效。")
    elif structure_type_str == '3':  # 其他
        print("\n因結構系統為'其他'，請依所採用之設計方法自行分析決定 αy 值。")
        while True:
            try:
                alpha_y_str = input("請手動輸入 αy 值: ")
                alpha_y = float(alpha_y_str)
                if alpha_y > 0:
                    break
                else:
                    print("αy 必須為正數。")
            except ValueError:
                print("請輸入數字。")

    # --- 步驟 6: 計算 Fu & (Sa/Fu)m ---
    FuDX, RaX = calculate_Fu(Rx, Tx, T0D, is_taipei_basin, mode=1)
    FuDY, RaY = calculate_Fu(Ry, Ty, T0D, is_taipei_basin, mode=1)
    FuMX, _ = calculate_Fu(Rx, Tx, T0M, is_taipei_basin, mode=2)
    FuMY, _ = calculate_Fu(Ry, Ty, T0M, is_taipei_basin, mode=2)
    FuDX_no_fault, _ = calculate_Fu(Rx, Tx, T0D_no_fault, is_taipei_basin, mode=1)
    FuDY_no_fault, _ = calculate_Fu(Ry, Ty, T0D_no_fault, is_taipei_basin, mode=1)

    SaD_over_FuD_m_X = calculate_Sa_over_Fu_m(SaDX, FuDX)
    SaD_over_FuD_m_Y = calculate_Sa_over_Fu_m(SaDY, FuDY)
    SaD_over_FuD_m_X_no_fault = calculate_Sa_over_Fu_m(SaDX_no_fault, FuDX_no_fault)
    SaD_over_FuD_m_Y_no_fault = calculate_Sa_over_Fu_m(SaDY_no_fault, FuDY_no_fault)
    SaM_over_FuM_m_X = calculate_Sa_over_Fu_m(SaMX, FuMX)
    SaM_over_FuM_m_Y = calculate_Sa_over_Fu_m(SaMY, FuMY)

    # --- 步驟 7: 計算總橫力係數 ---
    C_VX = (I / (1.4 * alpha_y)) * SaD_over_FuD_m_X
    C_VY = (I / (1.4 * alpha_y)) * SaD_over_FuD_m_Y

    V_star_divisor = 3.5 if is_taipei_basin else 4.2
    C_V_star_X = (I * FuDX_no_fault / (V_star_divisor * alpha_y)) * SaD_over_FuD_m_X_no_fault
    C_V_star_Y = (I * FuDY_no_fault / (V_star_divisor * alpha_y)) * SaD_over_FuD_m_Y_no_fault

    C_VMX = (I / (1.4 * alpha_y)) * SaM_over_FuM_m_X
    C_VMY = (I / (1.4 * alpha_y)) * SaM_over_FuM_m_Y

    # --- 【新增】步驟 8: 計算垂直地震力係數 ---
    print("\n" + "=" * 40)
    print("--- 步驟: 計算垂直地震力係數 (2.18節) ---")

    print("\n請選擇垂直地震力計算模式:")
    print("  [1] 標準模式 (X, Y方向獨立計算，符合規範精神)")
    print("  [2] 保守模式 (統一採用X, Y方向中較不利的水平反應進行計算)")
    while True:
        v_mode = input("請輸入模式 [1/2]: ")
        if v_mode in ['1', '2']:
            break
        else:
            print("輸入無效。")

    Rv = 3.0  # 根據解說，垂直向韌性容量 R 暫訂為 3.0
    vertical_ratio = 2 / 3 if is_near_fault else 1 / 2
    print(f"\n此地區為 {'近斷層區' if is_near_fault else '一般區'}，垂直力與水平力比例為 {vertical_ratio:.2f}")

    SaDV_eff, Fuv_eff, Tv_eff = 0, 0, 0
    if v_mode == '1':
        print("採標準模式，X 與 Y 方向獨立計算。")
        # 假設垂直向週期與水平向相同
        TvX, TvY = Tx, Ty

        SaDVX = SaDX * vertical_ratio
        SaDVY = SaDY * vertical_ratio

        FuvX, _ = calculate_Fu(Rv, TvX, T0D, is_taipei_basin, mode=1)
        FuvY, _ = calculate_Fu(Rv, TvY, T0D, is_taipei_basin, mode=1)

        SaDV_over_Fuv_m_X = calculate_Sa_over_Fu_m(SaDVX, FuvX)
        SaDV_over_Fuv_m_Y = calculate_Sa_over_Fu_m(SaDVY, FuvY)

        C_VZX = (I / (1.4 * alpha_y)) * SaDV_over_Fuv_m_X
        C_VZY = (I / (1.4 * alpha_y)) * SaDV_over_Fuv_m_Y
    else:  # v_mode == '2'
        print("採保守模式，取較大水平反應計算。")
        if SaDX >= SaDY:
            print("X向水平反應較大 (SaDX >= SaDY)，將以X向參數計算統一垂直力。")
            Tv_eff = Tx
            SaD_eff = SaDX
        else:
            print("Y向水平反應較大 (SaDY > SaDX)，將以Y向參數計算統一垂直力。")
            Tv_eff = Ty
            SaD_eff = SaDY

        SaDV_eff = SaD_eff * vertical_ratio
        Fuv_eff, _ = calculate_Fu(Rv, Tv_eff, T0D, is_taipei_basin, mode=1)
        SaDV_over_Fuv_m = calculate_Sa_over_Fu_m(SaDV_eff, Fuv_eff)
        C_VZX = C_VZY = (I / (1.4 * alpha_y)) * SaDV_over_Fuv_m

    # 柱子專用係數 (與方向無關，只與SDS有關)
    C_column = 0
    if is_near_fault:
        C_column = (0.80 * SDS * I) / (3 * alpha_y)
    else:
        C_column = (0.40 * SDS * I) / (2 * alpha_y)

    # --- 最終輸出 ---
    print("\n" + "=" * 40)
    print("--- 最終總橫力係數計算結果 ---")
    print(f"  基本參數: I={I}, αy={alpha_y}")
    print(f"  X方向: Rx={Rx}, Tx={Tx:.3f}s | Y方向: Ry={Ry}, Ty={Ty:.3f}s")

    print("\n1. 最小設計總橫力係數 C (2.2節)")
    print(f"   X方向: V = {C_VX:.4f} * W")
    print(f"   Y方向: V = {C_VY:.4f} * W")

    print("\n2. 中小度地震降伏之設計地震力係數 C* (2.10.1節)")
    print(f"   X方向: V* = {C_V_star_X:.4f} * W")
    print(f"   Y方向: V* = {C_V_star_Y:.4f} * W")

    print("\n3. 最大考量地震崩塌之設計地震力係數 CM (2.10.2節)")
    print(f"   X方向: VM = {C_VMX:.4f} * W")
    print(f"   Y方向: VM = {C_VMY:.4f} * W")

    print("\n4. 垂直地震力係數 Cz (2.18節)")
    print(f"   X方向 (梁版用): Vz = {C_VZX:.4f} * W")
    print(f"   Y方向 (梁版用): Vz = {C_VZY:.4f} * W")
    print(f"   柱子專用係數 C_column = {C_column:.4f}")

    print("\n" + "=" * 40)
    print("【設計提醒】")
    print("1. 用於強度設計之基底剪力係數，應取 C 與 C* 之較大值。")
    print(f"   X方向建議設計係數 C_design,x = max({C_VX:.4f}, {C_V_star_X:.4f}) = {max(C_VX, C_V_star_X):.4f}")
    print(f"   Y方向建議設計係數 C_design,y = max({C_VY:.4f}, {C_V_star_Y:.4f}) = {max(C_VY, C_V_star_Y):.4f}")
    print("\n2. 用於崩塌檢核之基底剪力係數為 CM。")
    print("   完成強度設計後，須另以 VM (或 CM) 進行韌性檢核，確保結構不崩塌。")
    print("\n3. 垂直地震力應依規範納入載重組合中進行分析與檢核。")


if __name__ == "__main__":
    get_seismic_params_interactive()
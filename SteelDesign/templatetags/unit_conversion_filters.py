from django import template
import numpy as np

register = template.Library()

# --- 單位換算常數 ---
IN_TO_CM = 2.54
KSI_TO_KGF_CM2 = 70.307
PSI_TO_KGF_CM2 = 0.070307
KIP_TO_TF = 0.453592          # 新增：千磅 -> 噸力
KIP_IN_TO_TF_M = 0.011521     # 新增：千磅-英寸 -> 噸力-米
KIP_IN_PER_IN_TO_TF_M_PER_M = 0.45358

# --- 輔助函式 ---
def is_number(value):
    """檢查值是否為數字 (int, float, numpy number)"""
    return isinstance(value, (int, float, np.number))

# --- 過濾器 ---
@register.filter(name='to_cm')
def to_cm(value_in_inches, precision=2):
    """將英寸轉換為厘米，並格式化小數位數"""
    if not is_number(value_in_inches):
        return value_in_inches
    cm_value = float(value_in_inches) * IN_TO_CM
    return f"{cm_value:.{precision}f}"

@register.filter(name='to_kgf_cm2_from_ksi')
def to_kgf_cm2_from_ksi(value_in_ksi, precision=2):
    """將 ksi 轉換為 kgf/cm²，並格式化小數位數"""
    if not is_number(value_in_ksi):
        return value_in_ksi
    kgf_value = float(value_in_ksi) * KSI_TO_KGF_CM2
    return f"{kgf_value:.{precision}f}"

@register.filter(name='to_kgf_cm2_from_psi')
def to_kgf_cm2_from_psi(value_in_psi, precision=2):
    """將 psi 轉換為 kgf/cm²，並格式化小數位數"""
    if not is_number(value_in_psi):
        return value_in_psi
    kgf_value = float(value_in_psi) * PSI_TO_KGF_CM2
    return f"{kgf_value:.{precision}f}"

@register.filter(name='to_tf')
def to_tf(value_in_kips, precision=2):
    """將 kips 轉換為 tf"""
    if not is_number(value_in_kips): return value_in_kips
    tf_value = float(value_in_kips) * KIP_TO_TF
    return f"{tf_value:.{precision}f}"

@register.filter(name='to_tf_m')
def to_tf_m(value_in_kip_in, precision=2):
    """將 kip-in 轉換為 tf-m"""
    if not is_number(value_in_kip_in): return value_in_kip_in
    tf_m_value = float(value_in_kip_in) * KIP_IN_TO_TF_M
    return f"{tf_m_value:.{precision}f}"

@register.filter(name='to_tf_m_per_m')
def to_tf_m_per_m(value_in_kip_in_per_in, precision=3):
    """將 kip-in/in 轉換為 tf-m/m"""
    if not is_number(value_in_kip_in_per_in):
        return value_in_kip_in_per_in
    tf_m_value = float(value_in_kip_in_per_in) * KIP_IN_PER_IN_TO_TF_M_PER_M
    return f"{tf_m_value:.{precision}f}"
def safe_dc_ratio(demand, capacity):
    """
    安全地计算 D/C Ratio。
    如果容量为 0, None, 或极小，则回传 None (会被序列化为 JSON 的 null)。
    """
    if capacity is None or abs(capacity) < 1e-9:
        return None
    if demand is None:
        return 0.0
    return demand / capacity
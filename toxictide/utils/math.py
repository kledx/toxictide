"""
TOXICTIDE Math Utils

数学工具函数
"""


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """安全除法
    
    Args:
        a: 分子
        b: 分母
        default: 分母为 0 时的默认返回值
    
    Returns:
        a / b 或 default
    
    Example:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0, default=0.0)
        0.0
    """
    return a / b if b != 0 else default


def clip(x: float, min_val: float, max_val: float) -> float:
    """裁剪值到指定范围
    
    Args:
        x: 输入值
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        裁剪后的值
    
    Example:
        >>> clip(5.0, 0.0, 10.0)
        5.0
        >>> clip(-5.0, 0.0, 10.0)
        0.0
        >>> clip(15.0, 0.0, 10.0)
        10.0
    """
    return max(min_val, min(max_val, x))


def bps_to_decimal(bps: float) -> float:
    """将基点转换为小数
    
    Args:
        bps: 基点值（1 bps = 0.01%）
    
    Returns:
        小数值
    
    Example:
        >>> bps_to_decimal(100)
        0.01
    """
    return bps / 10000.0


def decimal_to_bps(decimal: float) -> float:
    """将小数转换为基点
    
    Args:
        decimal: 小数值
    
    Returns:
        基点值
    
    Example:
        >>> decimal_to_bps(0.01)
        100.0
    """
    return decimal * 10000.0

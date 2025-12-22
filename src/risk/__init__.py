# Input: RiskManager and protective stop
# Output: risk exports
# Pos: risk package initializer
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
风控模块

导出：
- RiskManager: 风险管理器
- ProtectiveStopManager: 保护性止损管理器
"""

from src.risk.manager import RiskManager
from src.risk.protective_stop import ProtectiveStopManager

__all__ = ["RiskManager", "ProtectiveStopManager"]

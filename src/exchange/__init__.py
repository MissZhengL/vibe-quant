# Input: ExchangeAdapter
# Output: exchange exports
# Pos: exchange package initializer
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
交易所模块

导出：
- ExchangeAdapter: 交易所适配器
"""

from src.exchange.adapter import ExchangeAdapter

__all__ = ["ExchangeAdapter"]

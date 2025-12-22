# Input: config loader and models
# Output: config exports
# Pos: config package initializer
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
配置模块

导出：
- ConfigLoader: 配置加载器
- AppConfig: 应用配置
- MergedSymbolConfig: 合并后的 symbol 配置
"""

from src.config.loader import ConfigLoader
from src.config.models import (
    AppConfig,
    MergedSymbolConfig,
    WSConfig,
    ReconnectConfig,
    ExecutionConfig,
    AccelConfig,
    AccelTier,
    RoiConfig,
    RoiTier,
    RiskConfig,
    RateLimitConfig,
    TelegramConfig,
    TelegramEventsConfig,
    SymbolConfig,
    SymbolExecutionConfig,
    SymbolAccelConfig,
    SymbolRoiConfig,
    GlobalConfig,
)

__all__ = [
    "ConfigLoader",
    "AppConfig",
    "MergedSymbolConfig",
    "WSConfig",
    "ReconnectConfig",
    "ExecutionConfig",
    "AccelConfig",
    "AccelTier",
    "RoiConfig",
    "RoiTier",
    "RiskConfig",
    "RateLimitConfig",
    "TelegramConfig",
    "TelegramEventsConfig",
    "SymbolConfig",
    "SymbolExecutionConfig",
    "SymbolAccelConfig",
    "SymbolRoiConfig",
    "GlobalConfig",
]

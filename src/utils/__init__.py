# Input: helper and logger modules
# Output: utils exports
# Pos: utils package initializer
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
工具模块

导出：
- setup_logger, get_logger, log_event: 日志工具
- log_startup, log_shutdown, log_ws_*, log_signal, log_order_*, log_position_update, log_error: 便捷日志函数
- round_to_tick, round_up_to_tick, round_to_step, round_up_to_step: 规整函数
- current_time_ms: 时间工具
- symbol_to_ws_stream, ws_stream_to_symbol: symbol 转换
"""

from src.utils.logger import (
    setup_logger,
    get_logger,
    log_event,
    log_startup,
    log_shutdown,
    log_ws_connect,
    log_ws_disconnect,
    log_ws_reconnect,
    log_market_update,
    log_signal,
    log_order_place,
    log_order_cancel,
    log_order_fill,
    log_order_timeout,
    log_position_update,
    log_error,
)
from src.utils.helpers import (
    round_to_tick,
    round_up_to_tick,
    round_to_step,
    round_up_to_step,
    current_time_ms,
    symbol_to_ws_stream,
    ws_stream_to_symbol,
)

__all__ = [
    # 日志
    "setup_logger",
    "get_logger",
    "log_event",
    "log_startup",
    "log_shutdown",
    "log_ws_connect",
    "log_ws_disconnect",
    "log_ws_reconnect",
    "log_market_update",
    "log_signal",
    "log_order_place",
    "log_order_cancel",
    "log_order_fill",
    "log_order_timeout",
    "log_position_update",
    "log_error",
    # 规整函数
    "round_to_tick",
    "round_up_to_tick",
    "round_to_step",
    "round_up_to_step",
    # 时间
    "current_time_ms",
    # Symbol 转换
    "symbol_to_ws_stream",
    "ws_stream_to_symbol",
]

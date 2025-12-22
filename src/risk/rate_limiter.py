# Input: request timestamps and limits
# Output: allow/deny decisions
# Pos: sliding window rate limiter
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
全局限速器（账户级）

用于限制下单/撤单频率，避免触发交易所速率限制。
实现采用固定窗口滑动计数：统计最近 1 秒内的请求数。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from src.utils.helpers import current_time_ms


@dataclass
class SlidingWindowRateLimiter:
    """最近 window_ms 内最多允许 max_events 次。"""

    max_events: int
    window_ms: int = 1000
    _events_ms: Deque[int] = field(default_factory=deque)

    def try_acquire(self, current_ms: Optional[int] = None) -> bool:
        """
        尝试占用一个配额。

        Returns:
            True 表示已占用配额；False 表示触发限速（未占用）。
        """
        if self.max_events <= 0:
            return True

        now_ms = current_ms if current_ms is not None else current_time_ms()
        cutoff = now_ms - self.window_ms

        while self._events_ms and self._events_ms[0] <= cutoff:
            self._events_ms.popleft()

        if len(self._events_ms) >= self.max_events:
            return False

        self._events_ms.append(now_ms)
        return True


# Input: MarketEvent, Position, config
# Output: ExitSignal
# Pos: signal evaluation engine
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
信号引擎模块

职责：
- 维护每个 symbol 的 MarketState（best_bid/ask, last/prev trade price）
- 评估 LONG/SHORT 平仓触发条件
- 实现触发节流（min_signal_interval_ms）
- 维护滑动窗口回报率（accel）并计算 accel_mult
- 计算 ROI 并匹配 roi_mult

输入：
- MarketEvent
- Position

输出：
- ExitSignal（满足条件时）
"""

from collections import deque
from decimal import Decimal
from typing import Deque, Dict, Optional, Tuple, List

from src.models import (
    MarketEvent,
    MarketState,
    Position,
    PositionSide,
    ExitSignal,
    SignalReason,
)
from src.utils.logger import get_logger, log_signal
from src.utils.helpers import current_time_ms


class SignalEngine:
    """信号引擎"""

    def __init__(self, min_signal_interval_ms: int = 200):
        """
        初始化信号引擎

        Args:
            min_signal_interval_ms: 同一侧仓位两次信号的最小间隔
        """
        self.min_signal_interval_ms = min_signal_interval_ms
        self._market_states: Dict[str, MarketState] = {}
        self._last_signal_ms: Dict[str, int] = {}  # key: symbol:position_side
        self._last_logged_signal: Dict[str, Tuple[SignalReason, Decimal, Decimal, Decimal]] = {}  # key: symbol:position_side

        # 追踪是否收到过 bid/ask 和 trade 数据
        self._has_book_data: Dict[str, bool] = {}
        self._has_trade_data: Dict[str, bool] = {}

        # per-symbol 参数（允许覆盖）
        self._symbol_min_signal_interval_ms: Dict[str, int] = {}
        self._symbol_accel_window_ms: Dict[str, int] = {}
        self._symbol_accel_tiers: Dict[str, List[Tuple[Decimal, int]]] = {}
        self._symbol_roi_tiers: Dict[str, List[Tuple[Decimal, int]]] = {}

        # trade 价格序列（用于 accel 滑动窗口）
        self._trade_history: Dict[str, Deque[Tuple[int, Decimal]]] = {}

    def configure_symbol(
        self,
        symbol: str,
        *,
        min_signal_interval_ms: Optional[int] = None,
        accel_window_ms: Optional[int] = None,
        accel_tiers: Optional[List[Tuple[Decimal, int]]] = None,
        roi_tiers: Optional[List[Tuple[Decimal, int]]] = None,
    ) -> None:
        """配置某个 symbol 的节流/倍数档位参数。"""
        if min_signal_interval_ms is not None:
            self._symbol_min_signal_interval_ms[symbol] = min_signal_interval_ms
        if accel_window_ms is not None:
            self._symbol_accel_window_ms[symbol] = accel_window_ms
        if accel_tiers is not None:
            self._symbol_accel_tiers[symbol] = sorted(accel_tiers, key=lambda x: x[0])
        if roi_tiers is not None:
            self._symbol_roi_tiers[symbol] = sorted(roi_tiers, key=lambda x: x[0])

        self._trade_history.setdefault(symbol, deque())

    def update_market(self, event: MarketEvent) -> None:
        """
        更新市场状态

        根据事件类型更新：
        - book_ticker: 更新 best_bid/best_ask
        - agg_trade: 更新 last_trade_price (previous <- last)

        Args:
            event: 市场数据事件
        """
        symbol = event.symbol
        state = self._market_states.get(symbol)

        if state is None:
            # 初始化 MarketState
            state = MarketState(
                symbol=symbol,
                best_bid=Decimal("0"),
                best_ask=Decimal("0"),
                last_trade_price=Decimal("0"),
                previous_trade_price=None,
                last_update_ms=0,
                is_ready=False,
            )
            self._market_states[symbol] = state
            self._has_book_data[symbol] = False
            self._has_trade_data[symbol] = False

        # 更新时间戳
        state.last_update_ms = event.timestamp_ms

        if event.event_type == "book_ticker":
            # 更新 best bid/ask
            if event.best_bid is not None:
                state.best_bid = event.best_bid
            if event.best_ask is not None:
                state.best_ask = event.best_ask
            self._has_book_data[symbol] = True

        elif event.event_type == "agg_trade":
            # 更新 trade price，保存上一次价格
            if event.last_trade_price is not None:
                # 维护 trade 历史（用于 accel 滑动窗口）
                history = self._trade_history.setdefault(symbol, deque())
                history.append((event.timestamp_ms, event.last_trade_price))

                # 只有当 last_trade_price 已有有效值时才保存到 previous
                if state.last_trade_price > Decimal("0"):
                    state.previous_trade_price = state.last_trade_price
                state.last_trade_price = event.last_trade_price
                self._has_trade_data[symbol] = True

        # 检查数据是否就绪
        # 就绪条件：有 bid/ask 数据 AND 有 trade 数据 AND 有 previous trade price
        state.is_ready = (
            self._has_book_data.get(symbol, False)
            and self._has_trade_data.get(symbol, False)
            and state.previous_trade_price is not None
            and state.best_bid > Decimal("0")
            and state.best_ask > Decimal("0")
            and state.last_trade_price > Decimal("0")
        )

    def evaluate(
        self,
        symbol: str,
        position_side: PositionSide,
        position: Position,
        current_ms: Optional[int] = None,
    ) -> Optional[ExitSignal]:
        """
        评估是否满足平仓条件

        Args:
            symbol: 交易对
            position_side: 仓位方向
            position: 当前仓位
            current_ms: 当前时间戳（可选，默认使用系统时间）

        Returns:
            ExitSignal（满足条件时）或 None
        """
        if current_ms is None:
            current_ms = current_time_ms()

        # 检查数据是否就绪
        state = self._market_states.get(symbol)
        if state is None or not state.is_ready:
            return None

        # 检查节流
        if self._is_throttled(symbol, position_side, current_ms):
            return None

        # 检查仓位是否有效（非零）
        if abs(position.position_amt) == Decimal("0"):
            return None

        # 根据仓位方向检查退出条件
        reason: Optional[SignalReason] = None

        if position_side == PositionSide.LONG:
            reason = self._check_long_exit(state)
        elif position_side == PositionSide.SHORT:
            reason = self._check_short_exit(state)

        if reason is None:
            return None

        ret_window = self._compute_accel_ret(symbol, current_ms, state.last_trade_price)
        accel_mult = self._select_accel_mult(symbol, position_side, ret_window)

        roi = self._compute_roi(position)
        roi_mult = self._select_roi_mult(symbol, roi)

        # 更新最后信号时间
        key = f"{symbol}:{position_side.value}"
        self._last_signal_ms[key] = current_ms

        # 创建 ExitSignal
        signal = ExitSignal(
            symbol=symbol,
            position_side=position_side,
            reason=reason,
            timestamp_ms=current_ms,
            best_bid=state.best_bid,
            best_ask=state.best_ask,
            last_trade_price=state.last_trade_price,
            roi_mult=roi_mult,
            accel_mult=accel_mult,
            roi=roi,
            ret_window=ret_window,
        )

        # 记录日志（避免完全相同的信号快照重复刷屏）
        signature = (reason, state.best_bid, state.best_ask, state.last_trade_price)
        if self._last_logged_signal.get(key) != signature:
            self._last_logged_signal[key] = signature
            log_signal(
                symbol=symbol,
                side=position_side.value,
                reason=reason.value,
                best_bid=state.best_bid,
                best_ask=state.best_ask,
                last_trade=state.last_trade_price,
                roi_mult=roi_mult,
                accel_mult=accel_mult,
                roi=roi,
                ret_window=ret_window,
            )

        return signal

    def _check_long_exit(self, state: MarketState) -> Optional[SignalReason]:
        """
        检查 LONG 平仓条件

        条件（设计文档 3.1）：
        - long_primary: last > prev AND best_bid >= last
        - long_bid_improve: (not primary) AND best_bid >= last AND best_bid > prev

        Args:
            state: 市场状态

        Returns:
            SignalReason 或 None
        """
        if state.previous_trade_price is None:
            return None

        last = state.last_trade_price
        prev = state.previous_trade_price
        best_bid = state.best_bid

        # Primary condition: 价格上涨 AND 买一支撑当前价
        long_primary = last > prev and best_bid >= last

        if long_primary:
            return SignalReason.LONG_PRIMARY

        # Bid improve condition: 买一支撑当前价 AND 买一比上一成交价高
        long_bid_improve = best_bid >= last and best_bid > prev

        if long_bid_improve:
            return SignalReason.LONG_BID_IMPROVE

        return None

    def _check_short_exit(self, state: MarketState) -> Optional[SignalReason]:
        """
        检查 SHORT 平仓条件

        条件（设计文档 3.2）：
        - short_primary: last < prev AND best_ask <= last
        - short_ask_improve: (not primary) AND best_ask <= last AND best_ask < prev

        Args:
            state: 市场状态

        Returns:
            SignalReason 或 None
        """
        if state.previous_trade_price is None:
            return None

        last = state.last_trade_price
        prev = state.previous_trade_price
        best_ask = state.best_ask

        # Primary condition: 价格下跌 AND 卖一压低到当前价
        short_primary = last < prev and best_ask <= last

        if short_primary:
            return SignalReason.SHORT_PRIMARY

        # Ask improve condition: 卖一压低到当前价 AND 卖一比上一成交价低
        short_ask_improve = best_ask <= last and best_ask < prev

        if short_ask_improve:
            return SignalReason.SHORT_ASK_IMPROVE

        return None

    def _is_throttled(self, symbol: str, position_side: PositionSide, current_ms: int) -> bool:
        """
        检查是否在节流期内

        Args:
            symbol: 交易对
            position_side: 仓位方向
            current_ms: 当前时间戳

        Returns:
            True 如果在节流期内
        """
        key = f"{symbol}:{position_side.value}"
        last_signal_ms = self._last_signal_ms.get(key, 0)

        if last_signal_ms == 0:
            return False

        elapsed = current_ms - last_signal_ms
        interval = self._symbol_min_signal_interval_ms.get(symbol, self.min_signal_interval_ms)
        return elapsed < interval

    def _compute_accel_ret(self, symbol: str, current_ms: int, last_price: Decimal) -> Optional[Decimal]:
        """计算滑动窗口回报率 ret = p_now/p_window_ago - 1（基于 last_trade_price）。"""
        if last_price <= Decimal("0"):
            return None

        history = self._trade_history.get(symbol)
        if not history or len(history) < 2:
            return None

        window_ms = self._symbol_accel_window_ms.get(symbol, 2000)
        cutoff = current_ms - window_ms

        # 移除窗口外数据（保留窗口内最早点作为 window_ago 近似）
        while history and history[0][0] < cutoff:
            history.popleft()

        if not history:
            return None

        window_price = history[0][1]
        if window_price <= Decimal("0"):
            return None

        return (last_price / window_price) - Decimal("1")

    def _select_accel_mult(
        self, symbol: str, position_side: PositionSide, ret_window: Optional[Decimal]
    ) -> int:
        """按档位选择 accel_mult（取满足条件的最高档）。LONG/SHORT 共用 tiers，方向自动处理。"""
        if ret_window is None:
            return 1

        tiers = self._symbol_accel_tiers.get(symbol, [])

        best_mult = 1
        for threshold, mult in tiers:
            candidate = max(int(mult), 1)
            if position_side == PositionSide.LONG:
                if ret_window >= threshold:
                    best_mult = max(best_mult, candidate)
            else:
                if ret_window <= -threshold:
                    best_mult = max(best_mult, candidate)
        return best_mult

    def _compute_roi(self, position: Position) -> Optional[Decimal]:
        """计算该侧仓位 ROI（以初始保证金为分母的比例值）。"""
        qty = abs(position.position_amt)
        if qty <= Decimal("0"):
            return None
        if position.entry_price <= Decimal("0"):
            return None

        leverage = position.leverage if position.leverage > 0 else 1
        notional = qty * position.entry_price
        initial_margin = notional / Decimal(leverage)
        if initial_margin <= Decimal("0"):
            return None

        return position.unrealized_pnl / initial_margin

    def _select_roi_mult(self, symbol: str, roi: Optional[Decimal]) -> int:
        """按档位选择 roi_mult（取满足条件的最高档）。"""
        if roi is None:
            return 1

        tiers = self._symbol_roi_tiers.get(symbol, [])
        best_mult = 1
        for threshold, mult in tiers:
            candidate = max(int(mult), 1)
            if roi >= threshold:
                best_mult = max(best_mult, candidate)
        return best_mult

    def get_market_state(self, symbol: str) -> Optional[MarketState]:
        """
        获取 symbol 的市场状态

        Args:
            symbol: 交易对

        Returns:
            MarketState 或 None
        """
        return self._market_states.get(symbol)

    def is_data_ready(self, symbol: str) -> bool:
        """
        检查是否有足够数据进行信号判断

        Args:
            symbol: 交易对

        Returns:
            True 如果数据就绪
        """
        state = self._market_states.get(symbol)
        return state is not None and state.is_ready

    def reset_throttle(self, symbol: str, position_side: PositionSide) -> None:
        """
        重置节流计时器

        Args:
            symbol: 交易对
            position_side: 仓位方向
        """
        key = f"{symbol}:{position_side.value}"
        if key in self._last_signal_ms:
            del self._last_signal_ms[key]
        if key in self._last_logged_signal:
            del self._last_logged_signal[key]

    def clear_state(self, symbol: str) -> None:
        """
        清除指定 symbol 的状态

        Args:
            symbol: 交易对
        """
        if symbol in self._market_states:
            del self._market_states[symbol]
        if symbol in self._has_book_data:
            del self._has_book_data[symbol]
        if symbol in self._has_trade_data:
            del self._has_trade_data[symbol]
        if symbol in self._trade_history:
            del self._trade_history[symbol]

        # 清除相关的节流记录
        keys_to_remove = [k for k in self._last_signal_ms if k.startswith(f"{symbol}:")]
        for key in keys_to_remove:
            del self._last_signal_ms[key]

        keys_to_remove = [k for k in self._last_logged_signal if k.startswith(f"{symbol}:")]
        for key in keys_to_remove:
            del self._last_logged_signal[key]

"""
保护性止损（ProtectiveStopManager）单元测试
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exchange.adapter import ExchangeAdapter
from src.models import (
    OrderIntent,
    OrderResult,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    SymbolRules,
)
from src.risk.protective_stop import ProtectiveStopManager


class TestProtectiveStopPrice:
    def test_compute_stop_price_rounding(self):
        exchange = MagicMock(spec=ExchangeAdapter)
        mgr = ProtectiveStopManager(exchange, client_order_id_prefix="vq-ps-")

        tick = Decimal("0.1")
        liq = Decimal("100")
        dist = Decimal("0.01")

        long_stop = mgr.compute_stop_price(
            position_side=PositionSide.LONG,
            liquidation_price=liq,
            dist_to_liq=dist,
            tick_size=tick,
        )
        # 100/0.99=101.0101..., LONG 采用向上规整
        assert long_stop == Decimal("101.1")

        short_stop = mgr.compute_stop_price(
            position_side=PositionSide.SHORT,
            liquidation_price=liq,
            dist_to_liq=dist,
            tick_size=tick,
        )
        # 100/1.01=99.0099..., SHORT 采用向下规整
        assert short_stop == Decimal("99.0")


@pytest.mark.asyncio
class TestProtectiveStopSync:
    async def test_sync_places_order_when_missing(self):
        exchange = MagicMock(spec=ExchangeAdapter)
        exchange.fetch_open_orders = AsyncMock(return_value=[])
        exchange.place_order = AsyncMock(
            return_value=OrderResult(success=True, order_id="1", status=OrderStatus.NEW)
        )
        exchange.cancel_order = AsyncMock(
            return_value=OrderResult(success=True, order_id="1", status=OrderStatus.CANCELED)
        )

        mgr = ProtectiveStopManager(exchange, client_order_id_prefix="vq-ps-")
        symbol = "BTC/USDT:USDT"
        rules = SymbolRules(
            symbol=symbol,
            tick_size=Decimal("0.1"),
            step_size=Decimal("0.001"),
            min_qty=Decimal("0.001"),
            min_notional=Decimal("5"),
        )
        positions = {
            PositionSide.LONG: Position(
                symbol=symbol,
                position_side=PositionSide.LONG,
                position_amt=Decimal("0.01"),
                entry_price=Decimal("100"),
                unrealized_pnl=Decimal("0"),
                leverage=10,
                liquidation_price=Decimal("100"),
                mark_price=Decimal("110"),
            )
        }

        await mgr.sync_symbol(
            symbol=symbol,
            rules=rules,
            positions=positions,
            enabled=True,
            dist_to_liq=Decimal("0.01"),
        )

        exchange.place_order.assert_called_once()
        intent: OrderIntent = exchange.place_order.call_args.args[0]
        assert intent.order_type == OrderType.STOP_MARKET
        assert intent.close_position is True
        assert intent.stop_price == Decimal("101.1")
        assert intent.is_risk is True

    async def test_sync_cancels_order_when_no_position(self):
        exchange = MagicMock(spec=ExchangeAdapter)
        symbol = "BTC/USDT:USDT"
        mgr = ProtectiveStopManager(exchange, client_order_id_prefix="vq-ps-")
        cid = mgr.build_client_order_id(symbol, PositionSide.LONG)

        exchange.fetch_open_orders = AsyncMock(
            return_value=[
                {
                    "id": "123",
                    "clientOrderId": cid,
                    "stopPrice": "101.1",
                    "info": {"positionSide": "LONG", "clientOrderId": cid, "stopPrice": "101.1"},
                }
            ]
        )
        exchange.cancel_order = AsyncMock(
            return_value=OrderResult(success=True, order_id="123", status=OrderStatus.CANCELED)
        )
        exchange.place_order = AsyncMock(
            return_value=OrderResult(success=True, order_id="1", status=OrderStatus.NEW)
        )

        rules = SymbolRules(
            symbol=symbol,
            tick_size=Decimal("0.1"),
            step_size=Decimal("0.001"),
            min_qty=Decimal("0.001"),
            min_notional=Decimal("5"),
        )

        await mgr.sync_symbol(
            symbol=symbol,
            rules=rules,
            positions={},  # 无仓位
            enabled=True,
            dist_to_liq=Decimal("0.01"),
        )

        exchange.cancel_order.assert_called_once_with(symbol, "123")
        exchange.place_order.assert_not_called()


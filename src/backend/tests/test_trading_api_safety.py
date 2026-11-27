"""Regression tests ensuring trading routes never invent state or fake success."""

import pytest
from fastapi import HTTPException

from src.backend.api.routes import trading


@pytest.mark.parametrize(
    "name",
    ["MOCK_POSITIONS", "MOCK_ORDERS", "MOCK_TRADES", "MOCK_TPSL_STAGES", "generate_mock_data"],
)
def test_mock_trading_fixtures_are_removed(name):
    assert not hasattr(trading, name)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        trading.get_paper_status(),
        trading.get_positions(),
        trading.get_position(123),
        trading.get_position_tp_sl(123),
        trading.get_orders(),
        trading.get_trade_history(),
        trading.get_pnl_summary(),
    ],
)
async def test_trading_reads_fail_closed_without_persisted_read_model(call):
    with pytest.raises(HTTPException) as exc:
        await call

    assert exc.value.status_code == 503
    assert "No simulated data is returned" in exc.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        trading.place_paper_trade(
            trading.PaperTradeRequest(
                symbol="BTCUSDT",
                exchange="binance",
                direction=trading.TradeDirection.LONG,
                stop_loss=90,
                tp1=110,
                tp2=120,
                tp3=130,
            )
        ),
        trading.close_position(
            123, trading.ClosePositionRequest(position_id=123)
        ),
        trading.cancel_order(123),
        trading.pause_paper_trading(),
        trading.resume_paper_trading(),
        trading.reset_paper_trading(),
    ],
)
async def test_trading_mutations_never_claim_success_without_execution_wiring(call):
    with pytest.raises(HTTPException) as exc:
        await call

    assert exc.value.status_code == 409
    assert "No order or state change occurred" in exc.value.detail

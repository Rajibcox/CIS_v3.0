"""Safety tests for the internal signal-to-paper-execution boundary."""

import asyncio

from src.backend.services.signal_service import SignalService


class _DatabaseMustNotBeUsed:
    def query(self, *_args, **_kwargs):
        raise AssertionError("Unavailable signal execution must not query or mutate the database")


def test_internal_signal_paper_execution_fails_closed_without_fake_position():
    service = SignalService.__new__(SignalService)

    result = asyncio.run(
        service.execute_paper_trade(_DatabaseMustNotBeUsed(), signal_id=123)
    )

    assert result == {
        "success": False,
        "error": "paper_execution_unavailable",
        "message": (
            "Paper execution from signals is disabled until qualified trade "
            "plans and the complete paper-execution persistence workflow are wired."
        ),
    }
    assert "position_id" not in result

"""Request-scoped database and application service dependencies.

This module never creates schemas or runs migrations.
"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session


def get_db(request: Request):
    """Yield one SQLAlchemy session per request."""
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Database session factory is unavailable")
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


def get_strategy_service(request: Request):
    """Resolve the strategy service owned by the application service container."""
    container = getattr(request.app.state, "services", None)
    service = getattr(container, "strategy_service", None) if container else None
    if service is None:
        raise HTTPException(status_code=503, detail="Strategy service is unavailable")
    return service

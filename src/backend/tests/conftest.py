"""
Pytest configuration for QUANTUM TRADER V1 tests
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def config():
    """Create test configuration"""
    from src.backend.utils.config import Config
    config = Config()
    config.settings.debug = True
    config.settings.mock_exchange = True
    config.settings.database_url = "sqlite:///:memory:"
    return config


@pytest.fixture
def db_session(config):
    """Create a test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.backend.models.database import Base

    engine = create_engine(config.settings.database_url, echo=False)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_exchange_credentials():
    """Mock exchange credentials for testing"""
    return {
        'binance': {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'testnet': True
        },
        'bitget': {
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'passphrase': 'test_passphrase',
            'testnet': True
        }
    }


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "exchange: mark test as requiring exchange connection"
    )
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.backend.models.database import Base, Exchange, Strategy, Configuration, TelegramUser


class DatabaseInitializer:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        print("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        print("Tables created successfully")

    def initialize_exchanges(self):
        print("Initializing exchanges...")
        session = self.SessionLocal()
        exchanges = [
            Exchange(name="Binance", base_url="https://fapi.binance.com", api_version="v1", is_active=True),
            Exchange(name="Bitget", base_url="https://api.bitget.com", api_version="v2", is_active=True),
        ]
        for exchange in exchanges:
            if not session.query(Exchange).filter_by(name=exchange.name).first():
                session.add(exchange)
                print(f"Added exchange: {exchange.name}")
        session.commit()
        session.close()

    def initialize_strategies(self):
        print("Initializing strategies...")
        session = self.SessionLocal()
        strategies = [
            Strategy(name="Trend Following", description="Long-only trend following strategy", version="1.0.0", is_active=True),
            Strategy(name="Mean Reversion", description="Short-term mean reversion strategy", version="1.0.0", is_active=True),
            Strategy(name="Breakout", description="Breakout and retest strategy", version="1.0.0", is_active=True),
            Strategy(name="Momentum Scalping", description="Short-term momentum strategy", version="1.0.0", is_active=True),
            Strategy(name="Volume Expansion", description="Volume expansion based strategy", version="1.0.0", is_active=True),
        ]
        for strategy in strategies:
            if not session.query(Strategy).filter_by(name=strategy.name).first():
                session.add(strategy)
                print(f"Added strategy: {strategy.name}")
        session.commit()
        session.close()

    def initialize_configurations(self):
        print("Initializing configurations...")
        session = self.SessionLocal()
        configs = [
            Configuration(config_key="trading.initial_equity", config_value={"value": 100.0, "currency": "USDT"}, description="Starting paper trading equity"),
            Configuration(config_key="trading.risk_per_trade", config_value={"value": 0.005, "percentage": 0.5}, description="Risk per trade as percentage of equity"),
            Configuration(config_key="trading.max_leverage", config_value={"value": 3, "max": 100}, description="Maximum leverage for new positions"),
            Configuration(config_key="trading.max_positions", config_value={"value": 2, "max": 10}, description="Maximum number of simultaneous positions"),
            Configuration(config_key="market.scan_interval", config_value={"value": 300, "seconds": 5}, description="Market scan interval in seconds"),
            Configuration(config_key="market.supported_timeframes", config_value={"value": ["3m", "5m", "15m", "1h", "4h", "1d"]}, description="Supported timeframe list"),
            Configuration(config_key="tp.sl.allocation", config_value={"tp1": 0.4, "tp2": 0.3, "tp3": 0.2, "runner": 0.1}, description="TP stage allocation percentages"),
            Configuration(config_key="telegram.enabled", config_value={"value": False}, description="Enable Telegram notifications"),
        ]
        for config in configs:
            if not session.query(Configuration).filter_by(config_key=config.config_key).first():
                session.add(config)
                print(f"Added config: {config.config_key}")
        session.commit()
        session.close()

    def initialize_telegram_admin(self, admin_user_id: int = None):
        print("Initializing Telegram admin...")
        session = self.SessionLocal()
        admin_user = TelegramUser(user_id=admin_user_id or 0, username="admin", is_admin=True, is_active=True)
        if not session.query(TelegramUser).filter_by(user_id=admin_user_id or 0).first():
            session.add(admin_user)
            session.commit()
            print(f"Added Telegram admin: {admin_user_id or 0}")
        else:
            print("Telegram admin already exists")
        session.close()

    def seed_data(self):
        self.initialize_exchanges()
        self.initialize_strategies()
        self.initialize_configurations()
        self.initialize_telegram_admin()

    def drop_all_tables(self):
        print("WARNING: This will delete all data!")
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() == "yes":
            Base.metadata.drop_all(bind=self.engine)
            print("All tables dropped")
        else:
            print("Operation cancelled")


def main():
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.backend.utils.config import Config
    config = Config()
    database_url = config.settings.database_url
    print("=" * 60)
    print("QUANTUM TRADER V1 - Database Initialization")
    print("=" * 60)
    print(f"Database URL: {database_url}")
    print(f"Project Root: {project_root}")
    print("=" * 60)
    initializer = DatabaseInitializer(database_url)
    initializer.create_tables()
    initializer.seed_data()
    print("=" * 60)
    print("Database initialization complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()

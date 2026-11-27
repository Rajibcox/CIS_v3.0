"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-11-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create exchanges table
    op.create_table(
        'exchanges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('base_url', sa.String(255), nullable=False),
        sa.Column('api_version', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create exchange_credentials table
    op.create_table(
        'exchange_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exchange_id', sa.Integer(), nullable=False),
        sa.Column('api_key', sa.String(255), nullable=False),
        sa.Column('api_secret', sa.String(255), nullable=False),
        sa.Column('passphrase', sa.String(255), nullable=True),
        sa.Column('permissions', sa.String(50), nullable=False, server_default='read'),
        sa.Column('ip_whitelist', sa.JSON(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['exchange_id'], ['exchanges.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create symbols table
    op.create_table(
        'symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exchange_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('base_asset', sa.String(20), nullable=False),
        sa.Column('quote_asset', sa.String(20), nullable=False),
        sa.Column('contract_size', sa.Float(), nullable=True),
        sa.Column('tick_size', sa.Float(), nullable=True),
        sa.Column('lot_size', sa.Float(), nullable=True),
        sa.Column('min_notional', sa.Float(), nullable=True),
        sa.Column('max_leverage', sa.Integer(), nullable=True),
        sa.Column('maintenance_margin_rate', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_eligible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['exchange_id'], ['exchanges.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exchange_id', 'symbol', name='uq_exchange_symbol')
    )

    # Create market_candles table
    op.create_table(
        'market_candles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol_id', sa.Integer(), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('open_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('quote_volume', sa.Float(), nullable=True),
        sa.Column('trades', sa.Integer(), nullable=True),
        sa.Column('is_closed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['symbol_id'], ['symbols.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol_id', 'timeframe', 'open_time', name='uq_symbol_timeframe_open_time')
    )
    op.create_index('ix_market_candles_symbol_timeframe_time', 'market_candles', ['symbol_id', 'timeframe', 'open_time'])
    op.create_index('ix_market_candles_closed', 'market_candles', ['is_closed'])

    # Create strategies table
    op.create_table(
        'strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('direction', sa.String(10), nullable=False, server_default='both'),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('risk_multiplier', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('timeframes', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('symbols', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('min_signal_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create strategy_rules table
    op.create_table(
        'strategy_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('rule_config', sa.JSON(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol_id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('signal_score', sa.Float(), nullable=True),
        sa.Column('market_regime', sa.String(50), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('tp1', sa.Float(), nullable=True),
        sa.Column('tp2', sa.Float(), nullable=True),
        sa.Column('tp3', sa.Float(), nullable=True),
        sa.Column('runner_quantity', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='candidate'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('invalidation_reason', sa.Text(), nullable=True),
        sa.Column('supporting_evidence', sa.JSON(), nullable=True),
        sa.Column('risk_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['symbol_id'], ['symbols.id']),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("direction IN ('LONG', 'SHORT')", name='ck_signal_direction')
    )

    # Persist every signal lifecycle transition independently of in-memory handlers.
    op.create_table(
        'signal_lifecycle_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(20), nullable=True),
        sa.Column('to_status', sa.String(20), nullable=False),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signal_lifecycle_events_signal_id', 'signal_lifecycle_events', ['signal_id'])

    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.Column('exchange_id', sa.Integer(), nullable=False),
        sa.Column('symbol_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('notional_value', sa.Float(), nullable=True),
        sa.Column('margin_used', sa.Float(), nullable=True),
        sa.Column('leverage_used', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('pnl', sa.Float(), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Float(), nullable=False, server_default='0'),
        sa.Column('open_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id']),
        sa.ForeignKeyConstraint(['exchange_id'], ['exchanges.id']),
        sa.ForeignKeyConstraint(['symbol_id'], ['symbols.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("direction IN ('LONG', 'SHORT')", name='ck_position_direction'),
        sa.CheckConstraint("status IN ('open', 'closed', 'liquidated', 'force_closed')", name='ck_position_status')
    )

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.Column('exchange_id', sa.Integer(), nullable=False),
        sa.Column('symbol_id', sa.Integer(), nullable=False),
        sa.Column('exchange_order_id', sa.String(100), nullable=True),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('stop_price', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('filled_quantity', sa.Float(), nullable=False, server_default='0'),
        sa.Column('average_fill_price', sa.Float(), nullable=True),
        sa.Column('fees', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.ForeignKeyConstraint(['exchange_id'], ['exchanges.id']),
        sa.ForeignKeyConstraint(['symbol_id'], ['symbols.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name='ck_order_side'),
        sa.CheckConstraint("order_type IN ('market', 'limit', 'stop_market', 'stop_limit')", name='ck_order_type'),
        sa.CheckConstraint("status IN ('pending', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired')", name='ck_order_status')
    )

    # Create tp_sl_stages table
    op.create_table(
        'tp_sl_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('stage_type', sa.String(10), nullable=False),
        sa.Column('stage_number', sa.Integer(), nullable=False),
        sa.Column('target_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exchange_order_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("stage_type IN ('TP', 'SL')", name='ck_stage_type'),
        sa.CheckConstraint("status IN ('pending', 'triggered', 'filled', 'cancelled', 'failed')", name='ck_stage_status')
    )

    # Create pnl_entries table
    op.create_table(
        'pnl_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=True),
        sa.Column('pnl_type', sa.String(20), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('running_balance', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("pnl_type IN ('realized', 'unrealized', 'fee', 'funding')", name='ck_pnl_type')
    )

    # Create configurations table
    op.create_table(
        'configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(100), nullable=False),
        sa.Column('config_value', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_user_time', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_created', 'audit_logs', ['created_at'])

    # Create system_events table
    op.create_table(
        'system_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')", name='ck_severity')
    )
    op.create_index('ix_system_events_type_severity', 'system_events', ['event_type', 'severity'])
    op.create_index('ix_system_events_resolved', 'system_events', ['is_resolved'])
    op.create_index('ix_system_events_created', 'system_events', ['created_at'])

    # Create telegram_users table
    op.create_table(
        'telegram_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Insert default data
    op.execute("""
        INSERT INTO exchanges (name, base_url, api_version, is_active) VALUES
        ('Binance', 'https://fapi.binance.com', 'v1', true),
        ('Bitget', 'https://api.bitget.com', 'v2', true)
        ON CONFLICT (name) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO strategies (name, description, version, is_active) VALUES
        ('Trend Following', 'Long-only trend following strategy', '1.0.0', true),
        ('Mean Reversion', 'Short-term mean reversion strategy', '1.0.0', true),
        ('Breakout', 'Breakout and retest strategy', '1.0.0', true),
        ('Momentum Scalping', 'Short-term momentum strategy', '1.0.0', true),
        ('Volume Expansion', 'Volume expansion based strategy', '1.0.0', true)
        ON CONFLICT (name) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO configurations (config_key, config_value, description) VALUES
        ('trading.initial_equity', '{"value": 100.0, "currency": "USDT"}', 'Starting paper trading equity'),
        ('trading.risk_per_trade', '{"value": 0.005, "percentage": 0.5}', 'Risk per trade as percentage of equity'),
        ('trading.max_leverage', '{"value": 3, "max": 100}', 'Maximum leverage for new positions'),
        ('trading.max_positions', '{"value": 2, "max": 10}', 'Maximum number of simultaneous positions'),
        ('market.scan_interval', '{"value": 300, "seconds": 5}', 'Market scan interval in seconds'),
        ('market.supported_timeframes', '{"value": ["3m", "5m", "15m", "1h", "4h", "1d"]}', 'Supported timeframe list'),
        ('tp.sl.allocation', '{"tp1": 0.4, "tp2": 0.3, "tp3": 0.2, "runner": 0.1}', 'TP stage allocation percentages'),
        ('telegram.enabled', '{"value": false}', 'Enable Telegram notifications')
        ON CONFLICT (config_key) DO NOTHING;
    """)


def downgrade():
    op.drop_table('telegram_users')
    op.drop_table('system_events')
    op.drop_table('audit_logs')
    op.drop_table('configurations')
    op.drop_table('pnl_entries')
    op.drop_table('tp_sl_stages')
    op.drop_table('orders')
    op.drop_table('positions')
    op.drop_table('signal_lifecycle_events')
    op.drop_table('signals')
    op.drop_table('strategy_rules')
    op.drop_table('strategies')
    op.drop_table('market_candles')
    op.drop_table('symbols')
    op.drop_table('exchange_credentials')
    op.drop_table('exchanges')
/**
 * Type definitions matching the backend API models
 * These mirror the Pydantic models in the backend
 */

// ============================================================================
// Enums
// ============================================================================

export type SignalDirection = 'LONG' | 'SHORT';
export type SignalStatus = 'candidate' | 'qualified' | 'active' | 'triggered' | 'expired' | 'invalidated' | 'rejected' | 'executed';
export type MarketRegime = 'trending' | 'ranging' | 'volatile' | 'low_volatility' | 'breakout' | 'reversal' | 'sideways';
export type PositionStatus = 'open' | 'closed' | 'liquidated' | 'force_closed';
export type OrderStatus = 'pending' | 'partially_filled' | 'filled' | 'cancelled' | 'rejected' | 'expired';
export type OrderType = 'market' | 'limit' | 'stop_market' | 'stop_limit';
export type OrderSide = 'BUY' | 'SELL';
export type TPStageType = 'TP' | 'SL';
export type ExecutionMode = 'paper' | 'live';
export type LiveTradingState = 'paper' | 'live_eligible' | 'live_armed' | 'live_active' | 'live_paused' | 'emergency_stop';
export type HealthStatus = 'healthy' | 'degraded' | 'critical';
export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
export type ExchangeName = 'binance' | 'bitget';
export type MarginMode = 'isolated' | 'cross';
export type PositionMode = 'one_way' | 'hedge';
export type Theme = 'light' | 'dark' | 'system';

// ============================================================================
// Base Models
// ============================================================================

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// ============================================================================
// Overview / Dashboard
// ============================================================================

export interface PositionSummary {
  symbol: string;
  exchange: string;
  direction: SignalDirection;
  entry_price: number;
  current_price: number;
  quantity: number;
  unrealized_pnl: number;
  leverage: number;
  margin_used: number;
}

export interface SystemServiceStatus {
  market_data: string;
  strategy_engine: string;
  risk_engine: string;
  execution_engine: string;
  tp_sl_manager: string;
  pnl_analytics: string;
  telegram_bot: string;
}

export interface ExchangeConnectionStatus {
  binance: string;
  bitget: string;
}

export interface SystemStatus {
  status: HealthStatus;
  uptime_seconds: number;
  services: SystemServiceStatus;
  exchange_connections: ExchangeConnectionStatus;
  last_market_data_update: string;
}

export interface DashboardOverview {
  total_equity: number;
  available_balance: number;
  allocated_margin: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  total_unrealized_pnl: number;
  total_realized_pnl: number;
  drawdown_pct: number;
  peak_equity: number;
  open_positions_count: number;
  max_positions: number;
  positions: PositionSummary[];
  risk_per_trade_pct: number;
  daily_loss_limit_pct: number;
  max_leverage: number;
  current_max_leverage_used: number;
  system_status: SystemStatus;
  trading_mode: LiveTradingState;
  win_rate_30d: number;
  profit_factor_30d: number;
  expectancy_30d: number;
  sharpe_30d: number | null;
  max_drawdown_30d: number;
  timestamp: string;
}

export interface EquityCurvePoint {
  date: string;
  equity: number;
  drawdown: number;
}

// ============================================================================
// Market Intelligence
// ============================================================================

export interface MarketOverview {
  btc_dominance: number;
  fear_greed_index: number;
  fear_greed_label: string;
  total_volume_24h: number;
  total_open_interest: number;
  funding_rate_avg: number;
  top_gainer: { symbol: string; change_pct: number; price: number };
  top_loser: { symbol: string; change_pct: number; price: number };
  top_volume: { symbol: string; volume: number };
  liquidations_24h: { long: number; short: number };
  timestamp: string;
}

export interface SymbolSnapshot {
  symbol: string;
  exchange: string;
  price: number;
  change_24h_pct: number;
  volume_24h: number;
  volume_change_24h_pct: number;
  open_interest: number;
  oi_change_24h_pct: number;
  funding_rate: number;
  next_funding_time: string;
  spread_bps: number;
  spread_pct: number;
  atr: number;
  atr_pct: number;
  volatility_24h: number;
  regime: MarketRegime;
  btc_correlation: number;
  timestamp: string;
}

export interface ScannerResult {
  symbol: string;
  exchange: string;
  direction: SignalDirection;
  strategy: string;
  timeframe: string;
  signal_score: number;
  regime: MarketRegime;
  entry_price: number;
  stop_loss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  risk_reward: number;
  suggested_leverage: number;
  position_quantity: number;
  notional: number;
  required_margin: number;
  htf_alignment: boolean;
  btc_alignment: boolean;
  expires_at: string;
  created_at: string;
}

export interface OpportunityResponse {
  opportunities: ScannerResult[];
  total_scanned: number;
  scan_duration_ms: number;
  timestamp: string;
}

// ============================================================================
// Signals
// ============================================================================

export interface SignalBase {
  symbol: string;
  exchange: string;
  direction: SignalDirection;
  strategy: string;
  timeframe: string;
  signal_score: number;
  regime: MarketRegime;
  entry_price: number;
  stop_loss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  runner_quantity: number;
  risk_reward: number;
  suggested_leverage: number;
  position_quantity: number;
  notional: number;
  required_margin: number;
  estimated_fees: number;
  estimated_funding: number;
  net_pnl_tp1: number;
  net_pnl_tp2: number;
  net_pnl_tp3: number;
  net_pnl_runner: number;
  htf_alignment: boolean;
  btc_alignment: boolean;
  supporting_evidence: string[];
  invalidating_conditions: string[];
}

export interface SignalResponse extends SignalBase {
  id: number;
  status: SignalStatus;
  created_at: string;
  updated_at: string;
  expires_at: string;
  triggered_at: string | null;
  executed_at: string | null;
  rejection_reason: string | null;
}

export interface SignalDetail extends SignalResponse {
  entry_zone_low: number;
  entry_zone_high: number;
  market_structure: {
    trend: string;
    structure: string;
    key_level: number;
    invalidation_level: number;
  };
  indicator_values: Record<string, number>;
  higher_timeframe_context: Record<string, any>;
  risk_calculation: Record<string, any>;
  leverage_decision: Record<string, any>;
}

export interface SignalStats {
  total_signals: number;
  by_status: Record<string, number>;
  by_direction: Record<string, number>;
  by_strategy: Record<string, number>;
  avg_score: number;
  execution_rate: number;
  avg_risk_reward: number;
  tp1_hit_rate: number;
  tp2_hit_rate: number;
  tp3_hit_rate: number;
  runner_profit_pct: number;
}

// ============================================================================
// Strategies
// ============================================================================

export type RuleType = 'indicator_vs_value' | 'indicator_vs_indicator' | 'price_action' | 'volume' | 'trend' | 'regime' | 'time_based';
export type ComparisonOperator = '>' | '<' | '>=' | '<=' | '==' | 'crosses_above' | 'crosses_below';
export type LogicalOperator = 'AND' | 'OR';

export interface IndicatorConfig {
  name: string;
  params: Record<string, any>;
  source: string;
}

export interface RuleCondition {
  indicator?: IndicatorConfig;
  operator?: ComparisonOperator;
  threshold?: number;
  indicator_a?: IndicatorConfig;
  indicator_b?: IndicatorConfig;
  price_relation?: string;
  volume_condition?: string;
  volume_multiplier?: number;
  trend_condition?: string;
  adx_threshold?: number;
  regime?: string;
  session?: string;
  time_range?: string;
}

export interface RuleGroup {
  operator: LogicalOperator;
  conditions: RuleCondition[];
  groups: RuleGroup[];
}

export interface StrategyRuleSet {
  entry_rules: RuleGroup;
  exit_rules: RuleGroup;
  long_rules?: RuleGroup;
  short_rules?: RuleGroup;
}

export interface StrategyBase {
  name: string;
  description?: string;
  version: string;
  is_active: boolean;
  direction: 'LONG' | 'SHORT' | 'BOTH';
  weight: number;
  risk_multiplier: number;
  timeframes: string[];
  symbols: string[];
  min_signal_score: number;
}

export interface StrategyCreate extends StrategyBase {
  rule_set: StrategyRuleSet;
}

export interface StrategyUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  weight?: number;
  risk_multiplier?: number;
  timeframes?: string[];
  symbols?: string[];
  min_signal_score?: number;
  rule_set?: StrategyRuleSet;
}

export interface StrategyResponse extends StrategyBase {
  id: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
  signal_count_24h: number;
  win_rate_30d: number;
  profit_factor_30d: number;
  expectancy_30d: number;
}

export interface StrategyPerformance {
  strategy_id: number;
  strategy_name: string;
  version: string;
  period_days: number;
  total_signals: number;
  executed_signals: number;
  win_rate: number;
  loss_rate: number;
  profit_factor: number;
  expectancy: number;
  avg_win: number;
  avg_loss: number;
  avg_r_multiple: number;
  max_drawdown: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  by_symbol: Record<string, Record<string, number>>;
  by_timeframe: Record<string, Record<string, number>>;
  by_direction: Record<string, Record<string, number>>;
  by_regime: Record<string, Record<string, number>>;
  equity_curve: EquityCurvePoint[];
}

export interface StrategyVersion {
  version: string;
  description: string;
  created_at: string;
  performance?: StrategyPerformance;
  is_current: boolean;
}

export interface IndicatorInfo {
  name: string;
  display_name: string;
  category: 'trend' | 'momentum' | 'volatility' | 'volume' | 'other';
  description: string;
  default_params: Record<string, any>;
  param_schema: Record<string, any>;
  supports_timeframes: string[];
  repainting_risk: 'none' | 'low' | 'medium' | 'high';
  lookahead_risk: boolean;
}

// ============================================================================
// Trading / Positions
// ============================================================================

export interface Position {
  id: number;
  signal_id?: number;
  exchange: string;
  symbol: string;
  direction: SignalDirection;
  entry_price: number;
  current_price: number;
  quantity: number;
  notional_value: number;
  margin_used: number;
  leverage: number;
  unrealized_pnl: number;
  realized_pnl: number;
  status: PositionStatus;
  tp_stage: number;
  open_time: string;
  tp1_price?: number;
  tp2_price?: number;
  tp3_price?: number;
  stop_loss: number;
  liquidation_price?: number;
  liquidation_buffer_pct?: number;
  runner_trailing_price?: number;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: number;
  position_id?: number;
  exchange: string;
  symbol: string;
  exchange_order_id?: string;
  order_type: OrderType;
  side: OrderSide;
  quantity: number;
  price?: number;
  stop_price?: number;
  status: OrderStatus;
  filled_quantity: number;
  average_fill_price?: number;
  fees: number;
  reduce_only: boolean;
  created_at: string;
  updated_at: string;
  filled_at?: string;
}

export interface TPStage {
  id: number;
  position_id: number;
  stage_type: TPStageType;
  stage_number: number;
  target_price: number;
  quantity: number;
  status: string;
  exchange_order_id?: string;
  triggered_at?: string;
  filled_at?: string;
  created_at: string;
}

export interface PaperTradeRequest {
  signal_id?: number;
  symbol: string;
  exchange: string;
  direction: SignalDirection;
  entry_price?: number;
  quantity?: number;
  leverage?: number;
  stop_loss: number;
  tp1: number;
  tp2: number;
  tp3: number;
  runner_pct?: number;
  execution_mode: ExecutionMode;
}

export interface PaperTradeResponse {
  success: boolean;
  message: string;
  position_id?: number;
  order_id?: number;
  entry_price?: number;
  quantity?: number;
  leverage?: number;
  required_margin?: number;
  tp_sl_stages: TPStage[];
}

export interface TradeHistoryEntry {
  id: number;
  position_id: number;
  symbol: string;
  exchange: string;
  direction: SignalDirection;
  entry_price: number;
  exit_price: number;
  quantity: number;
  gross_pnl: number;
  fees: number;
  funding: number;
  net_pnl: number;
  r_multiple: number;
  hold_time_hours: number;
  exit_reason: string;
  tp_stage_reached: number;
  opened_at: string;
  closed_at: string;
}

export interface PaperAccountStatus {
  mode: ExecutionMode;
  equity: number;
  available_balance: number;
  allocated_margin: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  open_positions: number;
  max_positions: number;
  daily_loss_limit: number;
  daily_loss_used_pct: number;
  is_paused: boolean;
  last_reset: string;
}

// ============================================================================
// Configuration
// ============================================================================

export interface ExchangeConfig {
  name: ExchangeName;
  enabled: boolean;
  testnet: boolean;
  margin_mode: MarginMode;
  position_mode: PositionMode;
  rate_limit_buffer: number;
  recv_window: number;
}

export interface ExchangeConfigResponse {
  name: ExchangeName;
  enabled: boolean;
  testnet: boolean;
  margin_mode: MarginMode;
  position_mode: PositionMode;
  has_credentials: boolean;
  last_tested?: string;
  connection_status: string;
}

export interface MarketConfig {
  enabled_exchanges: ExchangeName[];
  quote_asset: string;
  contract_type: string;
  min_volume_24h: number;
  max_spread_bps: number;
  min_history_days: number;
  supported_timeframes: string[];
  primary_timeframe: string;
  context_timeframes: string[];
}

export interface ScannerConfig {
  scan_interval_seconds: number;
  max_candidates: number;
  min_signal_score: number;
  volume_filter: boolean;
  spread_filter: boolean;
  volatility_filter: boolean;
  regime_filter: boolean;
  btc_correlation_filter: boolean;
  min_btc_correlation: number;
  max_btc_correlation: number;
}

export interface RiskConfig {
  initial_equity: number;
  risk_per_trade_pct: number;
  max_simultaneous_positions: number;
  max_leverage: number;
  daily_loss_limit_pct: number;
  drawdown_warning_pct: number;
  emergency_drawdown_pct: number;
  max_correlated_exposure_pct: number;
  min_risk_reward: number;
  min_stop_distance_pct: number;
}

export interface TP_SL_Config {
  tp_allocation: {
    tp1: number;
    tp2: number;
    tp3: number;
    runner: number;
  };
  trailing_atr_multiplier: number;
  min_trailing_distance_pct: number;
  break_even_fee_aware: boolean;
  break_even_funding_aware: boolean;
  runner_trailing_type: string;
  runner_min_profit_pct: number;
}

export interface LeverageConfig {
  max_leverage: number;
  risk_first_sizing: boolean;
  liquidation_buffer_pct: number;
  use_exchange_maintenance_margin: boolean;
  leverage_tiers_respected: boolean;
}

export interface PaperTradingConfig {
  enabled: boolean;
  fees_bps: number;
  slippage_bps: number;
  funding_rate_pct: number;
  partial_fill_probability: number;
  latency_ms: number;
}

export interface TelegramConfig {
  enabled: boolean;
  bot_token?: string;
  allowed_users: number[];
  admin_users: number[];
  notifications: Record<string, boolean>;
  command_categories: Record<string, boolean>;
}

export interface NotificationConfig {
  telegram_enabled: boolean;
  email_enabled: boolean;
  email_address?: string;
  webhook_enabled: boolean;
  webhook_url?: string;
  webhook_events: string[];
}

export interface UIConfig {
  theme: Theme;
  auto_refresh_seconds: number;
  chart_timezone: string;
  decimal_places: number;
  show_advanced: boolean;
  compact_mode: boolean;
  sound_enabled: boolean;
}

export interface BackupConfig {
  enabled: boolean;
  interval_hours: number;
  retention_count: number;
  encrypt_backups: boolean;
  backup_path: string;
}

export interface FullConfig {
  exchanges: Record<string, ExchangeConfig>;
  market: MarketConfig;
  scanner: ScannerConfig;
  risk: RiskConfig;
  tp_sl: TP_SL_Config;
  leverage: LeverageConfig;
  paper_trading: PaperTradingConfig;
  telegram: TelegramConfig;
  notifications: NotificationConfig;
  ui: UIConfig;
  backup: BackupConfig;
}

// ============================================================================
// Analytics
// ============================================================================

export interface PnLSummary {
  period_days: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  gross_pnl: number;
  total_fees: number;
  total_funding: number;
  net_pnl: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  avg_r_multiple: number;
  max_drawdown: number;
  best_trade: number;
  worst_trade: number;
  avg_hold_time_hours: number;
  by_exit_reason: Record<string, number>;
  by_tp_stage: Record<string, number>;
}

export interface PerformanceMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  volatility_pct: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  calmar_ratio?: number;
  max_drawdown_pct: number;
  avg_drawdown_pct: number;
  max_drawdown_duration_days: number;
  current_drawdown_pct: number;
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  avg_win: number;
  avg_loss: number;
  avg_r_multiple: number;
  largest_win: number;
  largest_loss: number;
  consecutive_wins: number;
  consecutive_losses: number;
  risk_adjusted_return: number;
  ulcer_index: number;
  sterling_ratio: number;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  return_pct: number;
  trades: number;
  win_rate: number;
}

export interface BreakdownItem {
  category: string;
  trades: number;
  win_rate: number;
  profit_factor: number;
  net_pnl: number;
  avg_r_multiple: number;
}

export interface TradeDistribution {
  r_multiples: number[];
  hold_times_hours: number[];
  mae_pct: number[];
  mfe_pct: number[];
}

export interface TPAnalytics {
  tp1_hit_rate: number;
  tp2_hit_rate: number;
  tp3_hit_rate: number;
  runner_hit_rate: number;
  profit_captured_tp1_pct: number;
  profit_captured_tp2_pct: number;
  profit_captured_tp3_pct: number;
  profit_given_back_after_tp3_pct: number;
  stop_out_after_tp1_rate: number;
  stop_out_after_tp2_rate: number;
  stop_out_after_tp3_rate: number;
  avg_r_multiple_by_stage: Record<string, number>;
}

export interface BacktestResult {
  backtest_id: string;
  strategy_id: number;
  strategy_name: string;
  status: string;
  period: { start: string; end: string };
  symbols: string[];
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  metrics: PerformanceMetrics;
  equity_curve: EquityCurvePoint[];
  monthly_returns: MonthlyReturn[];
  trade_list: any[];
  created_at: string;
  completed_at?: string;
}

export interface WalkForwardResult {
  strategy_id: number;
  strategy_name: string;
  windows: any[];
  is_oos_correlation: number;
  stability_score: number;
  avg_oos_return: number;
  avg_oos_sharpe: number;
  worst_oos_drawdown: number;
}

export interface MonteCarloResult {
  strategy_id: number;
  strategy_name: string;
  simulations: number;
  confidence_intervals: Record<string, Record<string, number>>;
  ruin_probability: number;
  median_max_drawdown: number;
  median_final_equity: number;
  percentile_5_final_equity: number;
  percentile_95_final_equity: number;
  distribution_data: number[];
}

// ============================================================================
// System
// ============================================================================

export interface ServiceHealth {
  name: string;
  status: HealthStatus;
  last_check: string;
  details: Record<string, any>;
}

export interface SystemHealth {
  overall_status: HealthStatus;
  uptime_seconds: number;
  version: string;
  services: ServiceHealth[];
  database: Record<string, any>;
  disk_usage: Record<string, any>;
  memory_usage: Record<string, any>;
  exchange_connections: Record<string, string>;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  logger: string;
  message: string;
  service?: string;
  component?: string;
  exchange?: string;
}

export interface LogsResponse {
  logs: LogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface TelegramBotStatus {
  enabled: boolean;
  connected: boolean;
  bot_username?: string;
  bot_id?: number;
  allowed_users: number;
  admin_users: number;
  pending_commands: number;
  last_message_at?: string;
}

export interface TelegramCommandLog {
  id: number;
  user_id: number;
  username?: string;
  command: string;
  args: string;
  success: boolean;
  response_time_ms: number;
  timestamp: string;
}

export interface LiveTradingAction {
  action: 'check_eligibility' | 'arm' | 'confirm' | 'disarm' | 'emergency_stop';
  confirmation?: string;
}

export interface LiveTradingStatus {
  state: LiveTradingState;
  eligibility_checks: Record<string, boolean>;
  live_credentials_configured: boolean;
  paper_trades_count: number;
  paper_days_active: number;
  paper_net_expectancy: number;
  paper_profit_factor: number;
  paper_max_drawdown: number;
  critical_issues: string[];
  armed_at?: string;
  activated_at?: string;
}

export interface StorageInfo {
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  usage_pct: number;
  database_size_bytes: number;
  logs_size_bytes: number;
  backups_size_bytes: number;
  market_data_size_bytes: number;
}

export interface BackupInfo {
  filename: string;
  size_bytes: number;
  created_at: string;
  type: 'auto' | 'manual';
  description?: string;
}

export interface AuditLogEntry {
  id: number;
  user_id?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  ip_address?: string;
  success: boolean;
  error_message?: string;
  timestamp: string;
}

export interface SystemEvent {
  id: number;
  event_type: string;
  severity: string;
  message: string;
  details?: Record<string, any>;
  is_resolved: boolean;
  created_at: string;
}
/**
 * API Service Layer for QUANTUM TRADER V1 Frontend
 * Centralized HTTP client with request/response interceptors
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  DashboardOverview, EquityCurvePoint,
  MarketOverview, SymbolSnapshot, OpportunityResponse,
  SignalResponse, SignalDetail, SignalStats,
  StrategyResponse, StrategyCreate, StrategyUpdate, StrategyPerformance, StrategyVersion, IndicatorInfo,
  Position, Order, OrderType, TPStage, PaperTradeRequest, PaperTradeResponse, TradeHistoryEntry, PaperAccountStatus,
  FullConfig, ExchangeConfig, ExchangeConfigResponse,
  PnLSummary, PerformanceMetrics, MonthlyReturn, BreakdownItem, TPAnalytics, TradeDistribution,
  BacktestResult, WalkForwardResult, MonteCarloResult,
  SystemHealth, LogEntry, LogsResponse,
  TelegramBotStatus, TelegramCommandLog,
  LiveTradingStatus, LiveTradingAction,
  StorageInfo, BackupInfo, AuditLogEntry, SystemEvent
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('auth_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('auth_token');
          // Redirect to login if not already there
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic request methods
  async get<T>(url: string, params?: any): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }

  // ============================================================================
  // Overview / Dashboard
  // ============================================================================

  async getOverview(): Promise<DashboardOverview> {
    return this.get<DashboardOverview>('/overview');
  }

  async getEquityCurve(days: number = 30): Promise<{ data: EquityCurvePoint[] }> {
    return this.get('/overview/equity-curve', { days });
  }

  async getOpenPositions(): Promise<Position[]> {
    return this.get<Position[]>('/overview/positions');
  }

  async getQuickStats(): Promise<any> {
    return this.get('/overview/quick-stats');
  }

  // ============================================================================
  // Market Intelligence
  // ============================================================================

  async getMarketOverview(): Promise<MarketOverview> {
    return this.get<MarketOverview>('/market/overview');
  }

  async getSymbolSnapshot(symbol: string, exchange: string = 'binance'): Promise<SymbolSnapshot> {
    return this.get<SymbolSnapshot>(`/market/symbol/${symbol}`, { exchange });
  }

  async scanMarkets(params?: {
    exchanges?: string[];
    timeframes?: string[];
    min_score?: number;
    max_results?: number;
  }): Promise<OpportunityResponse> {
    return this.get<OpportunityResponse>('/market/scanner/scan', params);
  }

  async getLongOpportunities(minScore?: number, maxResults?: number): Promise<OpportunityResponse> {
    return this.get<OpportunityResponse>('/market/opportunities/long', { min_score: minScore, max_results: maxResults });
  }

  async getShortOpportunities(minScore?: number, maxResults?: number): Promise<OpportunityResponse> {
    return this.get<OpportunityResponse>('/market/opportunities/short', { min_score: minScore, max_results: maxResults });
  }

  async getMarketRegime(): Promise<any> {
    return this.get('/market/regime');
  }

  async getFundingRates(): Promise<any> {
    return this.get('/market/funding');
  }

  async getOpenInterest(): Promise<any> {
    return this.get('/market/open-interest');
  }

  async getLiquidations(): Promise<any> {
    return this.get('/market/liquidations');
  }

  // ============================================================================
  // Signals
  // ============================================================================

  async getSignals(params?: {
    status?: string;
    direction?: string;
    strategy?: string;
    symbol?: string;
    exchange?: string;
    start_date?: string;
    end_date?: string;
    min_score?: number;
    page?: number;
    page_size?: number;
  }): Promise<any> {
    return this.get('/signals', params);
  }

  async getActiveSignals(): Promise<SignalResponse[]> {
    return this.get<SignalResponse[]>('/signals/active');
  }

  async getBestSignals(limit: number = 10): Promise<SignalResponse[]> {
    return this.get<SignalResponse[]>('/signals/best', { limit });
  }

  async getSignalDetail(signalId: number): Promise<SignalDetail> {
    return this.get<SignalDetail>(`/signals/${signalId}`);
  }

  async getSignalStats(days: number = 30): Promise<SignalStats> {
    return this.get<SignalStats>('/signals/stats/summary', { days });
  }

  async executePaperTrade(signalId: number): Promise<any> {
    return this.post(`/signals/${signalId}/paper-trade`);
  }

  async triggerScan(): Promise<any> {
    return this.post('/signals/scan-now');
  }

  // ============================================================================
  // Strategies
  // ============================================================================

  async getStrategies(activeOnly?: boolean, includePerformance?: boolean): Promise<StrategyResponse[]> {
    return this.get<StrategyResponse[]>('/strategies', { active_only: activeOnly, include_performance: includePerformance });
  }

  async getStrategy(strategyId: number): Promise<StrategyResponse> {
    return this.get<StrategyResponse>(`/strategies/${strategyId}`);
  }

  async createStrategy(strategy: StrategyCreate): Promise<StrategyResponse> {
    return this.post<StrategyResponse>('/strategies', strategy);
  }

  async updateStrategy(strategyId: number, update: StrategyUpdate): Promise<StrategyResponse> {
    return this.put<StrategyResponse>(`/strategies/${strategyId}`, update);
  }

  async deleteStrategy(strategyId: number): Promise<any> {
    return this.delete(`/strategies/${strategyId}`);
  }

  async cloneStrategy(strategyId: number, newName: string): Promise<StrategyResponse> {
    return this.post<StrategyResponse>(`/strategies/${strategyId}/clone`, { new_name: newName });
  }

  async getStrategyPerformance(strategyId: number, days: number = 30): Promise<StrategyPerformance> {
    return this.get<StrategyPerformance>(`/strategies/${strategyId}/performance`, { days });
  }

  async getStrategyVersions(strategyId: number): Promise<StrategyVersion[]> {
    return this.get<StrategyVersion[]>(`/strategies/${strategyId}/versions`);
  }

  async createStrategyVersion(strategyId: number, version: string, description: string): Promise<StrategyVersion> {
    return this.post<StrategyVersion>(`/strategies/${strategyId}/versions`, { version, description });
  }

  async getIndicators(category?: string, timeframe?: string): Promise<IndicatorInfo[]> {
    return this.get<IndicatorInfo[]>('/strategies/indicators/list', { category, timeframe });
  }

  async getIndicator(indicatorName: string): Promise<IndicatorInfo> {
    return this.get<IndicatorInfo>(`/strategies/indicators/${indicatorName}`);
  }

  async validateRule(rule: any): Promise<any> {
    return this.post('/strategies/validate-rule', rule);
  }

  async validateStrategy(ruleSet: any): Promise<any> {
    return this.post('/strategies/validate-strategy', ruleSet);
  }

  async runBacktest(params: {
    strategy_id: number;
    symbols: string[];
    start_date: string;
    end_date: string;
    timeframes?: string[];
    initial_capital?: number;
  }): Promise<any> {
    return this.post('/strategies/backtest', params);
  }

  // ============================================================================
  // Trading
  // ============================================================================

  async getPaperStatus(): Promise<PaperAccountStatus> {
    return this.get<PaperAccountStatus>('/trading/paper/status');
  }

  async getPositions(params?: { status?: string; exchange?: string; symbol?: string }): Promise<Position[]> {
    return this.get<Position[]>('/trading/positions', params);
  }

  async getPosition(positionId: number): Promise<Position> {
    return this.get<Position>(`/trading/positions/${positionId}`);
  }

  async getPositionTpSl(positionId: number): Promise<TPStage[]> {
    return this.get<TPStage[]>(`/trading/positions/${positionId}/tp-sl`);
  }

  async placePaperTrade(trade: PaperTradeRequest): Promise<PaperTradeResponse> {
    return this.post<PaperTradeResponse>('/trading/paper-trade', trade);
  }

  async closePosition(positionId: number, quantity?: number, orderType: OrderType = 'market'): Promise<any> {
    return this.post(`/trading/positions/${positionId}/close`, { quantity, order_type: orderType });
  }

  async cancelOrder(orderId: number): Promise<any> {
    return this.delete(`/trading/orders/${orderId}`);
  }

  async getOrders(params?: { position_id?: number; status?: string; exchange?: string; symbol?: string }): Promise<Order[]> {
    return this.get<Order[]>('/trading/orders', params);
  }

  async getTradeHistory(params?: {
    symbol?: string;
    exchange?: string;
    direction?: string;
    start_date?: string;
    end_date?: string;
    exit_reason?: string;
    limit?: number;
  }): Promise<TradeHistoryEntry[]> {
    return this.get<TradeHistoryEntry[]>('/trading/history', params);
  }

  async pausePaperTrading(): Promise<any> {
    return this.post('/trading/paper/pause');
  }

  async resumePaperTrading(): Promise<any> {
    return this.post('/trading/paper/resume');
  }

  async resetPaperTrading(): Promise<any> {
    return this.post('/trading/paper/reset');
  }

  async getPnLSummary(days: number = 30): Promise<any> {
    return this.get('/trading/pnl/summary', { days });
  }

  // ============================================================================
  // Configuration
  // ============================================================================

  async getFullConfig(): Promise<FullConfig> {
    return this.get<FullConfig>('/config');
  }

  async getExchangeConfigs(): Promise<ExchangeConfigResponse[]> {
    return this.get<ExchangeConfigResponse[]>('/config/exchanges');
  }

  async updateExchangeConfig(exchangeName: string, config: ExchangeConfig): Promise<any> {
    return this.put(`/config/exchanges/${exchangeName}`, config);
  }

  async testExchangeConnection(exchangeName: string): Promise<any> {
    return this.post(`/config/exchanges/${exchangeName}/test`);
  }

  // Individual config sections
  async getMarketConfig(): Promise<any> { return this.get('/config/market'); }
  async updateMarketConfig(config: any): Promise<any> { return this.put('/config/market', config); }
  async getScannerConfig(): Promise<any> { return this.get('/config/scanner'); }
  async updateScannerConfig(config: any): Promise<any> { return this.put('/config/scanner', config); }
  async getRiskConfig(): Promise<any> { return this.get('/config/risk'); }
  async updateRiskConfig(config: any): Promise<any> { return this.put('/config/risk', config); }
  async getTpSlConfig(): Promise<any> { return this.get('/config/tp-sl'); }
  async updateTpSlConfig(config: any): Promise<any> { return this.put('/config/tp-sl', config); }
  async getLeverageConfig(): Promise<any> { return this.get('/config/leverage'); }
  async updateLeverageConfig(config: any): Promise<any> { return this.put('/config/leverage', config); }
  async getPaperTradingConfig(): Promise<any> { return this.get('/config/paper-trading'); }
  async updatePaperTradingConfig(config: any): Promise<any> { return this.put('/config/paper-trading', config); }
  async getTelegramConfig(): Promise<any> { return this.get('/config/telegram'); }
  async updateTelegramConfig(config: any): Promise<any> { return this.put('/config/telegram', config); }
  async testTelegramBot(): Promise<any> { return this.post('/config/telegram/test'); }
  async getNotificationConfig(): Promise<any> { return this.get('/config/notifications'); }
  async updateNotificationConfig(config: any): Promise<any> { return this.put('/config/notifications', config); }
  async getUiConfig(): Promise<any> { return this.get('/config/ui'); }
  async updateUiConfig(config: any): Promise<any> { return this.put('/config/ui', config); }
  async getBackupConfig(): Promise<any> { return this.get('/config/backup'); }
  async updateBackupConfig(config: any): Promise<any> { return this.put('/config/backup', config); }
  async runBackup(): Promise<any> { return this.post('/config/backup/run'); }
  async validateConfig(): Promise<any> { return this.post('/config/validate'); }
  async getConfigVersion(): Promise<any> { return this.get('/config/version'); }
  async resetConfig(section?: string): Promise<any> { return this.post('/config/reset', { section }); }
  async exportConfig(): Promise<any> { return this.post('/config/export'); }
  async importConfig(encryptedData: string, passphrase: string): Promise<any> { return this.post('/config/import', { encrypted_data: encryptedData, passphrase }); }

  // ============================================================================
  // Analytics
  // ============================================================================

  async getAnalyticsPnLSummary(days: number = 30, params?: any): Promise<PnLSummary> {
    return this.get<PnLSummary>('/analytics/pnl/summary', { days, ...params });
  }

  async getPerformanceMetrics(days: number = 30): Promise<PerformanceMetrics> {
    return this.get<PerformanceMetrics>('/analytics/pnl/metrics', { days });
  }

  async getAnalyticsEquityCurve(days: number = 30): Promise<{ data: EquityCurvePoint[] }> {
    return this.get('/analytics/pnl/equity-curve', { days });
  }

  async getMonthlyReturns(years: number = 1): Promise<{ data: MonthlyReturn[] }> {
    return this.get('/analytics/pnl/monthly-returns', { years });
  }

  async getStrategyBreakdown(days: number = 30): Promise<{ data: BreakdownItem[] }> {
    return this.get('/analytics/pnl/breakdown/strategy', { days });
  }

  async getSymbolBreakdown(days: number = 30): Promise<{ data: BreakdownItem[] }> {
    return this.get('/analytics/pnl/breakdown/symbol', { days });
  }

  async getDirectionBreakdown(days: number = 30): Promise<{ data: BreakdownItem[] }> {
    return this.get('/analytics/pnl/breakdown/direction', { days });
  }

  async getTimeframeBreakdown(days: number = 30): Promise<{ data: BreakdownItem[] }> {
    return this.get('/analytics/pnl/breakdown/timeframe', { days });
  }

  async getRegimeBreakdown(days: number = 30): Promise<{ data: BreakdownItem[] }> {
    return this.get('/analytics/pnl/breakdown/regime', { days });
  }

  async getTpAnalytics(days: number = 30): Promise<TPAnalytics> {
    return this.get<TPAnalytics>('/analytics/pnl/tp-analytics', { days });
  }

  async getTradeDistribution(days: number = 30): Promise<TradeDistribution> {
    return this.get<TradeDistribution>('/analytics/pnl/distribution', { days });
  }

  // Backtesting
  async runAnalyticsBacktest(params: {
    strategy_id: number;
    symbols: string[];
    start_date: string;
    end_date: string;
    timeframes?: string[];
    initial_capital?: number;
    fees_bps?: number;
    slippage_bps?: number;
    funding_rate_pct?: number;
  }): Promise<BacktestResult> {
    return this.post<BacktestResult>('/analytics/backtest/run', params);
  }

  async getBacktest(backtestId: string): Promise<BacktestResult> {
    return this.get<BacktestResult>(`/analytics/backtest/${backtestId}`);
  }

  async listBacktests(strategyId?: number, limit: number = 20): Promise<any> {
    return this.get('/analytics/backtest/list', { strategy_id: strategyId, limit });
  }

  // Walk-Forward
  async runWalkforward(params: {
    strategy_id: number;
    symbols: string[];
    start_date: string;
    end_date: string;
    window_days?: number;
    step_days?: number;
    min_train_days?: number;
  }): Promise<WalkForwardResult> {
    return this.post<WalkForwardResult>('/analytics/walkforward/run', params);
  }

  // Monte Carlo
  async runMonteCarlo(params: {
    strategy_id: number;
    trade_history: any[];
    simulations?: number;
    confidence_levels?: number[];
  }): Promise<MonteCarloResult> {
    return this.post<MonteCarloResult>('/analytics/montecarlo/run', params);
  }

  // Reports
  async getDailyReport(date?: string): Promise<any> {
    return this.get('/analytics/reports/daily', { date });
  }

  async getWeeklyReport(weekStart?: string): Promise<any> {
    return this.get('/analytics/reports/weekly', { week_start: weekStart });
  }

  async getMonthlyReport(month?: string): Promise<any> {
    return this.get('/analytics/reports/monthly', { month });
  }

  // ============================================================================
  // System
  // ============================================================================

  async getSystemHealth(): Promise<SystemHealth> {
    return this.get<SystemHealth>('/system/health');
  }

  async getLogs(params?: {
    level?: string;
    service?: string;
    component?: string;
    exchange?: string;
    start_time?: string;
    end_time?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<LogsResponse> {
    return this.get<LogsResponse>('/system/logs', params);
  }

  async getErrorLogs(hours: number = 24, limit: number = 100): Promise<LogEntry[]> {
    return this.get<LogEntry[]>('/system/logs/errors', { hours, limit });
  }

  // Telegram
  async getTelegramStatus(): Promise<TelegramBotStatus> {
    return this.get<TelegramBotStatus>('/system/telegram/status');
  }

  async getTelegramCommandLogs(userId?: number, limit: number = 50): Promise<TelegramCommandLog[]> {
    return this.get<TelegramCommandLog[]>('/system/telegram/commands', { user_id: userId, limit });
  }

  async sendTelegramTestMessage(chatId: number, message?: string): Promise<any> {
    return this.post('/system/telegram/send-test', { chat_id: chatId, message });
  }

  // Live Trading
  async getLiveTradingStatus(): Promise<LiveTradingStatus> {
    return this.get<LiveTradingStatus>('/system/live/status');
  }

  async liveTradingAction(action: LiveTradingAction): Promise<any> {
    return this.post('/system/live/action', action);
  }

  // Storage
  async getStorageInfo(): Promise<StorageInfo> {
    return this.get<StorageInfo>('/system/storage');
  }

  // Backup
  async listBackups(): Promise<BackupInfo[]> {
    return this.get<BackupInfo[]>('/system/backups');
  }

  async createBackup(description?: string): Promise<any> {
    return this.post('/system/backups/create', { description });
  }

  async restoreBackup(filename: string, confirm: boolean = false): Promise<any> {
    return this.post(`/system/backups/${filename}/restore`, { confirm });
  }

  async deleteBackup(filename: string): Promise<any> {
    return this.delete(`/system/backups/${filename}`);
  }

  // Audit Logs
  async getAuditLogs(params?: {
    user_id?: string;
    action?: string;
    resource_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<AuditLogEntry[]> {
    return this.get<AuditLogEntry[]>('/system/audit-logs', params);
  }

  // System Events
  async getSystemEvents(params?: {
    event_type?: string;
    severity?: string;
    unresolved_only?: boolean;
    limit?: number;
  }): Promise<SystemEvent[]> {
    return this.get<SystemEvent[]>('/system/events', params);
  }

  async resolveEvent(eventId: number): Promise<any> {
    return this.post(`/system/events/${eventId}/resolve`);
  }

  // Diagnostics
  async runDiagnostics(): Promise<any> {
    return this.get('/system/diagnostics');
  }

  // Version
  async getVersion(): Promise<any> {
    return this.get('/system/version');
  }

  async getSystemInfo(): Promise<any> {
    return this.get('/system/info');
  }
}

// Export singleton instance
export const api = new ApiClient();

// Helper for hook usage
export function useApi() {
  return api;
}
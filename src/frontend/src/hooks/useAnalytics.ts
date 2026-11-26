/**
 * Custom hooks for Analytics data
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import type {
  PnLSummary, PerformanceMetrics, EquityCurvePoint, MonthlyReturn,
  BreakdownItem, TPAnalytics, TradeDistribution,
  BacktestResult, WalkForwardResult, MonteCarloResult
} from '../types/api';

// ============================================================================
// PnL Analytics Hooks
// ============================================================================

export function usePnLSummary(
  days: number = 30,
  params?: { strategy_id?: number; symbol?: string; direction?: string }
) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'summary', days, params],
    queryFn: () => api.getPnLSummary(days, params),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function usePerformanceMetrics(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'metrics', days],
    queryFn: () => api.getPerformanceMetrics(days),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useEquityCurve(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'equity-curve', days],
    queryFn: () => api.getEquityCurve(days),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useMonthlyReturns(years: number = 1) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'monthly-returns', years],
    queryFn: () => api.getMonthlyReturns(years),
    staleTime: 60000,
  });
}

export function useStrategyBreakdown(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'breakdown', 'strategy', days],
    queryFn: () => api.getStrategyBreakdown(days),
    staleTime: 30000,
  });
}

export function useSymbolBreakdown(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'breakdown', 'symbol', days],
    queryFn: () => api.getSymbolBreakdown(days),
    staleTime: 30000,
  });
}

export function useDirectionBreakdown(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'breakdown', 'direction', days],
    queryFn: () => api.getDirectionBreakdown(days),
    staleTime: 30000,
  });
}

export function useTimeframeBreakdown(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'breakdown', 'timeframe', days],
    queryFn: () => api.getTimeframeBreakdown(days),
    staleTime: 30000,
  });
}

export function useRegimeBreakdown(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'breakdown', 'regime', days],
    queryFn: () => api.getRegimeBreakdown(days),
    staleTime: 30000,
  });
}

export function useTpAnalytics(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'tp-analytics', days],
    queryFn: () => api.getTpAnalytics(days),
    staleTime: 30000,
  });
}

export function useTradeDistribution(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'pnl', 'distribution', days],
    queryFn: () => api.getTradeDistribution(days),
    staleTime: 30000,
  });
}

// ============================================================================
// Research Hooks
// ============================================================================

export function useBacktest() {
  return useMutation({
    mutationFn: (params: {
      strategy_id: number;
      symbols: string[];
      start_date: string;
      end_date: string;
      timeframes?: string[];
      initial_capital?: number;
      fees_bps?: number;
      slippage_bps?: number;
      funding_rate_pct?: number;
    }) => api.runBacktest(params),
  });
}

export function useWalkforward() {
  return useMutation({
    mutationFn: (params: {
      strategy_id: number;
      symbols: string[];
      start_date: string;
      end_date: string;
      window_days?: number;
      step_days?: number;
      min_train_days?: number;
    }) => api.runWalkforward(params),
  });
}

export function useMonteCarlo() {
  return useMutation({
    mutationFn: (params: {
      strategy_id: number;
      trade_history: any[];
      simulations?: number;
      confidence_levels?: number[];
    }) => api.runMonteCarlo(params),
  });
}

// ============================================================================
// Combined export for convenience
// ============================================================================

export function useAnalytics() {
  return {
    pnlSummary: usePnLSummary,
    performanceMetrics: usePerformanceMetrics,
    equityCurve: useEquityCurve,
    monthlyReturns: useMonthlyReturns,
    strategyBreakdown: useStrategyBreakdown,
    symbolBreakdown: useSymbolBreakdown,
    directionBreakdown: useDirectionBreakdown,
    timeframeBreakdown: useTimeframeBreakdown,
    regimeBreakdown: useRegimeBreakdown,
    tpAnalytics: useTpAnalytics,
    tradeDistribution: useTradeDistribution,
    backtest: useBacktest,
    walkforward: useWalkforward,
    monteCarlo: useMonteCarlo,
  };
}
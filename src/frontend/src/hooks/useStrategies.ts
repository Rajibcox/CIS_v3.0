/**
 * Custom hooks for Strategies data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { StrategyResponse, StrategyCreate, StrategyUpdate, StrategyPerformance, StrategyVersion, IndicatorInfo } from '../types/api';

// ============================================================================
// Strategy List Hooks
// ============================================================================

export function useStrategies(activeOnly?: boolean, includePerformance?: boolean) {
  return useQuery({
    queryKey: ['strategies', activeOnly, includePerformance],
    queryFn: () => api.getStrategies(activeOnly, includePerformance),
    staleTime: 30000,
  });
}

export function useStrategy(strategyId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['strategy', strategyId],
    queryFn: () => api.getStrategy(strategyId),
    enabled: enabled && !!strategyId,
    staleTime: 30000,
  });
}

export function useStrategyPerformance(strategyId: number, days: number = 30, enabled: boolean = true) {
  return useQuery({
    queryKey: ['strategyPerformance', strategyId, days],
    queryFn: () => api.getStrategyPerformance(strategyId, days),
    enabled: enabled && !!strategyId,
    staleTime: 60000,
  });
}

export function useStrategyVersions(strategyId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['strategyVersions', strategyId],
    queryFn: () => api.getStrategyVersions(strategyId),
    enabled: enabled && !!strategyId,
    staleTime: 60000,
  });
}

export function useIndicators(category?: string, timeframe?: string) {
  return useQuery({
    queryKey: ['indicators', category, timeframe],
    queryFn: () => api.getIndicators(category, timeframe),
    staleTime: 300000, // 5 minutes
  });
}

export function useIndicator(indicatorName: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['indicator', indicatorName],
    queryFn: () => api.getIndicator(indicatorName),
    enabled: enabled && !!indicatorName,
    staleTime: 300000,
  });
}

// ============================================================================
// Strategy Mutations
// ============================================================================

export function useCreateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategy: StrategyCreate) => api.createStrategy(strategy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ strategyId, update }: { strategyId: number; update: StrategyUpdate }) =>
      api.updateStrategy(strategyId, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      queryClient.invalidateQueries({ queryKey: ['strategy'] });
    },
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (strategyId: number) => api.deleteStrategy(strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

export function useCloneStrategy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ strategyId, newName }: { strategyId: number; newName: string }) =>
      api.cloneStrategy(strategyId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });
}

export function useCreateStrategyVersion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ strategyId, version, description }: { strategyId: number; version: string; description: string }) =>
      api.createStrategyVersion(strategyId, version, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategyVersions'] });
    },
  });
}

// ============================================================================
// Validation Hooks
// ============================================================================

export function useValidateRule() {
  return useMutation({
    mutationFn: (rule: any) => api.validateRule(rule),
  });
}

export function useValidateStrategy() {
  return useMutation({
    mutationFn: (ruleSet: any) => api.validateStrategy(ruleSet),
  });
}

// ============================================================================
// Backtest Hook
// ============================================================================

export function useRunBacktest() {
  return useMutation({
    mutationFn: (params: {
      strategy_id: number;
      symbols: string[];
      start_date: string;
      end_date: string;
      timeframes?: string[];
      initial_capital?: number;
    }) => api.runBacktest(params),
  });
}
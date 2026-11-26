/**
 * Custom hooks for Market Intelligence data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { MarketOverview, SymbolSnapshot, OpportunityResponse } from '../types/api';

// ============================================================================
// Market Overview Hooks
// ============================================================================

export function useMarketOverview() {
  return useQuery({
    queryKey: ['marketOverview'],
    queryFn: () => api.getMarketOverview(),
    refetchInterval: 30000, // 30 seconds
    staleTime: 15000,
  });
}

export function useSymbolSnapshot(symbol: string, exchange: string = 'binance', enabled: boolean = true) {
  return useQuery({
    queryKey: ['symbolSnapshot', symbol, exchange],
    queryFn: () => api.getSymbolSnapshot(symbol, exchange),
    enabled: enabled && !!symbol,
    refetchInterval: 5000,
    staleTime: 3000,
  });
}

export function useMarketRegime() {
  return useQuery({
    queryKey: ['marketRegime'],
    queryFn: () => api.getMarketRegime(),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

export function useFundingRates() {
  return useQuery({
    queryKey: ['fundingRates'],
    queryFn: () => api.getFundingRates(),
    refetchInterval: 300000, // 5 minutes
    staleTime: 120000,
  });
}

export function useOpenInterest() {
  return useQuery({
    queryKey: ['openInterest'],
    queryFn: () => api.getOpenInterest(),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

export function useLiquidations() {
  return useQuery({
    queryKey: ['liquidations'],
    queryFn: () => api.getLiquidations(),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

// ============================================================================
// Scanner Hooks
// ============================================================================

export function useMarketScan(params?: {
  exchanges?: string[];
  timeframes?: string[];
  minScore?: number;
  maxResults?: number;
}) {
  return useQuery({
    queryKey: ['marketScan', params],
    queryFn: () => api.scanMarkets(params),
    refetchInterval: 30000, // 30 seconds
    staleTime: 15000,
  });
}

export function useLongOpportunities(minScore?: number, maxResults?: number) {
  return useQuery({
    queryKey: ['longOpportunities', minScore, maxResults],
    queryFn: () => api.getLongOpportunities(minScore, maxResults),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useShortOpportunities(minScore?: number, maxResults?: number) {
  return useQuery({
    queryKey: ['shortOpportunities', minScore, maxResults],
    queryFn: () => api.getShortOpportunities(minScore, maxResults),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

// ============================================================================
// Manual Scan Trigger
// ============================================================================

export function useTriggerScan() {
  return useMutation({
    mutationFn: () => api.triggerScan(),
  });
}
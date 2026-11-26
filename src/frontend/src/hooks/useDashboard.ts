/**
 * Custom hooks for Dashboard data fetching
 * Using TanStack Query (React Query) for server state management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { DashboardOverview, PositionSummary, EquityCurvePoint } from '../types/api';

// ============================================================================
// Overview Hooks
// ============================================================================

export function useDashboardOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: () => api.getOverview(),
    refetchInterval: 5000, // Refetch every 5 seconds
    staleTime: 3000,
  });
}

export function useEquityCurve(days: number = 30) {
  return useQuery({
    queryKey: ['equityCurve', days],
    queryFn: () => api.getEquityCurve(days),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useQuickStats() {
  return useQuery({
    queryKey: ['quickStats'],
    queryFn: () => api.getQuickStats(),
    refetchInterval: 2000,
    staleTime: 1000,
  });
}

export function useOpenPositions() {
  return useQuery({
    queryKey: ['positions', 'open'],
    queryFn: () => api.getOpenPositions(),
    refetchInterval: 5000,
    staleTime: 3000,
  });
}

// ============================================================================
// Position Mutation Hooks
// ============================================================================

export function useClosePosition() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ positionId, quantity, orderType }: { positionId: number; quantity?: number; orderType?: string }) =>
      api.closePosition(positionId, quantity, orderType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['overview'] });
    },
  });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orderId: number) => api.cancelOrder(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
    },
  });
}

// ============================================================================
// Paper Trading Hooks
// ============================================================================

export function usePaperStatus() {
  return useQuery({
    queryKey: ['paperStatus'],
    queryFn: () => api.getPaperStatus(),
    refetchInterval: 5000,
    staleTime: 3000,
  });
}

export function usePaperTrade() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (trade: any) => api.placePaperTrade(trade),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['paperStatus'] });
      queryClient.invalidateQueries({ queryKey: ['overview'] });
    },
  });
}

export function usePaperControl() {
  const queryClient = useQueryClient();

  const pause = useMutation({
    mutationFn: () => api.pausePaperTrading(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['paperStatus'] }),
  });

  const resume = useMutation({
    mutationFn: () => api.resumePaperTrading(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['paperStatus'] }),
  });

  const reset = useMutation({
    mutationFn: () => api.resetPaperTrading(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paperStatus'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['overview'] });
    },
  });

  return { pause, resume, reset };
}

// ============================================================================
// Trade History Hook
// ============================================================================

export function useTradeHistory(params?: {
  symbol?: string;
  exchange?: string;
  direction?: string;
  startDate?: string;
  endDate?: string;
  exitReason?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['tradeHistory', params],
    queryFn: () => api.getTradeHistory(params),
    staleTime: 30000,
  });
}

export function usePnLSummary(days: number = 30) {
  return useQuery({
    queryKey: ['pnlSummary', days],
    queryFn: () => api.getPnLSummary(days),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}
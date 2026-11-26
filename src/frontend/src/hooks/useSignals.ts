/**
 * Custom hooks for Signals data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { SignalResponse, SignalDetail, SignalStats } from '../types/api';

// ============================================================================
// Signal List Hooks
// ============================================================================

export function useSignals(params?: {
  status?: string;
  direction?: string;
  strategy?: string;
  symbol?: string;
  exchange?: string;
  startDate?: string;
  endDate?: string;
  minScore?: number;
  page?: number;
  pageSize?: number;
}) {
  return useQuery({
    queryKey: ['signals', params],
    queryFn: () => api.getSignals(params),
    staleTime: 10000,
  });
}

export function useActiveSignals() {
  return useQuery({
    queryKey: ['signals', 'active'],
    queryFn: () => api.getActiveSignals(),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}

export function useBestSignals(limit: number = 10) {
  return useQuery({
    queryKey: ['signals', 'best', limit],
    queryFn: () => api.getBestSignals(limit),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}

export function useSignalDetail(signalId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['signalDetail', signalId],
    queryFn: () => api.getSignalDetail(signalId),
    enabled: enabled && !!signalId,
    staleTime: 30000,
  });
}

export function useSignalStats(days: number = 30) {
  return useQuery({
    queryKey: ['signalStats', days],
    queryFn: () => api.getSignalStats(days),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

// ============================================================================
// Signal Actions
// ============================================================================

export function useExecutePaperTrade() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (signalId: number) => api.executePaperTrade(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['overview'] });
    },
  });
}

export function useTriggerSignalScan() {
  return useMutation({
    mutationFn: () => api.triggerScan(),
  });
}
/**
 * Custom hooks for System data
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../services/api';
import type { SystemHealth, LogEntry, LogsResponse, TelegramBotStatus, TelegramCommandLog, LiveTradingStatus, LiveTradingAction, StorageInfo, BackupInfo, AuditLogEntry, SystemEvent } from '../types/api';

// ============================================================================
// System Health Hooks
// ============================================================================

export function useSystemHealth() {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: () => api.getSystemHealth(),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useLogs(params?: {
  level?: string;
  service?: string;
  component?: string;
  exchange?: string;
  startTime?: string;
  endTime?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}) {
  return useQuery({
    queryKey: ['system', 'logs', params],
    queryFn: () => api.getLogs(params),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}

export function useErrorLogs(hours: number = 24, limit: number = 100) {
  return useQuery({
    queryKey: ['system', 'logs', 'errors', hours, limit],
    queryFn: () => api.getErrorLogs(hours, limit),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

// ============================================================================
// Telegram Hooks
// ============================================================================

export function useTelegramStatus() {
  return useQuery({
    queryKey: ['system', 'telegram', 'status'],
    queryFn: () => api.getTelegramStatus(),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useTelegramCommandLogs(userId?: number, limit: number = 50) {
  return useQuery({
    queryKey: ['system', 'telegram', 'commands', userId, limit],
    queryFn: () => api.getTelegramCommandLogs(userId, limit),
    staleTime: 30000,
  });
}

export function useSendTelegramTest() {
  return useMutation({
    mutationFn: ({ chatId, message }: { chatId: number; message?: string }) =>
      api.sendTelegramTestMessage(chatId, message),
  });
}

// ============================================================================
// Live Trading Hooks
// ============================================================================

export function useLiveTradingStatus() {
  return useQuery({
    queryKey: ['system', 'live', 'status'],
    queryFn: () => api.getLiveTradingStatus(),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}

export function useLiveTradingAction() {
  return useMutation({
    mutationFn: (action: LiveTradingAction) => api.liveTradingAction(action),
  });
}

// ============================================================================
// Storage Hooks
// ============================================================================

export function useStorageInfo() {
  return useQuery({
    queryKey: ['system', 'storage'],
    queryFn: () => api.getStorageInfo(),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

// ============================================================================
// Backup Hooks
// ============================================================================

export function useBackups() {
  return useQuery({
    queryKey: ['system', 'backups'],
    queryFn: () => api.listBackups(),
    staleTime: 30000,
  });
}

export function useCreateBackup() {
  return useMutation({
    mutationFn: (description?: string) => api.createBackup(description),
  });
}

export function useRestoreBackup() {
  return useMutation({
    mutationFn: ({ filename, confirm }: { filename: string; confirm: boolean }) =>
      api.restoreBackup(filename, confirm),
  });
}

export function useDeleteBackup() {
  return useMutation({
    mutationFn: (filename: string) => api.deleteBackup(filename),
  });
}

// ============================================================================
// Audit Logs Hooks
// ============================================================================

export function useAuditLogs(params?: {
  userId?: string;
  action?: string;
  resourceType?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['system', 'audit-logs', params],
    queryFn: () => api.getAuditLogs(params),
    staleTime: 30000,
  });
}

// ============================================================================
// System Events Hooks
// ============================================================================

export function useSystemEvents(params?: {
  eventType?: string;
  severity?: string;
  unresolvedOnly?: boolean;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['system', 'events', params],
    queryFn: () => api.getSystemEvents(params),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useResolveEvent() {
  return useMutation({
    mutationFn: (eventId: number) => api.resolveEvent(eventId),
  });
}

// ============================================================================
// Diagnostics Hooks
// ============================================================================

export function useDiagnostics() {
  return useMutation({
    mutationFn: () => api.runDiagnostics(),
  });
}

// ============================================================================
// Version Hooks
// ============================================================================

export function useVersion() {
  return useQuery({
    queryKey: ['system', 'version'],
    queryFn: () => api.getVersion(),
    staleTime: 300000,
  });
}

export function useSystemInfo() {
  return useQuery({
    queryKey: ['system', 'info'],
    queryFn: () => api.getSystemInfo(),
    staleTime: 300000,
  });
}
/**
 * Custom hooks for Configuration data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { FullConfig, ExchangeConfig, ExchangeConfigResponse } from '../types/api';

// ============================================================================
// Full Config Hook
// ============================================================================

export function useFullConfig() {
  return useQuery({
    queryKey: ['config', 'full'],
    queryFn: () => api.getFullConfig(),
    staleTime: 300000, // 5 minutes
  });
}

// ============================================================================
// Exchange Config Hooks
// ============================================================================

export function useExchangeConfigs() {
  return useQuery({
    queryKey: ['config', 'exchanges'],
    queryFn: () => api.getExchangeConfigs(),
    staleTime: 30000,
  });
}

export function useUpdateExchangeConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ exchangeName, config }: { exchangeName: string; config: ExchangeConfig }) =>
      api.updateExchangeConfig(exchangeName, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'exchanges'] });
      queryClient.invalidateQueries({ queryKey: ['config', 'full'] });
    },
  });
}

export function useTestExchangeConnection() {
  return useMutation({
    mutationFn: (exchangeName: string) => api.testExchangeConnection(exchangeName),
  });
}

// ============================================================================
// Individual Config Sections
// ============================================================================

function createConfigSectionHooks(sectionName: string, getFn: () => Promise<any>, updateFn: (config: any) => Promise<any>) {
  const queryKey = ['config', sectionName];

  return {
    useGet: () => useQuery({
      queryKey,
      queryFn: getFn,
      staleTime: 300000,
    }),
    useUpdate: () => {
      const queryClient = useQueryClient();
      return useMutation({
        mutationFn: (config: any) => updateFn(config),
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey });
          queryClient.invalidateQueries({ queryKey: ['config', 'full'] });
        },
      });
    },
  };
}

export const {
  useGet: useMarketConfig,
  useUpdate: useUpdateMarketConfig,
} = createConfigSectionHooks('market', api.getMarketConfig, api.updateMarketConfig);

export const {
  useGet: useScannerConfig,
  useUpdate: useUpdateScannerConfig,
} = createConfigSectionHooks('scanner', api.getScannerConfig, api.updateScannerConfig);

export const {
  useGet: useRiskConfig,
  useUpdate: useUpdateRiskConfig,
} = createConfigSectionHooks('risk', api.getRiskConfig, api.updateRiskConfig);

export const {
  useGet: useTpSlConfig,
  useUpdate: useUpdateTpSlConfig,
} = createConfigSectionHooks('tpSl', api.getTpSlConfig, api.updateTpSlConfig);

export const {
  useGet: useLeverageConfig,
  useUpdate: useUpdateLeverageConfig,
} = createConfigSectionHooks('leverage', api.getLeverageConfig, api.updateLeverageConfig);

export const {
  useGet: usePaperTradingConfig,
  useUpdate: useUpdatePaperTradingConfig,
} = createConfigSectionHooks('paperTrading', api.getPaperTradingConfig, api.updatePaperTradingConfig);

export const {
  useGet: useTelegramConfig,
  useUpdate: useUpdateTelegramConfig,
} = createConfigSectionHooks('telegram', api.getTelegramConfig, api.updateTelegramConfig);

export function useTestTelegramBot() {
  return useMutation({
    mutationFn: () => api.testTelegramBot(),
  });
}

export const {
  useGet: useNotificationConfig,
  useUpdate: useUpdateNotificationConfig,
} = createConfigSectionHooks('notifications', api.getNotificationConfig, api.updateNotificationConfig);

export const {
  useGet: useUiConfig,
  useUpdate: useUpdateUiConfig,
} = createConfigSectionHooks('ui', api.getUiConfig, api.updateUiConfig);

export const {
  useGet: useBackupConfig,
  useUpdate: useUpdateBackupConfig,
} = createConfigSectionHooks('backup', api.getBackupConfig, api.updateBackupConfig);

export function useRunBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (description?: string) => api.runBackup(description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'backup'] });
    },
  });
}

export function useValidateConfig() {
  return useMutation({
    mutationFn: () => api.validateConfig(),
  });
}

export function useConfigVersion() {
  return useQuery({
    queryKey: ['config', 'version'],
    queryFn: () => api.getConfigVersion(),
    staleTime: 300000,
  });
}

export function useResetConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (section?: string) => api.resetConfig(section),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useExportConfig() {
  return useMutation({
    mutationFn: () => api.exportConfig(),
  });
}

export function useImportConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ encryptedData, passphrase }: { encryptedData: string; passphrase: string }) =>
      api.importConfig(encryptedData, passphrase),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}
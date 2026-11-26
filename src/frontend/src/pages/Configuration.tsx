import React, { useState } from 'react';
import { useFullConfig, useExchangeConfigs, useUpdateExchangeConfig, useTestExchangeConnection } from '../hooks/useConfig';
import { useValidateConfig, useRunBackup, useConfigVersion, useResetConfig, useExportConfig, useImportConfig } from '../hooks/useConfig';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Label } from '../components/common/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/common/Select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/common/Tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import { Badge } from '../components/common/Badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/common/Dialog';
import { cn } from '../utils/cn';
import {
  Save, RotateCcw, Download, Upload, AlertTriangle, CheckCircle,
  Server, Shield, Zap, Settings, Database, Bell, MessageSquare,
  Eye, EyeOff, Key, Lock, Unlock, TestTube, Globe
} from 'lucide-react';

export function ConfigurationPage() {
  const { data: config, isLoading } = useFullConfig();
  const { data: exchangeConfigs } = useExchangeConfigs();
  const updateExchangeConfig = useUpdateExchangeConfig();
  const testExchangeConnection = useTestExchangeConnection();
  const validateConfig = useValidateConfig();
  const runBackup = useRunBackup();
  const { data: version } = useConfigVersion();
  const resetConfig = useResetConfig();
  const exportConfig = useExportConfig();
  const importConfig = useImportConfig();

  const [activeTab, setActiveTab] = useState<'exchanges' | 'market' | 'scanner' | 'risk' | 'tp-sl' | 'leverage' | 'paper' | 'telegram' | 'notifications' | 'ui' | 'backup' | 'advanced'>('exchanges');
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [validationResult, setValidationResult] = useState<any>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importData, setImportData] = useState('');
  const [importPassphrase, setImportPassphrase] = '';

  // Form states for each section
  const [exchangeForms, setExchangeForms] = useState<Record<string, any>>({});
  const [marketForm, setMarketForm] = useState<any>({});
  const [scannerForm, setScannerForm] = useState<any>({});
  const [riskForm, setRiskForm] = useState<any>({});
  const [tpSlForm, setTpSlForm] = useState<any>({});
  const [leverageForm, setLeverageForm] = useState<any>({});
  const [paperForm, setPaperForm] = useState<any>({});
  const [telegramForm, setTelegramForm] = useState<any>({});
  const [notificationsForm, setNotificationsForm] = useState<any>({});
  const [uiForm, setUiForm] = useState<any>({});
  const [backupForm, setBackupForm] = useState<any>({});

  // Initialize forms from config
  React.useEffect(() => {
    if (config) {
      // Initialize exchange forms
      const exchForms: Record<string, any> = {};
      Object.entries(config.exchanges).forEach(([key, value]) => {
        exchForms[key] = { ...value, api_key: '', api_secret: '', passphrase: '' }; // Don't populate secrets
      });
      setExchangeForms(exchForms);

      setMarketForm(config.market);
      setScannerForm(config.scanner);
      setRiskForm(config.risk);
      setTpSlForm(config.tp_sl);
      setLeverageForm(config.leverage);
      setPaperForm(config.paper_trading);
      setTelegramForm({ ...config.telegram, bot_token: '' });
      setNotificationsForm(config.notifications);
      setUiForm(config.ui);
      setBackupForm(config.backup);
    }
  }, [config]);

  const handleSave = async (section: string, data: any) => {
    setSaveStatus('saving');
    try {
      // In real app, call appropriate update API
      // await updateConfigSection(section, data);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      setSaveStatus('error');
    }
  };

  const handleValidate = async () => {
    const result = await validateConfig.mutateAsync();
    setValidationResult(result);
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Configuration Center</h1>
          <p className="text-muted-foreground">Manage all system settings through the web UI</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleValidate} disabled={validateConfig.isPending}>
            <AlertTriangle className="h-4 w-4 mr-2" />
            Validate All
          </Button>
          <Button variant="outline" onClick={() => exportConfig.mutate()} disabled={exportConfig.isPending}>
            <Download className="h-4 w-4 mr-2" />
            Export Config
          </Button>
          <Button variant="outline" onClick={() => setShowImportDialog(true)} disabled={importConfig.isPending}>
            <Upload className="h-4 w-4 mr-2" />
            Import Config
          </Button>
          <Button onClick={() => handleSave('all', config)} disabled={saveStatus === 'saving' || !config}>
            <Save className="h-4 w-4 mr-2" />
            {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved!' : 'Save All Changes'}
          </Button>
        </div>
      </div>

      {/* Validation Result */}
      {validationResult && (
        <Card className={cn(validationResult.valid ? 'border-green-500/20' : 'border-red-500/20')}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              {validationResult.valid ? (
                <CheckCircle className="h-5 w-5 text-green-400" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-400" />
              )}
              <span className="font-medium">
                {validationResult.valid ? 'Configuration Valid' : 'Validation Errors Found'}
              </span>
            </div>
            {validationResult.errors.length > 0 && (
              <ul className="list-disc list-inside space-y-1 text-sm text-red-400 mb-2">
                {validationResult.errors.map((e: string, i: number) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
            {validationResult.warnings.length > 0 && (
              <ul className="list-disc list-inside space-y-1 text-sm text-yellow-400">
                {validationResult.warnings.map((w: string, i: number) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {/* Save Status Toast */}
      {saveStatus === 'saved' && (
        <div className="fixed bottom-4 right-4 z-50 animate-slide-in-from-top">
          <Card className="border-green-500/50 bg-green-500/5">
            <CardContent className="flex items-center gap-2 p-3">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <span className="text-green-400">Configuration saved successfully</span>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="exchanges" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 md:grid-cols-6 lg:grid-cols-12">
          <TabsTrigger value="exchanges"><Server className="h-4 w-4 mr-2" />Exchanges</TabsTrigger>
          <TabsTrigger value="market"><Globe className="h-4 w-4 mr-2" />Market</TabsTrigger>
          <TabsTrigger value="scanner"><Zap className="h-4 w-4 mr-2" />Scanner</TabsTrigger>
          <TabsTrigger value="risk"><Shield className="h-4 w-4 mr-2" />Risk</TabsTrigger>
          <TabsTrigger value="tp-sl"><Zap className="h-4 w-4 mr-2" />TP/SL</TabsTrigger>
          <TabsTrigger value="leverage"><Shield className="h-4 w-4 mr-2" />Leverage</TabsTrigger>
          <TabsTrigger value="paper"><TestTube className="h-4 w-4 mr-2" />Paper Trading</TabsTrigger>
          <TabsTrigger value="telegram"><MessageSquare className="h-4 w-4 mr-2" />Telegram</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="h-4 w-4 mr-2" />Notifications</TabsTrigger>
          <TabsTrigger value="ui"><Settings className="h-4 w-4 mr-2" />UI</TabsTrigger>
          <TabsTrigger value="backup"><Database className="h-4 w-4 mr-2" />Backup</TabsTrigger>
          <TabsTrigger value="advanced"><Key className="h-4 w-4 mr-2" />Advanced</TabsTrigger>
        </TabsList>

        {/* Exchanges Tab */}
        <TabsContent value="exchanges">
          <ExchangesTab
            exchanges={exchangeConfigs}
            forms={exchangeForms}
            onFormChange={setExchangeForms}
            onSave={(data) => handleSave('exchanges', data)}
            onTest={testExchangeConnection}
          />
        </TabsContent>

        {/* Market Tab */}
        <TabsContent value="market">
          <ConfigFormSection
            title="Market Data Configuration"
            form={marketForm}
            onChange={setMarketForm}
            onSave={(data) => handleSave('market', data)}
            fields={[
              { key: 'quote_asset', label: 'Quote Asset', type: 'text' },
              { key: 'contract_type', label: 'Contract Type', type: 'text' },
              { key: 'min_volume_24h', label: 'Min 24h Volume', type: 'number', step: 1000000 },
              { key: 'max_spread_bps', label: 'Max Spread (bps)', type: 'number', step: 1 },
              { key: 'min_history_days', label: 'Min History Days', type: 'number' },
              { key: 'primary_timeframe', label: 'Primary Timeframe', type: 'select', options: ['3m', '5m', '15m', '1h', '4h', '1d'] },
            ]}
            arrayFields={{
              enabled_exchanges: { label: 'Enabled Exchanges', itemLabel: 'Exchange', type: 'select', options: ['binance', 'bitget'] },
              supported_timeframes: { label: 'Supported Timeframes', itemLabel: 'Timeframe', type: 'select', options: ['3m', '5m', '15m', '1h', '4h', '1d'] },
              context_timeframes: { label: 'Context Timeframes', itemLabel: 'Timeframe', type: 'select', options: ['3m', '5m', '15m', '1h', '4h', '1d'] },
            }}
          />
        </TabsContent>

        {/* Scanner Tab */}
        <TabsContent value="scanner">
          <ConfigFormSection
            title="Market Scanner Configuration"
            form={scannerForm}
            onChange={setScannerForm}
            onSave={(data) => handleSave('scanner', data)}
            fields={[
              { key: 'scan_interval_seconds', label: 'Scan Interval (seconds)', type: 'number', min: 60 },
              { key: 'max_candidates', label: 'Max Candidates', type: 'number', min: 10, max: 500 },
              { key: 'min_signal_score', label: 'Min Signal Score', type: 'number', min: 0, max: 100, step: 1 },
            ]}
            booleanFields={[
              { key: 'volume_filter', label: 'Volume Filter' },
              { key: 'spread_filter', label: 'Spread Filter' },
              { key: 'volatility_filter', label: 'Volatility Filter' },
              { key: 'regime_filter', label: 'Regime Filter' },
              { key: 'btc_correlation_filter', label: 'BTC Correlation Filter' },
            ]}
            numberFields={[
              { key: 'min_btc_correlation', label: 'Min BTC Correlation', min: -1, max: 1, step: 0.1 },
              { key: 'max_btc_correlation', label: 'Max BTC Correlation', min: -1, max: 1, step: 0.1 },
            ]}
          />
        </TabsContent>

        {/* Risk Tab */}
        <TabsContent value="risk">
          <ConfigFormSection
            title="Risk Management Configuration"
            form={riskForm}
            onChange={setRiskForm}
            onSave={(data) => handleSave('risk', data)}
            fields={[
              { key: 'initial_equity', label: 'Initial Equity (USDT)', type: 'number', step: 10, min: 10 },
              { key: 'risk_per_trade_pct', label: 'Risk Per Trade (%)', type: 'number', min: 0.1, max: 5, step: 0.1 },
              { key: 'max_simultaneous_positions', label: 'Max Simultaneous Positions', type: 'number', min: 1, max: 20 },
              { key: 'max_leverage', label: 'Max Leverage', type: 'number', min: 1, max: 100 },
              { key: 'daily_loss_limit_pct', label: 'Daily Loss Limit (%)', type: 'number', min: 0.5, max: 10, step: 0.1 },
              { key: 'drawdown_warning_pct', label: 'Drawdown Warning (%)', type: 'number', min: 1, max: 20, step: 0.5 },
              { key: 'emergency_drawdown_pct', label: 'Emergency Drawdown (%)', type: 'number', min: 5, max: 50, step: 0.5 },
              { key: 'max_correlated_exposure_pct', label: 'Max Correlated Exposure (%)', type: 'number', min: 10, max: 100, step: 5 },
              { key: 'min_risk_reward', label: 'Min Risk/Reward', type: 'number', min: 1, max: 10, step: 0.1 },
              { key: 'min_stop_distance_pct', label: 'Min Stop Distance (%)', type: 'number', min: 0.1, max: 5, step: 0.1 },
            ]}
          />
        </TabsContent>

        {/* TP/SL Tab */}
        <TabsContent value="tp-sl">
          <ConfigFormSection
            title="Take Profit / Stop Loss Configuration"
            form={tpSlForm}
            onChange={setTpSlForm}
            onSave={(data) => handleSave('tp_sl', data)}
            fields={[
              { key: 'trailing_atr_multiplier', label: 'Trailing ATR Multiplier', type: 'number', step: 0.1, min: 0.5, max: 5 },
              { key: 'min_trailing_distance_pct', label: 'Min Trailing Distance (%)', type: 'number', step: 0.01, min: 0.01, max: 1 },
              { key: 'runner_trailing_type', label: 'Runner Trailing Type', type: 'select', options: ['atr', 'structure', 'hybrid'] },
              { key: 'runner_min_profit_pct', label: 'Runner Min Profit (%)', type: 'number', step: 0.1, min: 0 },
            ]}
            booleanFields={[
              { key: 'break_even_fee_aware', label: 'Break-even Fee Aware' },
              { key: 'break_even_funding_aware', label: 'Break-even Funding Aware' },
            ]}
            objectFields={{
              tp_allocation: {
                label: 'TP Allocation (must sum to 1.0)',
                fields: [
                  { key: 'tp1', label: 'TP1 %', type: 'number', step: 0.01, min: 0, max: 1 },
                  { key: 'tp2', label: 'TP2 %', type: 'number', step: 0.01, min: 0, max: 1 },
                  { key: 'tp3', label: 'TP3 %', type: 'number', step: 0.01, min: 0, max: 1 },
                  { key: 'runner', label: 'Runner %', type: 'number', step: 0.01, min: 0, max: 1 },
                ]
              }
            }}
          />
        </TabsContent>

        {/* Leverage Tab */}
        <TabsContent value="leverage">
          <ConfigFormSection
            title="Leverage Intelligence Configuration"
            form={leverageForm}
            onChange={setLeverageForm}
            onSave={(data) => handleSave('leverage', data)}
            fields={[
              { key: 'max_leverage', label: 'Max Leverage', type: 'number', min: 1, max: 100 },
              { key: 'liquidation_buffer_pct', label: 'Liquidation Buffer (%)', type: 'number', step: 1, min: 5, max: 50 },
            ]}
            booleanFields={[
              { key: 'risk_first_sizing', label: 'Risk-First Sizing' },
              { key: 'use_exchange_maintenance_margin', label: 'Use Exchange Maintenance Margin' },
              { key: 'leverage_tiers_respected', label: 'Respect Leverage Tiers' },
            ]}
          />
        </TabsContent>

        {/* Paper Trading Tab */}
        <TabsContent value="paper">
          <ConfigFormSection
            title="Paper Trading Configuration"
            form={paperForm}
            onChange={setPaperForm}
            onSave={(data) => handleSave('paper_trading', data)}
            booleanFields={[
              { key: 'enabled', label: 'Enabled' },
            ]}
            fields={[
              { key: 'fees_bps', label: 'Fees (bps)', type: 'number', step: 1, min: 0 },
              { key: 'slippage_bps', label: 'Slippage (bps)', type: 'number', step: 1, min: 0 },
              { key: 'funding_rate_pct', label: 'Funding Rate (% per 8h)', type: 'number', step: 0.001, min: 0 },
              { key: 'partial_fill_probability', label: 'Partial Fill Probability', type: 'number', step: 0.01, min: 0, max: 1 },
              { key: 'latency_ms', label: 'Simulated Latency (ms)', type: 'number', step: 10, min: 0 },
            ]}
          />
        </TabsContent>

        {/* Telegram Tab */}
        <TabsContent value="telegram">
          <TelegramTab
            form={telegramForm}
            onChange={setTelegramForm}
            onSave={(data) => handleSave('telegram', data)}
          />
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <ConfigFormSection
            title="Notifications Configuration"
            form={notificationsForm}
            onChange={setNotificationsForm}
            onSave={(data) => handleSave('notifications', data)}
            booleanFields={[
              { key: 'telegram_enabled', label: 'Telegram Enabled' },
              { key: 'email_enabled', label: 'Email Enabled' },
              { key: 'webhook_enabled', label: 'Webhook Enabled' },
            ]}
            fields={[
              { key: 'email_address', label: 'Email Address', type: 'email' },
              { key: 'webhook_url', label: 'Webhook URL', type: 'url' },
            ]}
            arrayFields={{
              webhook_events: { label: 'Webhook Events', itemLabel: 'Event', type: 'text' },
            }}
          />
        </TabsContent>

        {/* UI Tab */}
        <TabsContent value="ui">
          <ConfigFormSection
            title="UI Configuration"
            form={uiForm}
            onChange={setUiForm}
            onSave={(data) => handleSave('ui', data)}
            fields={[
              { key: 'theme', label: 'Theme', type: 'select', options: ['light', 'dark', 'system'] },
              { key: 'auto_refresh_seconds', label: 'Auto Refresh (seconds)', type: 'number', min: 1, max: 300 },
              { key: 'chart_timezone', label: 'Chart Timezone', type: 'text' },
              { key: 'decimal_places', label: 'Decimal Places', type: 'number', min: 0, max: 8 },
            ]}
            booleanFields={[
              { key: 'show_advanced', label: 'Show Advanced Options' },
              { key: 'compact_mode', label: 'Compact Mode' },
              { key: 'sound_enabled', label: 'Sound Enabled' },
            ]}
          />
        </TabsContent>

        {/* Backup Tab */}
        <TabsContent value="backup">
          <ConfigFormSection
            title="Backup Configuration"
            form={backupForm}
            onChange={setBackupForm}
            onSave={(data) => handleSave('backup', data)}
            booleanFields={[
              { key: 'enabled', label: 'Enabled' },
              { key: 'encrypt_backups', label: 'Encrypt Backups' },
            ]}
            fields={[
              { key: 'interval_hours', label: 'Interval (hours)', type: 'number', min: 1, max: 168 },
              { key: 'retention_count', label: 'Retention Count', type: 'number', min: 1, max: 30 },
              { key: 'backup_path', label: 'Backup Path', type: 'text' },
            ]}
          />
        </TabsContent>

        {/* Advanced Tab */}
        <TabsContent value="advanced">
          <div className="space-y-6">
            {/* Version Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  Configuration Version
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <StatCard title="Version" value={version?.version || '1.0.0'} />
                <StatCard title="Schema Version" value={version?.schema_version || 1} />
                <StatCard title="Last Modified" value={version?.last_modified ? new Date(version.last_modified).toLocaleString() : 'N/A'} />
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <RotateCcw className="h-5 w-5" />
                  Configuration Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-4">
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Reset to Defaults
                  </Button>
                </DialogTrigger>
                <Button variant="outline" onClick={() => exportConfig.mutate()} disabled={exportConfig.isPending}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Config
                </Button>
                <Button variant="outline" onClick={() => setShowImportDialog(true)}>
                  <Upload className="h-4 w-4 mr-2" />
                  Import Config
                </Button>
                <Button variant="outline" onClick={() => runBackup.mutate()} disabled={runBackup.isPending}>
                  <Database className="h-4 w-4 mr-2" />
                  Run Backup Now
                </Button>
              </CardContent>
            </Card>

            {/* Reset Confirmation Dialog */}
            <Dialog open={false} onOpenChange={() => {}}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Reset Configuration</DialogTitle>
                  <DialogDescription>This will reset all configuration to default values. This action cannot be undone.</DialogDescription>
                </DialogHeader>
                <form className="space-y-4 p-4">
                  <div className="flex justify-end gap-2">
                    <Button variant="outline">Cancel</Button>
                    <Button variant="destructive" onClick={() => { resetConfig.mutate(); }}>
                      Reset Configuration
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>

            {/* Import Dialog */}
            <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Import Configuration</DialogTitle>
                  <DialogDescription>Paste encrypted configuration data and enter passphrase to import.</DialogDescription>
                </DialogHeader>
                <form className="space-y-4 p-4">
                  <div className="space-y-2">
                    <Label htmlFor="encryptedData">Encrypted Config Data</Label>
                    <textarea
                      id="encryptedData"
                      className="w-full h-40 rounded-md border border-input bg-background p-3 text-sm font-mono"
                      value={importData}
                      onChange={(e) => setImportData(e.target.value)}
                      placeholder="Paste encrypted configuration here..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="passphrase">Passphrase</Label>
                    <Input
                      id="passphrase"
                      type="password"
                      value={importPassphrase}
                      onChange={(e) => setImportPassphrase(e.target.value)}
                      placeholder="Enter decryption passphrase"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => { setShowImportDialog(false); setImportData(''); setImportPassphrase(''); }}>Cancel</Button>
                    <Button onClick={() => { importConfig.mutate({ encryptedData: importData, passphrase: importPassphrase }); setShowImportDialog(false); setImportData(''); setImportPassphrase(''); }} disabled={importConfig.isPending || !importData || !importPassphrase}>
                      {importConfig.isPending ? 'Importing...' : 'Import Configuration'}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Helper Components
function ExchangesTab({ exchanges, forms, onFormChange, onSave, onTest }: any) {
  return (
    <div className="space-y-6">
      {exchanges.map((exch: any) => {
        const form = forms[exch.name.toLowerCase()] || {};
        const isTestnet = form.testnet;

        return (
          <Card key={exch.name} className={cn(exch.enabled ? '' : 'opacity-50')}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  {exch.name === 'binance' ? <Globe className="h-5 w-5 text-yellow-500" /> : <Server className="h-5 w-5 text-blue-500" />}
                </div>
                <div>
                  <h3 className="font-semibold capitalize">{exch.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {exch.connection_status} • {exch.has_credentials ? 'Credentials configured' : 'No credentials'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={exch.enabled ? 'success' : 'secondary'}>
                  {exch.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                <Badge variant={isTestnet ? 'warning' : 'secondary'}>
                  {isTestnet ? 'Testnet' : 'Mainnet'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Connection Test */}
              <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
                <div className="flex-1">
                  <p className="font-medium">Connection Test</p>
                  <p className="text-sm text-muted-foreground">Test API connectivity and permissions</p>
                </div>
                <Button
                  onClick={() => onTest.mutate(exch.name.toLowerCase())}
                  disabled={testExchangeConnection.isPending}
                >
                  <RotateCcw className={cn("h-4 w-4 mr-2", testExchangeConnection.isPending && "animate-spin")} />
                  Test Connection
                </Button>
              </div>

              {/* Configuration Form */}
              <form className="space-y-6" onSubmit={(e) => { e.preventDefault(); onSave({ [exch.name.toLowerCase()]: form }); }}>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-enabled`}>Enabled</Label>
                    <input
                      id={`${exch.name}-enabled`}
                      type="checkbox"
                      checked={form.enabled}
                      onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], enabled: e.target.checked } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-testnet`}>Testnet Mode</Label>
                    <input
                      id={`${exch.name}-testnet`}
                      type="checkbox"
                      checked={form.testnet}
                      onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], testnet: e.target.checked } }))}
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-margin-mode`}>Margin Mode</Label>
                    <Select value={form.margin_mode} onValueChange={(v) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], margin_mode: v } }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="isolated">Isolated</SelectItem>
                        <SelectItem value="cross">Cross</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-position-mode`}>Position Mode</Label>
                    <Select value={form.position_mode} onValueChange={(v) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], position_mode: v } }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="one_way">One-Way</SelectItem>
                        <SelectItem value="hedge">Hedge</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${exch.name}-api-key`}>API Key</Label>
                  <Input
                    id={`${exch.name}-api-key`}
                    type="password"
                    value={form.api_key}
                    onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], api_key: e.target.value } }))}
                    placeholder="Enter API key"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${exch.name}-api-secret`}>API Secret</Label>
                  <Input
                    id={`${exch.name}-api-secret`}
                    type="password"
                    value={form.api_secret}
                    onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], api_secret: e.target.value } }))}
                    placeholder="Enter API secret"
                  />
                </div>

                {exch.name.toLowerCase() === 'bitget' && (
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-passphrase`}>Passphrase</Label>
                    <Input
                      id={`${exch.name}-passphrase`}
                      type="password"
                      value={form.passphrase}
                      onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], passphrase: e.target.value } }))}
                      placeholder="Enter passphrase"
                    />
                  </div>
                )}

                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-rate-limit`}>Rate Limit Buffer</Label>
                    <Input
                      id={`${exch.name}-rate-limit`}
                      type="number"
                      step="0.01"
                      min="0.1"
                      max="1"
                      value={form.rate_limit_buffer}
                      onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], rate_limit_buffer: parseFloat(e.target.value) } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`${exch.name}-recv-window`}>Receive Window (ms)</Label>
                    <Input
                      id={`${exch.name}-recv-window`}
                      type="number"
                      min="1000"
                      max="60000"
                      value={form.recv_window}
                      onChange={(e) => onFormChange(prev => ({ ...prev, [exch.name.toLowerCase()]: { ...prev[exch.name.toLowerCase()], recv_window: parseInt(e.target.value) } }))}
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button type="submit">
                    <Save className="h-4 w-4 mr-2" />
                    Save {exch.name} Config
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function TelegramTab({ form, onChange, onSave }: any) {
  return (
    <ConfigFormSection
      title="Telegram Bot Configuration"
      form={form}
      onChange={onChange}
      onSave={(data) => onSave('telegram', data)}
      fields={[
        { key: 'bot_token', label: 'Bot Token', type: 'password', placeholder: 'Enter bot token from @BotFather' },
      ]}
      booleanFields={[
        { key: 'enabled', label: 'Enabled' },
      ]}
      arrayFields={{
        allowed_users: { label: 'Allowed User IDs', itemLabel: 'User ID', type: 'number' },
        admin_users: { label: 'Admin User IDs', itemLabel: 'User ID', type: 'number' },
      }}
      objectFields={{
        notifications: {
          label: 'Notification Settings',
          fields: [
            { key: 'new_signal', label: 'New Signal', type: 'boolean' },
            { key: 'tp_triggered', label: 'TP Triggered', type: 'boolean' },
            { key: 'sl_triggered', label: 'SL Triggered', type: 'boolean' },
            { key: 'position_open', label: 'Position Open', type: 'boolean' },
            { key: 'position_close', label: 'Position Close', type: 'boolean' },
            { key: 'risk_alert', label: 'Risk Alert', type: 'boolean' },
            { key: 'daily_report', label: 'Daily Report', type: 'boolean' },
            { key: 'weekly_report', label: 'Weekly Report', type: 'boolean' },
            { key: 'system_error', label: 'System Error', type: 'boolean' },
          ]
        }}
      }}
      extraFields={[
        {
          label: 'Command Categories',
          render: () => (
            <div className="space-y-2">
              <Label>Command Categories</Label>
              <div className="grid gap-2 md:grid-cols-3">
                {[
                  'general', 'market', 'scanner', 'signals', 'paper',
                  'strategies', 'risk', 'backtest', 'portfolio', 'system', 'live'
                ].map((cat) => (
                  <label key={cat} className="flex items-center gap-2 p-2 rounded-lg bg-muted/50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.command_categories?.[cat] || false}
                      onChange={(e) => onChange(prev => ({
                        ...prev,
                        command_categories: { ...prev.command_categories, [cat]: e.target.checked }
                      }))}
                      className="h-4 w-4"
                    />
                    <span className="capitalize text-sm">{cat}</span>
                  </label>
                ))}
              </div>
            </div>
          )
        }
      ]}
    />
  );
}

function ConfigFormSection({
  title,
  form,
  onChange,
  onSave,
  fields = [],
  booleanFields = [],
  arrayFields = {},
  objectFields = {},
  extraFields = [],
}: any) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <form onSubmit={(e) => { e.preventDefault(); onSave(form); }}>
          {/* Regular Fields */}
          {fields.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {fields.map((field: any) => (
                <div key={field.key} className="space-y-2" style={field.fullWidth ? { gridColumn: '1 / -1' } : {}}>
                  <Label htmlFor={field.key}>{field.label}</Label>
                  {field.type === 'select' ? (
                    <Select value={form[field.key] || ''} onValueChange={(v) => onChange(prev => ({ ...prev, [field.key]: v }))}>
                      <SelectTrigger><SelectValue placeholder="Select..." /></SelectTrigger>
                      <SelectContent>
                        {field.options?.map((opt: string) => (
                          <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id={field.key}
                      type={field.type || 'text'}
                      step={field.step}
                      min={field.min}
                      max={field.max}
                      value={form[field.key] || ''}
                      onChange={(e) => onChange(prev => ({ ...prev, [field.key]: field.type === 'number' ? parseFloat(e.target.value) : e.target.value }))}
                      placeholder={field.placeholder}
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Boolean Fields */}
          {booleanFields.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {booleanFields.map((field: any) => (
                <label key={field.key} className="flex items-center gap-2 p-2 rounded-lg bg-muted/50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form[field.key] || false}
                    onChange={(e) => onChange(prev => ({ ...prev, [field.key]: e.target.checked }))}
                    className="h-4 w-4"
                  />
                  <span className="text-sm">{field.label}</span>
                </label>
              ))}
            </div>
          )}

          {/* Array Fields */}
          {Object.keys(arrayFields).length > 0 && (
            <div className="space-y-6">
              {Object.entries(arrayFields).map(([key, config]) => (
                <ArrayFieldEditor
                  key={key}
                  label={config.label}
                  itemLabel={config.itemLabel}
                  type={config.type}
                  value={form[key] || []}
                  onChange={(value) => onChange(prev => ({ ...prev, [key]: value }))}
                  options={config.options}
                />
              ))}
            </div>
          )}

          {/* Object Fields */}
          {Object.keys(objectFields).length > 0 && (
            <div className="space-y-6">
              {Object.entries(objectFields).map(([key, config]) => (
                <div key={key} className="p-4 rounded-lg bg-muted/50">
                  <h4 className="font-medium mb-4">{config.label}</h4>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {config.fields.map((field: any) => (
                      <div key={field.key} className="space-y-2">
                        <Label htmlFor={`${key}-${field.key}`}>{field.label}</Label>
                        {field.type === 'boolean' ? (
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={form[key]?.[field.key] || false}
                              onChange={(e) => onChange(prev => ({
                                ...prev,
                                [key]: { ...prev[key], [field.key]: e.target.checked }
                              }))}
                              className="h-4 w-4"
                            />
                            <span className="text-sm">{field.label}</span>
                          </label>
                        ) : (
                          <Input
                            id={`${key}-${field.key}`}
                            type={field.type || 'number'}
                            step={field.step}
                            min={field.min}
                            max={field.max}
                            value={form[key]?.[field.key] || ''}
                            onChange={(e) => onChange(prev => ({
                              ...prev,
                              [key]: { ...prev[key], [field.key]: field.type === 'number' ? parseFloat(e.target.value) : e.target.value }
                            }))}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Extra Custom Fields */}
          {extraFields.map((field: any) => (
            <div key={field.label} className="space-y-2">
              {field.render?.()}
            </div>
          ))}

          {/* Save Button */}
          <div className="flex justify-end pt-4 border-t">
            <Button type="submit">
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function ArrayFieldEditor({ label, itemLabel, type, value, onChange, options }: any) {
  const [items, setItems] = useState(value || []);
  const [newItem, setNewItem] = useState('');

  const addItem = () => {
    if (newItem.trim()) {
      const parsed = type === 'number' ? parseFloat(newItem) : newItem;
      if (!items.includes(parsed)) {
        setItems([...items, parsed]);
        setNewItem('');
      }
    }
  };

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  useEffect(() => {
    onChange(items);
  }, [items, onChange]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <Badge variant="secondary">{items.length} items</Badge>
      </div>

      <div className="flex gap-2">
        <Input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addItem()}
          placeholder={`Add ${itemLabel}`}
        />
        <Button variant="outline" size="sm" onClick={addItem}>Add</Button>
      </div>

      {items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {items.map((item, index) => (
            <Badge key={index} variant="secondary" className="gap-1">
              {type === 'select' && options ? options.find((o: string) => o === item) || item : item}
              <button
                onClick={() => setItems(items.filter((_, i) => i !== index))}
                className="ml-1 hover:text-red-400"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value }: any) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <p className="text-xs text-muted-foreground">{title}</p>
      <p className="text-lg font-bold font-mono mt-1">{value}</p>
    </div>
  );
}

// Need to import useEffect
import { useEffect } from 'react';
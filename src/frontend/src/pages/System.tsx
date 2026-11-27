import React, { useState } from 'react';
import { useSystemHealth, useLogs, useTelegramStatus, useLiveTradingStatus, useStorageInfo, useBackups, useAuditLogs, useSystemEvents, useDiagnostics } from '../hooks/useSystem';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import { Badge } from '../components/common/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/common/Tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/common/Dialog';
import { Input } from '../components/common/Input';
import { Label } from '../components/common/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/common/Select';
import { cn } from '../utils/cn';
import {
  Activity, Server, Database, HardDrive, MemoryStick, Wifi, WifiOff,
  MessageSquare, Shield, Zap, AlertTriangle, Info, RotateCcw,
  Download, Upload, Trash2, Search, Filter, ChevronDown
} from 'lucide-react';

export function SystemPage() {
  const { data: health } = useSystemHealth();
  const { data: logs, isLoading: logsLoading } = useLogs();
  const { data: telegram } = useTelegramStatus();
  const { data: liveStatus } = useLiveTradingStatus();
  const { data: storage } = useStorageInfo();
  const { data: backups } = useBackups();
  const { data: auditLogs } = useAuditLogs();
  const { data: events } = useSystemEvents();
  const runDiagnostics = useDiagnostics();

  const [activeTab, setActiveTab] = useState<'health' | 'logs' | 'telegram' | 'live' | 'storage' | 'backup' | 'audit' | 'events'>('health');
  const [logFilters, setLogFilters] = useState({ level: '', service: '', search: '' });
  const [newBackupDesc, setNewBackupDesc] = useState('');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">System Administration</h1>
          <p className="text-muted-foreground">Monitor and manage system health, logs, and configuration</p>
        </div>
        <Button onClick={() => runDiagnostics.mutate()} disabled={runDiagnostics.isPending}>
          <RotateCcw className={cn("h-4 w-4 mr-2", runDiagnostics.isPending && "animate-spin")} />
          Run Diagnostics
        </Button>
      </div>

      {/* System Status Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatusCard
          title="Overall Status"
          value={health?.overall_status || 'unknown'}
          icon={health?.overall_status === 'healthy' ? <Activity className="h-5 w-5 text-green-400" /> : <AlertTriangle className="h-5 w-5 text-yellow-400" />}
          className={health?.overall_status === 'healthy' ? 'border-green-500/20' : 'border-yellow-500/20'}
        />
        <StatusCard
          title="Uptime"
          value={formatUptime(health?.uptime_seconds || 0)}
          icon={<Server className="h-5 w-5 text-blue-400" />}
        />
        <StatusCard
          title="Version"
          value={health?.version || '1.0.0'}
          icon={<Info className="h-5 w-5 text-purple-400" />}
        />
        <StatusCard
          title="Exchange Connections"
          value={`${Object.values(health?.exchange_connections || {}).filter(v => v === 'connected').length} / ${Object.keys(health?.exchange_connections || {}).length}`}
          icon={<Wifi className="h-5 w-5 text-green-400" />}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="health" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 md:grid-cols-8">
          <TabsTrigger value="health">Health</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="telegram">Telegram</TabsTrigger>
          <TabsTrigger value="live">Live Trading</TabsTrigger>
          <TabsTrigger value="storage">Storage</TabsTrigger>
          <TabsTrigger value="backup">Backup</TabsTrigger>
          <TabsTrigger value="audit">Audit Logs</TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
        </TabsList>

        {/* Health Tab */}
        <TabsContent value="health">
          <div className="grid gap-6">
            {/* Services */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Services
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ServiceStatusTable services={health?.services || {}} />
              </CardContent>
            </Card>

            {/* System Resources */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Database
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <StatRow label="Status" value={health?.database?.status || 'unknown'} />
                  <StatRow label="Size" value={`${health?.database?.size_mb || 0} MB`} />
                  <StatRow label="Tables" value={health?.database?.tables || 0} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <HardDrive className="h-5 w-5" />
                    Disk Usage
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <StatRow label="Total" value={`${health?.disk_usage?.total_gb || 0} GB`} />
                  <StatRow label="Used" value={`${health?.disk_usage?.used_gb || 0} GB`} />
                  <StatRow label="Free" value={`${health?.disk_usage?.free_gb || 0} GB`} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MemoryStick className="h-5 w-5" />
                    Memory
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <StatRow label="Total" value={`${health?.memory_usage?.total_mb || 0} MB`} />
                  <StatRow label="Used" value={`${health?.memory_usage?.used_mb || 0} MB`} />
                  <StatRow label="Available" value={`${health?.memory_usage?.available_mb || 0} MB`} />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>System Logs</CardTitle>
              <div className="flex items-center gap-2">
                <Select value={logFilters.level} onValueChange={(v) => setLogFilters(prev => ({ ...prev, level: v }))}>
                  <SelectTrigger className="w-[140px]"><SelectValue placeholder="All Levels" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All</SelectItem>
                    <SelectItem value="DEBUG">DEBUG</SelectItem>
                    <SelectItem value="INFO">INFO</SelectItem>
                    <SelectItem value="WARNING">WARNING</SelectItem>
                    <SelectItem value="ERROR">ERROR</SelectItem>
                    <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={logFilters.service} onValueChange={(v) => setLogFilters(prev => ({ ...prev, service: v }))}>
                  <SelectTrigger className="w-[160px]"><SelectValue placeholder="All Services" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All</SelectItem>
                    <SelectItem value="market_data">Market Data</SelectItem>
                    <SelectItem value="strategy_engine">Strategy Engine</SelectItem>
                    <SelectItem value="risk_engine">Risk Engine</SelectItem>
                    <SelectItem value="execution">Execution</SelectItem>
                    <SelectItem value="tp_sl">TP/SL</SelectItem>
                    <SelectItem value="pnl">PnL</SelectItem>
                    <SelectItem value="telegram">Telegram</SelectItem>
                  </SelectContent>
                </Select>
                <Input placeholder="Search..." value={logFilters.search} onChange={(e) => setLogFilters(prev => ({ ...prev, search: e.target.value }))} className="w-64" />
              </div>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
              ) : (
                <LogTable logs={logs?.logs || []} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Telegram Tab */}
        <TabsContent value="telegram">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Bot Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <StatRow label="Enabled" value={telegram?.enabled ? 'Yes' : 'No'} />
                <StatRow label="Connected" value={telegram?.connected ? 'Yes' : 'No'} className={telegram?.connected ? 'text-green-400' : 'text-red-400'} />
                <StatRow label="Bot Username" value={telegram?.bot_username || 'N/A'} />
                <StatRow label="Bot ID" value={telegram?.bot_id || 'N/A'} />
                <StatRow label="Allowed Users" value={telegram?.allowed_users || 0} />
                <StatRow label="Admin Users" value={telegram?.admin_users || 0} />
                <StatRow label="Pending Commands" value={telegram?.pending_commands || 0} />
                <StatRow label="Last Message" value={telegram?.last_message_at ? new Date(telegram.last_message_at).toLocaleString() : 'Never'} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Command History</CardTitle>
                <Button variant="outline" size="sm" onClick={() => {}}>
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </CardHeader>
              <CardContent>
                <LogTable logs={[]} /> {/* Would use telegram command logs */}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Live Trading Tab */}
        <TabsContent value="live">
          <div className="space-y-6">
            {/* Status */}
            <Card className={cn(liveStatus?.state === 'live_active' ? 'border-red-500/20' : 'border-green-500/20')}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Live Trading Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <StatCard
                    title="State"
                    value={liveStatus?.state?.replace('_', ' ').toUpperCase() || 'PAPER'}
                    className={liveStatus?.state === 'live_active' ? 'text-red-400' : 'text-green-400'}
                  />
                  <StatCard title="Live Credentials" value={liveStatus?.live_credentials_configured ? 'Configured' : 'Not Configured'} />
                  <StatCard title="Paper Trades" value={liveStatus?.paper_trades_count || 0} />
                  <StatCard title="Paper Days" value={liveStatus?.paper_days_active || 0} />
                </div>

                {/* Eligibility Checks */}
                <div className="mt-6">
                  <h4 className="font-medium mb-3">Eligibility Checks</h4>
                  <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
                    {Object.entries(liveStatus?.eligibility_checks || {}).map(([key, passed]) => (
                      <EligibilityCheck key={key} name={formatCheckName(key)} passed={passed} />
                    ))}
                  </div>
                </div>

                {/* Critical Issues */}
                {liveStatus?.critical_issues && liveStatus.critical_issues.length > 0 && (
                  <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                    <h4 className="font-medium text-red-400 mb-2">Critical Issues</h4>
                    <ul className="list-disc list-inside space-y-1 text-red-300">
                      {liveStatus.critical_issues.map((issue, i) => <li key={i}>{issue}</li>)}
                    </ul>
                  </div>
                )}

                {/* Actions */}
                <div className="mt-6 flex gap-2">
                  <DialogTrigger asChild>
                    <Button variant={liveStatus?.state === 'paper' ? 'default' : 'outline'} onClick={() => {}}>
                      {liveStatus?.state === 'paper' ? 'Arm Live Mode' : 'Disarm'}
                    </Button>
                  </DialogTrigger>
                  <Button variant="destructive" onClick={() => {}}>
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    Emergency Stop
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Dialog for confirmation would go here */}
          </div>
        </TabsContent>

        {/* Storage Tab */}
        <TabsContent value="storage">
          <div className="grid gap-6 lg:grid-cols-4">
            <StatCard title="Total Space" value={`${storage?.total_bytes ? (storage.total_bytes / 1e9).toFixed(1) : 0} GB`} icon={<HardDrive className="h-5 w-5" />} />
            <StatCard title="Used" value={`${storage?.used_bytes ? (storage.used_bytes / 1e9).toFixed(1) : 0} GB`} icon={<HardDrive className="h-5 w-5" />} />
            <StatCard title="Free" value={`${storage?.free_bytes ? (storage.free_bytes / 1e9).toFixed(1) : 0} GB`} icon={<HardDrive className="h-5 w-5 text-green-400" />} />
            <StatCard title="Usage" value={`${storage?.usage_pct || 0}%`} icon={<AlertTriangle className="h-5 w-5" />} className={storage?.usage_pct && storage.usage_pct > 80 ? 'text-red-400' : ''} />
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StorageCard label="Database" value={storage?.database_size_bytes ? formatBytes(storage.database_size_bytes) : '0 B'} />
            <StorageCard label="Logs" value={storage?.logs_size_bytes ? formatBytes(storage.logs_size_bytes) : '0 B'} />
            <StorageCard label="Backups" value={storage?.backups_size_bytes ? formatBytes(storage.backups_size_bytes) : '0 B'} />
            <StorageCard label="Market Data" value={storage?.market_data_size_bytes ? formatBytes(storage.market_data_size_bytes) : '0 B'} />
          </div>
        </TabsContent>

        {/* Backup Tab */}
        <TabsContent value="backup">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <h2 className="text-xl font-bold">Backups</h2>
            <DialogTrigger asChild>
              <Button variant="outline" onClick={() => setNewBackupDesc('')}>
                <Download className="h-4 w-4 mr-2" />
                Create Backup
              </Button>
            </DialogTrigger>
          </div>

          <Card>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {backups?.map((backup) => (
                    <TableRow key={backup.filename}>
                      <TableCell className="font-mono">{backup.filename}</TableCell>
                      <TableCell>{formatBytes(backup.size_bytes)}</TableCell>
                      <TableCell>{new Date(backup.created_at).toLocaleString()}</TableCell>
                      <TableCell>
                        <Badge variant={backup.type === 'auto' ? 'secondary' : 'success'}>{backup.type}</Badge>
                      </TableCell>
                      <TableCell>{backup.description || '-'}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8"><Download className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-400 hover:text-red-300"><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Create Backup Dialog */}
          <Dialog open={false} onOpenChange={() => {}}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Backup</DialogTitle>
              </DialogHeader>
              <form className="space-y-4 p-4">
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Input id="description" placeholder="Pre-update backup" />
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline">Cancel</Button>
                  <Button>Create Backup</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </TabsContent>

        {/* Audit Logs Tab */}
        <TabsContent value="audit">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Audit Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <AuditLogTable logs={auditLogs || []} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Events Tab */}
        <TabsContent value="events">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>System Events</CardTitle>
            </CardHeader>
            <CardContent>
              <EventTable events={events || []} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Helper Components
function StatusCard({ title, value, icon, className }: any) {
  return (
    <Card className={cn('relative', className)}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold font-mono mt-1">{value}</p>
          </div>
          <div className="p-2 bg-primary/10 rounded-lg">{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function ServiceStatusTable({ services }: any) {
  const entries = Object.entries(services || {});
  return (
    <div className="space-y-2">
      {entries.map(([name, status]) => (
        <div key={name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
          <span className="font-medium capitalize">{name.replace(/_/g, ' ')}</span>
          <Badge variant={
            status === 'running' ? 'success' :
            status === 'stopped' ? 'secondary' : 'destructive'
          }>
            {String(status)}
          </Badge>
        </div>
      ))}
    </div>
  );
}

function StatRow({ label, value, className }: any) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn('font-mono font-medium', className)}>{value}</span>
    </div>
  );
}

function LogTable({ logs }: any) {
  if (!logs.length) return <div className="text-center py-8 text-muted-foreground">No logs</div>;
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Level</TableHead>
            <TableHead>Service</TableHead>
            <TableHead>Component</TableHead>
            <TableHead>Exchange</TableHead>
            <TableHead>Message</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.slice(0, 100).map((log: any, i: number) => (
            <TableRow key={i} className={cn(
              log.level === 'ERROR' || log.level === 'CRITICAL' ? 'bg-red-500/5' : ''
            )}>
              <TableCell className="font-mono text-xs">{new Date(log.timestamp).toLocaleTimeString()}</TableCell>
              <TableCell>
                <Badge variant={
                  log.level === 'DEBUG' ? 'secondary' :
                  log.level === 'INFO' ? 'success' :
                  log.level === 'WARNING' ? 'warning' : 'destructive'
                }>{log.level}</Badge>
              </TableCell>
              <TableCell className="text-xs">{log.service}</TableCell>
              <TableCell className="text-xs">{log.component || '-'}</TableCell>
              <TableCell className="text-xs">{log.exchange || '-'}</TableCell>
              <TableCell className="max-w-[400px] truncate">{log.message}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AuditLogTable({ logs }: any) {
  if (!logs.length) return <div className="text-center py-8 text-muted-foreground">No audit logs</div>;
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Resource</TableHead>
            <TableHead>Success</TableHead>
            <TableHead>IP</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.slice(0, 100).map((log: any, i: number) => (
            <TableRow key={i}>
              <TableCell className="font-mono text-xs">{new Date(log.timestamp).toLocaleString()}</TableCell>
              <TableCell>{log.user_id || 'system'}</TableCell>
              <TableCell>{log.action}</TableCell>
              <TableCell>{log.resource_type || '-'}:{log.resource_id || '-'}</TableCell>
              <TableCell>
                <Badge variant={log.success ? 'success' : 'destructive'}>
                  {log.success ? 'Success' : 'Failed'}
                </Badge>
              </TableCell>
              <TableCell className="font-mono text-xs">{log.ip_address || '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function EventTable({ events }: any) {
  if (!events.length) return <div className="text-center py-8 text-muted-foreground">No system events</div>;
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Message</TableHead>
            <TableHead>Resolved</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {events.slice(0, 100).map((event: any, i: number) => (
            <TableRow key={i}>
              <TableCell className="font-mono text-xs">{new Date(event.created_at).toLocaleString()}</TableCell>
              <TableCell>{event.event_type}</TableCell>
              <TableCell>
                <Badge variant={
                  event.severity === 'INFO' ? 'success' :
                  event.severity === 'WARNING' ? 'warning' : 'destructive'
                }>{event.severity}</Badge>
              </TableCell>
              <TableCell className="max-w-[400px] truncate">{event.message}</TableCell>
              <TableCell>
                <Badge variant={event.is_resolved ? 'success' : 'warning'}>
                  {event.is_resolved ? 'Yes' : 'No'}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function EligibilityCheck({ name, passed }: any) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
      <span className="text-sm">{name}</span>
      <Badge variant={passed ? 'success' : 'destructive'}>{passed ? 'PASS' : 'FAIL'}</Badge>
    </div>
  );
}

function StatCard({ title, value, className, icon }: any) {
  return (
    <Card className={cn('relative', className)}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold font-mono mt-1">{value}</p>
          </div>
          {icon && <div className="p-2 bg-primary/10 rounded-lg">{icon}</div>}
        </div>
      </CardContent>
    </Card>
  );
}

function StorageCard({ label, value }: any) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold font-mono mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${mins}m`;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatCheckName(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}

// Need hooks

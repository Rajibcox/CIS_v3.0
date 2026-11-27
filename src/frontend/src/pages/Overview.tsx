import React from 'react';
import { useDashboardOverview, useQuickStats, useEquityCurve, useOpenPositions } from '../hooks/useDashboard';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';
import {
  DollarSign, TrendingUp, TrendingDown, AlertTriangle,
  Shield, Zap, Activity, MoreHorizontal
} from 'lucide-react';
import { cn } from '../utils/cn';
import type { DashboardOverview, PositionSummary, EquityCurvePoint } from '../types/api';

export function OverviewPage() {
  const { data: overview, isLoading: overviewLoading } = useDashboardOverview();
  const { data: quickStats } = useQuickStats();
  const { data: equityCurve } = useEquityCurve(30);
  const { data: positions } = useOpenPositions();

  // Use quickStats if available, fallback to overview
  const stats = quickStats || overview;

  const formatCurrency = (value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const formatPct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  const getPnlColor = (value: number) => value >= 0 ? 'text-green-400' : 'text-red-400';
  const getPnlBg = (value: number) => value >= 0 ? 'bg-green-500/10' : 'bg-red-500/10';

  if (overviewLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Portfolio overview and system status</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <MoreHorizontal className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button size="sm">
            <Activity className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Equity"
          value={formatCurrency(overview?.total_equity || 0)}
          icon={<DollarSign className="h-5 w-5 text-green-400" />}
          change={overview?.daily_pnl_pct}
          changeLabel="Daily P&L"
        />
        <MetricCard
          title="Available Balance"
          value={formatCurrency(overview?.available_balance || 0)}
          icon={<Shield className="h-5 w-5 text-blue-400" />}
          subtitle={`${overview?.max_positions || 2} max positions`}
        />
        <MetricCard
          title="Daily P&L"
          value={formatCurrency(overview?.daily_pnl || 0)}
          icon={<TrendingUp className="h-5 w-5" />}
          className={cn(getPnlColor(overview?.daily_pnl || 0))}
          change={overview?.daily_pnl_pct}
          changeLabel="vs yesterday"
        />
        <MetricCard
          title="Drawdown"
          value={formatPct(overview?.drawdown_pct || 0)}
          icon={<AlertTriangle className="h-5 w-5 text-yellow-400" />}
          subtitle={`Peak: ${formatCurrency(overview?.peak_equity || 0)}`}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Equity Curve - Full Width on top */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Equity Curve (30 Days)</CardTitle>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 bg-primary" />
                Equity
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 bg-red-400" />
                Drawdown
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {equityCurve?.data && equityCurve.data.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityCurve.data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tickFormatter={(value) => new Date(value).toLocaleDateString()} stroke="hsl(var(--muted-foreground))" fontSize={11} />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickFormatter={(value) => formatCurrency(value)} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                      formatter={(value: number) => [formatCurrency(value), 'Equity']}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="hsl(var(--primary))"
                      fillOpacity={1}
                      fill="url(#colorEquity)"
                    />
                    <Area
                      type="monotone"
                      dataKey="drawdown"
                      stroke="hsl(var(--destructive))"
                      fillOpacity={1}
                      fill="url(#colorDrawdown)"
                      yAxisId="right"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  No equity data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* System Status - Right Column */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-green-400" />
              System Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <StatusItem label="Market Data" status="running" details="150 symbols tracked" />
            <StatusItem label="Strategy Engine" status="running" details="3 active strategies" />
            <StatusItem label="Risk Engine" status="running" details="100 checks/sec" />
            <StatusItem label="Execution Engine" status="running" details="0 pending orders" />
            <StatusItem label="TP/SL Manager" status="running" details="5 active stages" />
            <StatusItem label="PnL Analytics" status="running" details="3 trades today" />
            <StatusItem label="Telegram Bot" status="stopped" details="Not configured" />
          </CardContent>
        </Card>

        {/* Open Positions - Bottom Left */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Open Positions</CardTitle>
            <Button variant="ghost" size="sm">View All</Button>
          </CardHeader>
          <CardContent>
            {positions && positions.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Exchange</TableHead>
                      <TableHead className="text-right">Direction</TableHead>
                      <TableHead className="text-right">Entry</TableHead>
                      <TableHead className="text-right">Current</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">P&L</TableHead>
                      <TableHead className="text-right">Leverage</TableHead>
                      <TableHead className="text-right">Margin</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positions.map((pos: PositionSummary) => (
                      <TableRow key={pos.symbol}>
                        <TableCell className="font-mono font-medium">{pos.symbol}</TableCell>
                        <TableCell>{pos.exchange}</TableCell>
                        <TableCell className="text-right">
                          <span className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                            pos.direction === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                          )}>
                            {pos.direction}
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">{pos.entry_price.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{pos.current_price.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{pos.quantity}</TableCell>
                        <TableCell className={cn("text-right font-mono font-medium", getPnlColor(pos.unrealized_pnl))}>
                          {formatCurrency(pos.unrealized_pnl)}
                        </TableCell>
                        <TableCell className="text-right font-mono">{pos.leverage}x</TableCell>
                        <TableCell className="text-right font-mono">{formatCurrency(pos.margin_used)}</TableCell>
                        <TableCell>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Zap className="h-12 w-12 text-muted-foreground/50 mb-4" />
                <h3 className="text-lg font-medium">No Open Positions</h3>
                <p className="text-muted-foreground mt-1">
                  Positions will appear here when you execute trades from signals
                </p>
                <Button className="mt-4" onClick={() => window.location.href = '/signals'}>
                  View Signals
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Performance Summary - Bottom Right */}
        <Card>
          <CardHeader>
            <CardTitle>30-Day Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <StatRow label="Win Rate" value={`${overview?.win_rate_30d || 0}%`} />
            <StatRow label="Profit Factor" value={overview?.profit_factor_30d?.toFixed(2) || '0.00'} />
            <StatRow label="Expectancy" value={formatCurrency(overview?.expectancy_30d || 0)} />
            <StatRow label="Sharpe Ratio" value={overview?.sharpe_30d?.toFixed(2) || 'N/A'} />
            <StatRow label="Max Drawdown" value={`${overview?.max_drawdown_30d || 0}%`} className="text-red-400" />
            <StatRow label="Total Trades" value={overview?.open_positions_count?.toString() || '0'} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Helper Components
function MetricCard({
  title,
  value,
  icon,
  change,
  changeLabel,
  subtitle,
  className,
  children,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  change?: number;
  changeLabel?: string;
  subtitle?: string;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <Card className={cn('relative', className)}>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold font-mono mt-1">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className="p-2 bg-primary/10 rounded-lg">{icon}</div>
        </div>
        {change !== undefined && (
          <div className="mt-3 flex items-center gap-1">
            <span className={cn(
              'text-sm font-medium',
              change >= 0 ? 'text-green-400' : 'text-red-400'
            )}>
              {change >= 0 ? '+' : ''}{change.toFixed(2)}%
            </span>
            <span className="text-xs text-muted-foreground">{changeLabel}</span>
          </div>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

function StatusItem({
  label,
  status,
  details,
}: {
  label: string;
  status: 'running' | 'stopped' | 'error' | 'warning';
  details: string;
}) {
  const statusConfig = {
    running: { color: 'text-green-400', bg: 'bg-green-500/10', label: 'RUNNING' },
    stopped: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'STOPPED' },
    error: { color: 'text-red-400', bg: 'bg-red-500/10', label: 'ERROR' },
    warning: { color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'WARNING' },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">{details}</p>
      </div>
      <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', config.bg, config.color)}>
        {config.label}
      </span>
    </div>
  );
}

function StatRow({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn('font-mono font-medium', className)}>{value}</span>
    </div>
  );
}
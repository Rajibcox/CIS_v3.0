import React, { useState } from 'react';
import {
  usePnLSummary,
  usePerformanceMetrics,
  useEquityCurve,
  useMonthlyReturns,
  useStrategyBreakdown,
  useSymbolBreakdown,
  useDirectionBreakdown,
  useTimeframeBreakdown,
  useRegimeBreakdown,
  useTpAnalytics,
  useTradeDistribution,
  useBacktest,
  useWalkforward,
  useMonteCarlo,
} from '../hooks/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/common/Tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/common/Select';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  ScatterChart, Scatter
} from 'recharts';
import {
  DollarSign, TrendingUp, TrendingDown, CheckCircle, AlertTriangle,
  Settings, FlaskConical, Download, Upload
} from 'lucide-react';
import { cn } from '../utils/cn';
import { formatCurrency, formatPct } from '../utils/format';

export function AnalyticsPage() {
  const [period, setPeriod] = useState(30);

  const { data: pnlSummary } = usePnLSummary(period);
  const { data: metrics } = usePerformanceMetrics(period);
  const { data: equityCurve } = useEquityCurve(period);
  const { data: monthlyReturns } = useMonthlyReturns(1);
  const { data: strategyBreakdown } = useStrategyBreakdown(period);
  const { data: symbolBreakdown } = useSymbolBreakdown(period);
  const { data: directionBreakdown } = useDirectionBreakdown(period);
  const { data: timeframeBreakdown } = useTimeframeBreakdown(period);
  const { data: regimeBreakdown } = useRegimeBreakdown(period);
  const { data: tpAnalytics } = useTpAnalytics(period);
  const { data: tradeDistribution } = useTradeDistribution(period);

  const runBacktest = useBacktest();
  const runWalkforward = useWalkforward();
  const runMonteCarlo = useMonteCarlo();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">Performance analysis and research tools</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={period.toString()} onValueChange={(v) => setPeriod(parseInt(v))}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 Days</SelectItem>
              <SelectItem value="30">30 Days</SelectItem>
              <SelectItem value="90">90 Days</SelectItem>
              <SelectItem value="180">180 Days</SelectItem>
              <SelectItem value="365">1 Year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" size="sm">
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4 lg:grid-cols-6">
        <MetricCard title="Net P&L" value={formatCurrency(pnlSummary?.net_pnl || 0)} icon={<DollarSign className="h-5 w-5 text-green-400" />} change={pnlSummary?.net_pnl} changeLabel="Period" />
        <MetricCard title="Win Rate" value={formatPct(pnlSummary?.win_rate || 0)} icon={<CheckCircle className="h-5 w-5 text-blue-400" />} />
        <MetricCard title="Profit Factor" value={(pnlSummary?.profit_factor || 0).toFixed(2)} icon={<TrendingUp className="h-5 w-5 text-green-400" />} />
        <MetricCard title="Expectancy" value={formatCurrency(pnlSummary?.expectancy || 0)} icon={<TrendingUp className="h-5 w-5 text-purple-400" />} />
        <MetricCard title="Max DD" value={formatPct(pnlSummary?.max_drawdown || 0)} icon={<AlertTriangle className="h-5 w-5 text-red-400" />} className="text-red-400" />
        <MetricCard title="Sharpe" value={metrics?.sharpe_ratio?.toFixed(2) || 'N/A'} icon={<TrendingUp className="h-5 w-5 text-yellow-400" />} />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 md:grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="pnl">P&L Analysis</TabsTrigger>
          <TabsTrigger value="breakdown">Breakdowns</TabsTrigger>
          <TabsTrigger value="tp">TP Analytics</TabsTrigger>
          <TabsTrigger value="distribution">Distributions</TabsTrigger>
          <TabsTrigger value="research">Research</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Equity Curve */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Equity Curve</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  {equityCurve?.data && equityCurve.data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={equityCurve.data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="date" tickFormatter={(value) => new Date(value).toLocaleDateString()} stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickFormatter={(value) => formatCurrency(value)} />
                        <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }} formatter={(value: number) => [formatCurrency(value), 'Equity']} />
                        <Area type="monotone" dataKey="equity" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorEquity)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">No equity data available</div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Monthly Returns */}
            <Card>
              <CardHeader>
                <CardTitle>Monthly Returns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  {monthlyReturns?.data && monthlyReturns.data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={monthlyReturns.data.reverse()} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="month" tickFormatter={(value) => `${value.year}-${String(value.month).padStart(2, '0')}`} stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickFormatter={(value) => formatPct(value)} />
                        <Tooltip formatter={(value: number) => [formatPct(value), 'Return']} />
                        <Bar dataKey="return_pct" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">No monthly data</div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Performance Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <StatRow label="Total Return" value={formatPct(metrics?.total_return_pct || 0)} />
                <StatRow label="Annualized Return" value={formatPct(metrics?.annualized_return_pct || 0)} />
                <StatRow label="Volatility" value={formatPct(metrics?.volatility_pct || 0)} />
                <StatRow label="Sharpe Ratio" value={metrics?.sharpe_ratio?.toFixed(2) || 'N/A'} />
                <StatRow label="Sortino Ratio" value={metrics?.sortino_ratio?.toFixed(2) || 'N/A'} />
                <StatRow label="Calmar Ratio" value={metrics?.calmar_ratio?.toFixed(2) || 'N/A'} />
                <StatRow label="Max Drawdown" value={formatPct(metrics?.max_drawdown_pct || 0)} className="text-red-400" />
                <StatRow label="Avg Drawdown" value={formatPct(metrics?.avg_drawdown_pct || 0)} />
                <StatRow label="Max DD Duration" value={`${metrics?.max_drawdown_duration_days || 0} days`} />
                <StatRow label="Current DD" value={formatPct(metrics?.current_drawdown_pct || 0)} />
              </CardContent>
            </Card>

            {/* Trade Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Trade Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <StatRow label="Total Trades" value={pnlSummary?.total_trades || 0} />
                <StatRow label="Winning" value={pnlSummary?.winning_trades || 0} className="text-green-400" />
                <StatRow label="Losing" value={pnlSummary?.losing_trades || 0} className="text-red-400" />
                <StatRow label="Avg Win" value={formatCurrency(metrics?.avg_win || 0)} className="text-green-400" />
                <StatRow label="Avg Loss" value={formatCurrency(metrics?.avg_loss || 0)} className="text-red-400" />
                <StatRow label="Avg R-Multiple" value={metrics?.avg_r_multiple?.toFixed(2) || '0.00'} />
                <StatRow label="Largest Win" value={formatCurrency(metrics?.largest_win || 0)} className="text-green-400" />
                <StatRow label="Largest Loss" value={formatCurrency(metrics?.largest_loss || 0)} className="text-red-400" />
                <StatRow label="Consecutive Wins" value={metrics?.consecutive_wins || 0} />
                <StatRow label="Consecutive Losses" value={metrics?.consecutive_losses || 0} className="text-red-400" />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* P&L Tab */}
        <TabsContent value="pnl">
          <div className="grid gap-6">
            <div className="grid gap-4 md:grid-cols-4">
              <MetricCard title="Gross P&L" value={formatCurrency(pnlSummary?.gross_pnl || 0)} icon={<DollarSign className="h-5 w-5" />} />
              <MetricCard title="Total Fees" value={formatCurrency(pnlSummary?.total_fees || 0)} icon={<AlertTriangle className="h-5 w-5 text-yellow-400" />} className="text-yellow-400" />
              <MetricCard title="Total Funding" value={formatCurrency(pnlSummary?.total_funding || 0)} icon={<TrendingDown className="h-5 w-5 text-orange-400" />} className="text-orange-400" />
              <MetricCard title="Net P&L" value={formatCurrency(pnlSummary?.net_pnl || 0)} icon={<DollarSign className="h-5 w-5 text-green-400" />} change={pnlSummary?.net_pnl} changeLabel="Net" />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Exit Reason Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ExitReasonChart data={pnlSummary?.by_exit_reason || {}} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>TP Stage Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <TpStageChart data={pnlSummary?.by_tp_stage || {}} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Breakdowns Tab */}
        <TabsContent value="breakdown">
          <div className="grid gap-6 lg:grid-cols-2">
            <BreakdownCard title="By Strategy" data={strategyBreakdown?.data || []} keyField="category" />
            <BreakdownCard title="By Symbol" data={symbolBreakdown?.data || []} keyField="category" />
            <BreakdownCard title="By Direction" data={directionBreakdown?.data || []} keyField="category" />
            <BreakdownCard title="By Timeframe" data={timeframeBreakdown?.data || []} keyField="category" />
            <BreakdownCard title="By Regime" data={regimeBreakdown?.data || []} keyField="category" />
          </div>
        </TabsContent>

        {/* TP Analytics Tab */}
        <TabsContent value="tp">
          <div className="grid gap-6">
            <div className="grid gap-4 md:grid-cols-4">
              <MetricCard title="TP1 Hit Rate" value={formatPct(tpAnalytics?.tp1_hit_rate || 0)} icon={<CheckCircle className="h-5 w-5 text-green-400" />} />
              <MetricCard title="TP2 Hit Rate" value={formatPct(tpAnalytics?.tp2_hit_rate || 0)} icon={<CheckCircle className="h-5 w-5 text-blue-400" />} />
              <MetricCard title="TP3 Hit Rate" value={formatPct(tpAnalytics?.tp3_hit_rate || 0)} icon={<CheckCircle className="h-5 w-5 text-blue-400" />} />
              <MetricCard title="Runner Hit Rate" value={formatPct(tpAnalytics?.runner_hit_rate || 0)} icon={<TrendingUp className="h-5 w-5 text-purple-400" />} />
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <MetricCard title="Profit Captured TP1" value={formatPct(tpAnalytics?.profit_captured_tp1_pct || 0)} icon={<DollarSign className="h-5 w-5" />} />
              <MetricCard title="Profit Captured TP2" value={formatPct(tpAnalytics?.profit_captured_tp2_pct || 0)} icon={<DollarSign className="h-5 w-5" />} />
              <MetricCard title="Profit Captured TP3" value={formatPct(tpAnalytics?.profit_captured_tp3_pct || 0)} icon={<DollarSign className="h-5 w-5" />} />
              <MetricCard title="Given Back After TP3" value={formatPct(tpAnalytics?.profit_given_back_after_tp3_pct || 0)} icon={<AlertTriangle className="h-5 w-5 text-red-400" />} className="text-red-400" />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <MetricCard title="Stop Out After TP1" value={formatPct(tpAnalytics?.stop_out_after_tp1_rate || 0)} icon={<AlertTriangle className="h-5 w-5 text-red-400" />} className="text-red-400" />
              <MetricCard title="Stop Out After TP2" value={formatPct(tpAnalytics?.stop_out_after_tp2_rate || 0)} icon={<AlertTriangle className="h-5 w-5 text-red-400" />} className="text-red-400" />
              <MetricCard title="Stop Out After TP3" value={formatPct(tpAnalytics?.stop_out_after_tp3_rate || 0)} icon={<AlertTriangle className="h-5 w-5 text-red-400" />} className="text-red-400" />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Avg R-Multiple by Stage</CardTitle>
              </CardHeader>
              <CardContent>
                <RMultipleChart data={tpAnalytics?.avg_r_multiple_by_stage || {}} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Distribution Tab */}
        <TabsContent value="distribution">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>R-Multiple Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  {tradeDistribution?.r_multiples && tradeDistribution.r_multiples.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={createHistogram(tradeDistribution.r_multiples, 20)} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="range" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <Tooltip formatter={(value: number) => [value, 'Count']} />
                        <Bar dataKey="count" fill="hsl(var(--primary))" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">No distribution data</div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Hold Time Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  {tradeDistribution?.hold_times_hours && tradeDistribution.hold_times_hours.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={createHistogram(tradeDistribution.hold_times_hours, 15)} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="range" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <Tooltip formatter={(value: number) => [value, 'Trades']} />
                        <Bar dataKey="count" fill="hsl(var(--primary))" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">No distribution data</div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>MAE / MFE Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="mae" stroke="hsl(var(--muted-foreground))" fontSize={11} tickFormatter={(v) => formatPct(v)} />
                      <YAxis dataKey="mfe" stroke="hsl(var(--muted-foreground))" fontSize={11} tickFormatter={(v) => formatPct(v)} />
                      <Tooltip formatter={(value: number, name: string) => [formatPct(value), name === 'mae' ? 'MAE' : 'MFE']} />
                      <Scatter
                        name="Trades"
                        data={tradeDistribution?.mae_pct && tradeDistribution?.mfe_pct ? tradeDistribution.mae_pct.map((mae, i) => ({ mae, mfe: tradeDistribution.mfe_pct[i] })) : []}
                        fill="hsl(var(--primary))"
                        stroke="hsl(var(--primary))"
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Research Tab */}
        <TabsContent value="research">
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold">Research Tools</h2>
                <p className="text-muted-foreground">Backtesting, walk-forward analysis, and Monte Carlo simulation</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <ResearchCard
                title="Backtesting"
                description="Run historical backtests with realistic execution assumptions"
                icon={<FlaskConical className="h-8 w-8 text-blue-400" />}
                onRun={() => runBacktest.mutate({ strategy_id: 1, symbols: ['BTCUSDT', 'ETHUSDT'], start_date: '2026-01-01', end_date: '2026-11-26' })}
                isLoading={runBacktest.isPending}
              />
              <ResearchCard
                title="Walk-Forward Analysis"
                description="Validate strategy robustness with rolling in-sample/out-of-sample windows"
                icon={<Settings className="h-8 w-8 text-green-400" />}
                onRun={() => runWalkforward.mutate({ strategy_id: 1, symbols: ['BTCUSDT'], start_date: '2026-01-01', end_date: '2026-11-26' })}
                isLoading={runWalkforward.isPending}
              />
              <ResearchCard
                title="Monte Carlo Simulation"
                description="Statistical validation with 1000+ random trade sequence simulations"
                icon={<AlertTriangle className="h-8 w-8 text-purple-400" />}
                onRun={() => runMonteCarlo.mutate({ strategy_id: 1, trade_history: [], simulations: 1000 })}
                isLoading={runMonteCarlo.isPending}
              />
            </div>

            {runBacktest.isPending && <BacktestProgress />}
            {runWalkforward.isPending && <WalkforwardProgress />}
            {runMonteCarlo.isPending && <MonteCarloProgress />}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Helper Components
const [activeTab, setActiveTab] = useState('overview');

function MetricCard({ title, value, icon, change, changeLabel, className }: any) {
  const getPnlColor = (val: number | undefined) => val !== undefined && val >= 0 ? 'text-green-400' : 'text-red-400';
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
        {change !== undefined && (
          <div className="mt-3 flex items-center gap-1">
            <span className={cn('text-sm font-medium', getPnlColor(change))}>
              {change >= 0 ? '+' : ''}{formatCurrency(change)}
            </span>
            <span className="text-xs text-muted-foreground">{changeLabel}</span>
          </div>
        )}
      </CardContent>
    </Card>
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

function ExitReasonChart({ data }: any) {
  const entries = Object.entries(data || {});
  if (entries.length === 0) return <div className="text-center py-8 text-muted-foreground">No data</div>;
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={entries.map(([name, value]) => ({ name, value }))}
            cx="50%" cy="50%" innerRadius={60} outerRadius={100}
            dataKey="value" nameKey="name"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
          >
            {entries.map((_, i) => <Cell key={`cell-${i}`} fill={`hsl(var(--chart-${i + 1}))`} />)}
          </Pie>
          <Tooltip formatter={(value: number) => [value, 'Trades']} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function TpStageChart({ data }: any) {
  const entries = Object.entries(data || {});
  if (entries.length === 0) return <div className="text-center py-8 text-muted-foreground">No data</div>;
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={entries.map(([name, value]) => ({ stage: name, count: value }))} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="stage" stroke="hsl(var(--muted-foreground))" fontSize={11} />
          <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
          <Tooltip formatter={(value: number) => [value, 'Trades']} />
          <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RMultipleChart({ data }: any) {
  const entries = Object.entries(data || {});
  if (entries.length === 0) return <div className="text-center py-8 text-muted-foreground">No data</div>;
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={entries.map(([name, value]) => ({ stage: name, r: value }))} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="stage" stroke="hsl(var(--muted-foreground))" fontSize={11} />
          <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
          <Tooltip formatter={(value: number) => [value.toFixed(2), 'R-Multiple']} />
          <Bar dataKey="r" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function BreakdownCard({ title, data, keyField }: any) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
        <CardContent className="text-center py-8 text-muted-foreground">No data available</CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-3 max-h-96 overflow-y-auto">
        {data.map((item: any) => (
          <div key={item[keyField]} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
            <div>
              <p className="font-medium">{item[keyField]}</p>
              <p className="text-xs text-muted-foreground">{item.trades} trades • {item.win_rate?.toFixed(1)}% WR</p>
            </div>
            <div className="text-right">
              <p className="font-mono font-medium">{formatCurrency(item.net_pnl)}</p>
              <p className="text-xs text-muted-foreground">PF: {item.profit_factor?.toFixed(2)}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ResearchCard({ title, description, icon, onRun, isLoading }: any) {
  return (
    <Card className="h-full">
      <CardContent className="flex flex-col h-full">
        <div className="mb-4">{icon}</div>
        <h3 className="font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground mb-4 flex-1">{description}</p>
        <Button className="mt-auto" onClick={onRun} disabled={isLoading}>
          {isLoading ? 'Running...' : 'Run'}
        </Button>
      </CardContent>
    </Card>
  );
}

function BacktestProgress() {
  return (
    <Card className="border-blue-500/50 bg-blue-500/5">
      <CardContent className="py-4">
        <div className="flex items-center gap-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
          <div>
            <p className="font-medium">Backtest Running...</p>
            <p className="text-sm text-muted-foreground">Processing historical data...</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function WalkforwardProgress() {
  return (
    <Card className="border-green-500/50 bg-green-500/5">
      <CardContent className="py-4">
        <div className="flex items-center gap-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500" />
          <div>
            <p className="font-medium">Walk-Forward Analysis Running...</p>
            <p className="text-sm text-muted-foreground">Processing rolling windows...</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MonteCarloProgress() {
  return (
    <Card className="border-purple-500/50 bg-purple-500/5">
      <CardContent className="py-4">
        <div className="flex items-center gap-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500" />
          <div>
            <p className="font-medium">Monte Carlo Simulation Running...</p>
            <p className="text-sm text-muted-foreground">Running 1000+ simulations...</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function createHistogram(data: number[], bins: number) {
  if (!data.length) return [];
  const min = Math.min(...data);
  const max = Math.max(...data);
  const binSize = (max - min) / bins;
  const histogram: { range: string; count: number }[] = [];

  for (let i = 0; i < bins; i++) {
    const binMin = min + i * binSize;
    const binMax = min + (i + 1) * binSize;
    const count = data.filter(v => v >= binMin && v < binMax).length;
    histogram.push({ range: `${binMin.toFixed(2)}-${binMax.toFixed(2)}`, count });
  }
  return histogram;
}

// Need to import hooks
import { useAnalytics } from '../hooks/useAnalytics';

import React, { useState } from 'react';
import { usePaperStatus, useOpenPositions as usePositions, usePaperTrade, useTradeHistory, usePnLSummary, usePaperControl } from '../hooks/useDashboard';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import { Badge } from '../components/common/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/common/Tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/common/Dialog';
import { Input } from '../components/common/Input';
import { Label } from '../components/common/Label';
import { useForm } from 'react-hook-form';
import { Zap, TrendingUp, TrendingDown, DollarSign, RotateCcw, X, Plus, Minus, CheckCircle, AlertTriangle, Shield, Pause, Play } from 'lucide-react';
import { cn } from '../utils/cn';
import { formatCurrency, formatPct } from '../utils/format';
import type { Position, PaperTradeRequest } from '../types/api';

export function TradingPage() {
  const { data: paperStatus, isLoading } = usePaperStatus();
  const { data: positions } = usePositions();
  const { data: tradeHistory } = useTradeHistory({ limit: 50 });
  const { data: pnlSummary } = usePnLSummary(30);
  const paperTrade = usePaperTrade();
  const { pause, resume, reset } = usePaperControl();

  const [activeTab, setActiveTab] = useState<'positions' | 'orders' | 'history' | 'pnl'>('positions');
  const [newTradeDialog, setNewTradeDialog] = useState(false);
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);

  const {
    register,
    handleSubmit,
    reset: resetForm,
    formState: { errors },
  } = useForm<PaperTradeRequest>({
    defaultValues: {
      symbol: 'BTCUSDT',
      exchange: 'binance',
      direction: 'LONG',
      execution_mode: 'paper',
      runner_pct: 0.1,
    },
  });

  const onSubmit = async (data: PaperTradeRequest) => {
    try {
      await paperTrade.mutateAsync(data);
      setNewTradeDialog(false);
      resetForm();
    } catch (err) {
      console.error('Paper trade failed:', err);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Paper Trading</h1>
          <p className="text-muted-foreground">Simulated trading environment - no real funds at risk</p>
        </div>
        <div className="flex items-center gap-2">
          <DialogTrigger asChild onOpenChange={setNewTradeDialog}>
            <Button onClick={() => resetForm({ symbol: 'BTCUSDT', exchange: 'binance', direction: 'LONG', execution_mode: 'paper', runner_pct: 0.1 })}>
              <Plus className="h-4 w-4 mr-2" />
              New Trade
            </Button>
          </DialogTrigger>
          <Button variant="outline" size="sm" onClick={() => pause.mutate()} disabled={paperStatus?.is_paused}>
            <Pause className="h-4 w-4 mr-2" />
            Pause
          </Button>
          <Button variant="outline" size="sm" onClick={() => resume.mutate()} disabled={!paperStatus?.is_paused}>
            <Play className="h-4 w-4 mr-2" />
            Resume
          </Button>
          <Button variant="destructive" size="sm" onClick={() => reset.mutate()}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>
      </div>

      {/* Account Status Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          title="Equity"
          value={formatCurrency(paperStatus?.equity || 0)}
          icon={<DollarSign className="h-5 w-5 text-green-400" />}
          change={paperStatus?.unrealized_pnl}
          changeLabel="Unrealized P&L"
        />
        <MetricCard
          title="Available Balance"
          value={formatCurrency(paperStatus?.available_balance || 0)}
          icon={<Shield className="h-5 w-5 text-blue-400" />}
          subtitle={`${paperStatus?.open_positions || 0} / ${paperStatus?.max_positions || 2} positions`}
        />
        <MetricCard
          title="Daily P&L"
          value={formatCurrency(paperStatus?.realized_pnl_today || 0)}
          icon={<TrendingUp className="h-5 w-5" />}
          className={paperStatus?.realized_pnl_today && paperStatus.realized_pnl_today >= 0 ? 'text-green-400' : 'text-red-400'}
        />
        <MetricCard
          title="Drawdown Limit"
          value={`${paperStatus?.daily_loss_limit || 0}%`}
          icon={<AlertTriangle className="h-5 w-5 text-yellow-400" />}
          subtitle={paperStatus?.daily_loss_used_pct ? `${paperStatus.daily_loss_used_pct.toFixed(1)}% used` : '0% used'}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="positions" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="positions">Positions ({(positions?.length || 0)})</TabsTrigger>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="history">History ({(tradeHistory?.length || 0)})</TabsTrigger>
          <TabsTrigger value="pnl">P&L Analytics</TabsTrigger>
        </TabsList>

        {/* Positions Tab */}
        <TabsContent value="positions">
          <PositionsTable positions={positions || []} onClose={setEditingPosition} />
        </TabsContent>

        {/* Orders Tab */}
        <TabsContent value="orders">
          <Card>
            <CardHeader>
              <CardTitle>Order Management</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-center py-8">Order management table - to be implemented</p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <TradeHistoryTable trades={tradeHistory || []} />
        </TabsContent>

        {/* P&L Tab */}
        <TabsContent value="pnl">
          <PnLAnalytics pnlSummary={pnlSummary} />
        </TabsContent>
      </Tabs>

      {/* New Trade Dialog */}
      <Dialog open={newTradeDialog} onOpenChange={setNewTradeDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New Paper Trade</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-4">
            <div className="grid gap-2 md:grid-cols-2">
              <FormField label="Symbol" name="symbol" register={register} error={errors.symbol}>
                <Input placeholder="BTCUSDT" />
              </FormField>
              <FormField label="Exchange" name="exchange" register={register} error={errors.exchange}>
                <select {...register('exchange')} className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="binance">Binance</option>
                  <option value="bitget">Bitget</option>
                </select>
              </FormField>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <FormField label="Direction" name="direction" register={register} error={errors.direction}>
                <select {...register('direction')} className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="LONG">LONG</option>
                  <option value="SHORT">SHORT</option>
                </select>
              </FormField>
              <FormField label="Entry Price (optional)" name="entry_price" register={register} error={errors.entry_price}>
                <Input type="number" step="0.01" placeholder="Market price" />
              </FormField>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <FormField label="Quantity (optional)" name="quantity" register={register} error={errors.quantity}>
                <Input type="number" step="0.001" placeholder="Auto-calculated" />
              </FormField>
              <FormField label="Leverage (optional)" name="leverage" register={register} error={errors.leverage}>
                <Input type="number" step="1" min="1" max="10" placeholder="Auto-calculated" />
              </FormField>
            </div>

            <div className="grid gap-2 md:grid-cols-3">
              <FormField label="Stop Loss" name="stop_loss" register={register} error={errors.stop_loss}>
                <Input type="number" step="0.01" required />
              </FormField>
              <FormField label="TP1" name="tp1" register={register} error={errors.tp1}>
                <Input type="number" step="0.01" required />
              </FormField>
              <FormField label="TP2" name="tp2" register={register} error={errors.tp2}>
                <Input type="number" step="0.01" required />
              </FormField>
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <FormField label="TP3" name="tp3" register={register} error={errors.tp3}>
                <Input type="number" step="0.01" required />
              </FormField>
              <FormField label="Runner %" name="runner_pct" register={register} error={errors.runner_pct}>
                <Input type="number" step="0.01" min="0" max="1" defaultValue={0.1} />
              </FormField>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => setNewTradeDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={paperTrade.isPending}>
                <Zap className="h-4 w-4 mr-2" />
                {paperTrade.isPending ? 'Placing...' : 'Place Trade'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Close Position Dialog */}
      {editingPosition && (
        <Dialog open={true} onOpenChange={() => setEditingPosition(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Close Position</DialogTitle>
            </DialogHeader>
            <div className="p-4 space-y-4">
              <p>Close {editingPosition.direction} {editingPosition.symbol} @ {editingPosition.quantity}?</p>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setEditingPosition(null)}>Cancel</Button>
                <Button variant="destructive" onClick={() => { /* close logic */ setEditingPosition(null); }}>
                  Close Position
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
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
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  change?: number;
  changeLabel?: string;
  subtitle?: string;
  className?: string;
}) {
  const getPnlColor = (val: number | undefined) => val !== undefined && val >= 0 ? 'text-green-400' : 'text-red-400';

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

function FormField({
  label,
  name,
  register,
  error,
  children,
}: {
  label: string;
  name: string;
  register: any;
  error: any;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={name}>{label}</Label>
      {React.cloneElement(children as React.ReactElement, {
        ...register(name),
        id: name,
        'aria-invalid': !!error,
        'aria-describedby': error ? `${name}-error` : undefined,
      })}
      {error && <p id={`${name}-error`} className="text-sm text-red-400">{error.message}</p>}
    </div>
  );
}

function PositionsTable({ positions, onClose }: { positions: Position[]; onClose: (pos: Position) => void }) {
  if (positions.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Zap className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium">No Open Positions</h3>
          <p className="text-muted-foreground mt-1">Click "New Trade" to open a position</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Open Positions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead className="text-center">Dir</TableHead>
                <TableHead className="text-right">Entry</TableHead>
                <TableHead className="text-right">Current</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">P&L</TableHead>
                <TableHead className="text-right">P&L %</TableHead>
                <TableHead className="text-right">Lev</TableHead>
                <TableHead className="text-right">Margin</TableHead>
                <TableHead>TP Stage</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((pos) => (
                <TableRow key={pos.id}>
                  <TableCell className="font-mono font-medium">{pos.symbol}</TableCell>
                  <TableCell>{pos.exchange}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant="secondary" className={cn(
                      pos.direction === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                    )}>
                      {pos.direction}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">{pos.entry_price.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono">{pos.current_price.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono">{pos.quantity}</TableCell>
                  <TableCell className={cn("text-right font-mono font-medium", pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400')}>
                    {formatCurrency(pos.unrealized_pnl)}
                  </TableCell>
                  <TableCell className={cn("text-right font-mono font-medium", pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400')}>
                    {pos.entry_price > 0 ? formatPct((pos.current_price - pos.entry_price) / pos.entry_price * 100) : '0%'}
                  </TableCell>
                  <TableCell className="text-right font-mono">{pos.leverage}x</TableCell>
                  <TableCell className="text-right font-mono">{formatCurrency(pos.margin_used)}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="bg-blue-500/10 text-blue-400">
                      Stage {pos.tp_stage}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onClose(pos)}>
                      <X className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function TradeHistoryTable({ trades }: { trades: any[] }) {
  if (trades.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Zap className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium">No Trade History</h3>
          <p className="text-muted-foreground mt-1">Completed trades will appear here</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Trade History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead className="text-center">Dir</TableHead>
                <TableHead className="text-right">Entry</TableHead>
                <TableHead className="text-right">Exit</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Net P&L</TableHead>
                <TableHead className="text-right">R-Mult</TableHead>
                <TableHead className="text-right">Hold Time</TableHead>
                <TableHead>Exit Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((trade) => (
                <TableRow key={trade.id}>
                  <TableCell>{new Date(trade.closed_at).toLocaleDateString()}</TableCell>
                  <TableCell className="font-mono">{trade.symbol}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant="secondary" className={trade.direction === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}>
                      {trade.direction}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">{trade.entry_price.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono">{trade.exit_price.toLocaleString()}</TableCell>
                  <TableCell className="text-right font-mono">{trade.quantity}</TableCell>
                  <TableCell className={cn("text-right font-mono font-medium", trade.net_pnl >= 0 ? 'text-green-400' : 'text-red-400')}>
                    {formatCurrency(trade.net_pnl)}
                  </TableCell>
                  <TableCell className="text-right font-mono">{trade.r_multiple.toFixed(2)}</TableCell>
                  <TableCell className="text-right font-mono">{trade.hold_time_hours.toFixed(1)}h</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={trade.exit_reason.includes('TP') ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}>
                      {trade.exit_reason}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function PnLAnalytics({ pnlSummary }: { pnlSummary: any }) {
  if (!pnlSummary) {
    return <div className="text-center py-12 text-muted-foreground">Loading P&L data...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard title="Net P&L" value={formatCurrency(pnlSummary.net_pnl || 0)} icon={<DollarSign className="h-5 w-5 text-green-400" />} />
        <MetricCard title="Win Rate" value={formatPct(pnlSummary.win_rate || 0)} icon={<TrendingUp className="h-5 w-5 text-blue-400" />} />
        <MetricCard title="Profit Factor" value={(pnlSummary.profit_factor || 0).toFixed(2)} icon={<CheckCircle className="h-5 w-5 text-green-400" />} />
        <MetricCard title="Expectancy" value={formatCurrency(pnlSummary.expectancy || 0)} icon={<TrendingUp className="h-5 w-5 text-purple-400" />} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Trade Breakdown</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <StatRow label="Total Trades" value={pnlSummary.total_trades} />
            <StatRow label="Winning" value={pnlSummary.winning_trades} className="text-green-400" />
            <StatRow label="Losing" value={pnlSummary.losing_trades} className="text-red-400" />
            <StatRow label="Avg R-Multiple" value={pnlSummary.avg_r_multiple?.toFixed(2)} />
            <StatRow label="Best Trade" value={formatCurrency(pnlSummary.best_trade || 0)} className="text-green-400" />
            <StatRow label="Worst Trade" value={formatCurrency(pnlSummary.worst_trade || 0)} className="text-red-400" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Exit Reasons</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(pnlSummary.by_exit_reason || {}).map(([reason, count]) => (
              <StatRow key={reason} label={reason} value={String(count)} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>TP Stages</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(pnlSummary.by_tp_stage || {}).map(([stage, count]) => (
              <StatRow key={stage} label={`Stage ${stage}`} value={String(count)} />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatRow({ label, value, className }: { label: string; value: string | number; className?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn('font-mono font-medium', className)}>{value}</span>
    </div>
  );
}

// Need to import Dialog and Shield

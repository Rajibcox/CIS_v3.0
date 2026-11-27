import React, { useState } from 'react';
import { useSignals, useActiveSignals, useBestSignals, useSignalDetail, useExecutePaperTrade } from '../hooks/useSignals';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import { Badge } from '../components/common/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/common/Tabs';
import { Search, Filter, Zap, ExternalLink, Clock, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '../utils/cn';
import type { SignalResponse, SignalDetail } from '../types/api';
import { formatCurrency } from '../utils/format';

export function SignalsPage() {
  const { data: signalsData, isLoading, isError } = useSignals();
  const { data: activeSignals } = useActiveSignals();
  const { data: bestSignals } = useBestSignals(10);
  const executePaperTrade = useExecutePaperTrade();

  const [activeTab, setActiveTab] = useState<'active' | 'history' | 'best'>('active');
  const [selectedSignal, setSelectedSignal] = useState<SignalResponse | null>(null);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const { data: signalDetail } = useSignalDetail(detailSignalId || 0, !!detailSignalId);

  const formatCurrency = (value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const formatPct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  const getDirectionColor = (dir: string) => dir === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400';
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      candidate: 'bg-gray-500/10 text-gray-400',
      qualified: 'bg-blue-500/10 text-blue-400',
      active: 'bg-green-500/10 text-green-400',
      triggered: 'bg-yellow-500/10 text-yellow-400',
      executed: 'bg-green-500/10 text-green-400',
      expired: 'bg-red-500/10 text-red-400',
      invalidated: 'bg-red-500/10 text-red-400',
      rejected: 'bg-red-500/10 text-red-400',
    };
    return colors[status] || 'bg-muted text-muted-foreground';
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <h2 className="text-lg font-semibold">Signal data unavailable</h2>
        <p className="text-sm text-muted-foreground mt-2 max-w-xl">
          Persisted signal records and performance statistics are not available yet.
          Strategy-rule matches are not actionable signals, so no sample trades or
          fabricated signal values are shown.
        </p>
      </div>
    );
  }

  const handlePaperTrade = async (signal: SignalResponse) => {
    try {
      await executePaperTrade.mutateAsync(signal.id);
    } catch (err) {
      console.error('Paper trade failed:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Signal Center</h1>
          <p className="text-muted-foreground">Trading signals and opportunity management</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
          <Button variant="outline" size="sm" onClick={() => {}}>
            <Search className="h-4 w-4 mr-2" />
            Scan Now
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Active Signals"
          value={activeSignals?.length || 0}
          icon={<Zap className="h-5 w-5 text-yellow-400" />}
        />
        <StatCard
          title="Best Score"
          value={bestSignals?.[0]?.signal_score?.toFixed(1) || 'N/A'}
          subtitle={bestSignals?.[0]?.symbol}
          icon={<TrendingUp className="h-5 w-5 text-green-400" />}
        />
        <StatCard
          title="Total Today"
          value={signalsData?.total || 0}
          icon={<Clock className="h-5 w-5 text-blue-400" />}
        />
        <StatCard
          title="Executed"
          value={signalsData?.signals?.filter((s: SignalResponse) => s.status === 'executed').length || 0}
          icon={<TrendingUp className="h-5 w-5 text-purple-400" />}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="active" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="active">
            <Zap className="h-4 w-4 mr-2" />
            Active ({activeSignals?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="best">
            <TrendingUp className="h-4 w-4 mr-2" />
            Best Signals ({bestSignals?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="history">
            <Clock className="h-4 w-4 mr-2" />
            History ({signalsData?.total || 0})
          </TabsTrigger>
        </TabsList>

        {/* Active Signals Tab */}
        <TabsContent value="active">
          <SignalTable
            signals={activeSignals || []}
            onPaperTrade={handlePaperTrade}
            onViewDetail={setDetailSignalId}
          />
        </TabsContent>

        {/* Best Signals Tab */}
        <TabsContent value="best">
          <SignalTable
            signals={bestSignals || []}
            onPaperTrade={handlePaperTrade}
            onViewDetail={setDetailSignalId}
          />
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <SignalTable
            signals={signalsData?.signals || []}
            onPaperTrade={handlePaperTrade}
            onViewDetail={setDetailSignalId}
            showStatus={true}
          />
        </TabsContent>
      </Tabs>

      {/* Signal Detail Modal */}
      {detailSignalId && signalDetail && (
        <SignalDetailModal
          signal={signalDetail}
          onClose={() => setDetailSignalId(null)}
          onPaperTrade={handlePaperTrade}
        />
      )}
    </div>
  );
}

function StatCard({ title, value, subtitle, icon }: { title: string; value: string | number; subtitle?: string; icon: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold font-mono mt-1">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className="p-2 bg-primary/10 rounded-lg">{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function SignalTable({
  signals,
  onPaperTrade,
  onViewDetail,
  showStatus = false,
}: {
  signals: SignalResponse[];
  onPaperTrade: (signal: SignalResponse) => void;
  onViewDetail: (id: number) => void;
  showStatus?: boolean;
}) {
  if (signals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Zap className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium">No Signals</h3>
        <p className="text-muted-foreground mt-1">Run a scan or wait for new signals to appear</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Exchange</TableHead>
            <TableHead>Strategy</TableHead>
            <TableHead className="text-center">Dir</TableHead>
            {showStatus && <TableHead>Status</TableHead>}
            <TableHead>Score</TableHead>
            <TableHead>Regime</TableHead>
            <TableHead className="text-right">Entry</TableHead>
            <TableHead className="text-right">SL</TableHead>
            <TableHead className="text-right">TP1</TableHead>
            <TableHead className="text-right">TP2</TableHead>
            <TableHead className="text-right">TP3</TableHead>
            <TableHead className="text-right">R:R</TableHead>
            <TableHead className="text-right">Lev</TableHead>
            <TableHead className="text-right">Margin</TableHead>
            <TableHead>HTF</TableHead>
            <TableHead>BTC</TableHead>
            <TableHead>Age</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {signals.map((signal) => (
            <TableRow key={signal.id} onClick={() => onViewDetail(signal.id)} className="cursor-pointer hover:bg-accent/50">
              <TableCell className="font-mono font-medium">{signal.symbol}</TableCell>
              <TableCell>{signal.exchange}</TableCell>
              <TableCell className="max-w-[120px] truncate">{signal.strategy}</TableCell>
              <TableCell className="text-center">
                <Badge variant="secondary" className={getDirectionColor(signal.direction)}>
                  {signal.direction}
                </Badge>
              </TableCell>
              {showStatus && (
                <TableCell>
                  <Badge variant="secondary" className={getStatusColor(signal.status)}>
                    {signal.status}
                  </Badge>
                </TableCell>
              )}
              <TableCell className="font-mono font-medium">{signal.signal_score.toFixed(1)}</TableCell>
              <TableCell>
                <Badge variant="secondary" className={getRegimeColor(signal.regime)}>
                  {signal.regime}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-mono">{signal.entry_price.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{signal.stop_loss.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{signal.tp1.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{signal.tp2.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{signal.tp3.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono font-medium">{signal.risk_reward.toFixed(1)}</TableCell>
              <TableCell className="text-right font-mono">{signal.suggested_leverage}x</TableCell>
              <TableCell className="text-right font-mono">${signal.required_margin.toFixed(0)}</TableCell>
              <TableCell className="text-center">
                {signal.htf_alignment ? <span className="text-green-400">✓</span> : <span className="text-red-400">✗</span>}
              </TableCell>
              <TableCell className="text-center">
                {signal.btc_alignment ? <span className="text-green-400">✓</span> : <span className="text-red-400">✗</span>}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {Math.floor((Date.now() - new Date(signal.created_at).getTime()) / 3600000)}h
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => { e.stopPropagation(); onPaperTrade(signal); }}>
                    <Zap className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function getDirectionColor(dir: string) {
  return dir === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400';
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    candidate: 'bg-gray-500/10 text-gray-400',
    qualified: 'bg-blue-500/10 text-blue-400',
    active: 'bg-green-500/10 text-green-400',
    triggered: 'bg-yellow-500/10 text-yellow-400',
    executed: 'bg-green-500/10 text-green-400',
    expired: 'bg-red-500/10 text-red-400',
    invalidated: 'bg-red-500/10 text-red-400',
    rejected: 'bg-red-500/10 text-red-400',
  };
  return colors[status] || 'bg-muted text-muted-foreground';
}

function getRegimeColor(regime: string) {
  const colors: Record<string, string> = {
    trending: 'bg-blue-500/10 text-blue-400',
    ranging: 'bg-yellow-500/10 text-yellow-400',
    volatile: 'bg-red-500/10 text-red-400',
    breakout: 'bg-purple-500/10 text-purple-400',
    reversal: 'bg-orange-500/10 text-orange-400',
  };
  return colors[regime] || 'bg-muted text-muted-foreground';
}

function SignalDetailModal({
  signal,
  onClose,
  onPaperTrade,
}: {
  signal: SignalDetail;
  onClose: () => void;
  onPaperTrade: (signal: SignalResponse) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-auto rounded-lg bg-card border shadow-xl animate-fade-in">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-card/95 backdrop-blur p-4">
          <div>
            <h2 className="text-lg font-bold">{signal.symbol} - {signal.direction} Signal</h2>
            <p className="text-sm text-muted-foreground">{signal.strategy} • {signal.timeframe} • Score: {signal.signal_score}</p>
          </div>
          <button onClick={onClose} className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-6">
          {/* Key Metrics */}
          <div className="grid gap-4 md:grid-cols-4">
            <DetailMetric label="Entry Zone" value={`${signal.entry_zone_low.toLocaleString()} - ${signal.entry_zone_high.toLocaleString()}`} />
            <DetailMetric label="Stop Loss" value={signal.stop_loss.toLocaleString()} />
            <DetailMetric label="Risk/Reward" value={signal.risk_reward.toFixed(1)} />
            <DetailMetric label="Leverage" value={`${signal.suggested_leverage}x`} />
          </div>

          {/* TP Targets */}
          <div className="border rounded-lg p-4">
            <h3 className="font-medium mb-3">Take Profit Targets</h3>
            <div className="grid gap-3 md:grid-cols-3">
              <TPCard stage="TP1 (40%)" price={signal.tp1} netPnl={signal.net_pnl_tp1} />
              <TPCard stage="TP2 (30%)" price={signal.tp2} netPnl={signal.net_pnl_tp2} />
              <TPCard stage="TP3 (20%)" price={signal.tp3} netPnl={signal.net_pnl_tp3} />
            </div>
            <div className="mt-3 p-3 bg-muted/50 rounded">
              <p className="text-sm">Runner (10%): Trailing stop - Est. PnL: {formatCurrency(signal.net_pnl_runner)}</p>
            </div>
          </div>

          {/* Risk Calculation */}
          <div className="border rounded-lg p-4">
            <h3 className="font-medium mb-3">Risk Calculation</h3>
            <div className="grid gap-2 md:grid-cols-3 text-sm">
              {Object.entries(signal.risk_calculation).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted-foreground">{formatKey(key)}</span>
                  <span className="font-mono">{typeof value === 'number' ? value.toLocaleString() : value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Leverage Decision */}
          <div className="border rounded-lg p-4">
            <h3 className="font-medium mb-3">Leverage Decision</h3>
            <p className="text-sm text-muted-foreground mb-3">{signal.leverage_decision.reason}</p>
            <div className="grid gap-2 md:grid-cols-3 text-sm">
              {Object.entries(signal.leverage_decision).filter(([k]) => k !== 'reason' && k !== 'rejected_alternatives').map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted-foreground">{formatKey(key)}</span>
                  <span className="font-mono">{typeof value === 'number' ? value.toLocaleString() : value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Indicators */}
          <div className="border rounded-lg p-4">
            <h3 className="font-medium mb-3">Indicator Values</h3>
            <div className="grid gap-2 md:grid-cols-4 text-sm">
              {Object.entries(signal.indicator_values).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted-foreground">{key}</span>
                  <span className="font-mono">{typeof value === 'number' ? value.toFixed(2) : value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Supporting Evidence */}
          <div className="border rounded-lg p-4">
            <h3 className="font-medium mb-3">Supporting Evidence</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              {signal.supporting_evidence.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Invalidating Conditions */}
          <div className="border rounded-lg p-4 bg-red-500/5">
            <h3 className="font-medium mb-3 text-red-400">Invalidating Conditions</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-red-300">
              {signal.invalidating_conditions.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Actions */}
          <div className="sticky bottom-0 border-t bg-card/95 backdrop-blur p-4 flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Close</Button>
            <Button onClick={() => { onPaperTrade(signal); onClose(); }}>
              <Zap className="h-4 w-4 mr-2" />
              Paper Trade
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold font-mono mt-1">{value}</p>
    </div>
  );
}

function TPCard({ stage, price, netPnl }: { stage: string; price: number; netPnl: number }) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <p className="text-xs text-muted-foreground">{stage}</p>
      <p className="text-lg font-bold font-mono mt-1">{price.toLocaleString()}</p>
      <p className="text-sm font-medium mt-1 text-green-400">Net PnL: {formatCurrency(netPnl)}</p>
    </div>
  );
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}
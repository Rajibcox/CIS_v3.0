import React, { useState } from 'react';
import { useMarketOverview, useMarketScan, useLongOpportunities, useShortOpportunities, useMarketRegime, useTriggerScan } from '../hooks/useMarket';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import { Badge } from '../components/common/Badge';
import { Search, Filter, RotateCcw, TrendingUp, TrendingDown, Zap, AlertTriangle, Activity, ExternalLink } from 'lucide-react';
import { cn } from '../utils/cn';
import type { MarketOverview, OpportunityResponse, ScannerResult } from '../types/api';

export function MarketPage() {
  const { data: overview, isLoading: overviewLoading } = useMarketOverview();
  const { data: scanData, isLoading: scanLoading, refetch: refetchScan } = useMarketScan();
  const { data: longData } = useLongOpportunities(70, 20);
  const { data: shortData } = useShortOpportunities(70, 20);
  const { data: regime } = useMarketRegime();
  const triggerScan = useTriggerScan();

  const [activeTab, setActiveTab] = useState<'scan' | 'long' | 'short' | 'overview'>('overview');
  const [filters, setFilters] = useState({
    minScore: 70,
    exchanges: ['binance', 'bitget'],
    timeframes: ['15m', '1h', '4h'],
  });

  const formatCurrency = (value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const formatPct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  const getDirectionColor = (dir: string) => dir === 'LONG' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400';
  const getRegimeColor = (regime: string) => {
    const colors: Record<string, string> = {
      trending: 'bg-blue-500/10 text-blue-400',
      ranging: 'bg-yellow-500/10 text-yellow-400',
      volatile: 'bg-red-500/10 text-red-400',
      breakout: 'bg-purple-500/10 text-purple-400',
      reversal: 'bg-orange-500/10 text-orange-400',
    };
    return colors[regime] || 'bg-muted text-muted-foreground';
  };

  const handleScan = async () => {
    await triggerScan.mutateAsync();
    setTimeout(() => refetchScan(), 2000);
  };

  if (overviewLoading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Market Intelligence</h1>
          <p className="text-muted-foreground">Real-time market scanning and opportunity detection</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleScan} disabled={triggerScan.isPending}>
            <RotateCcw className={cn("h-4 w-4 mr-2", triggerScan.isPending && "animate-spin")} />
            Scan Now
          </Button>
          <Button variant="outline" size="sm">
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
        </div>
      </div>

      {/* Market Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="BTC Dominance"
          value={`${overview?.btc_dominance || 0}%`}
          icon={<TrendingUp className="h-5 w-5 text-orange-400" />}
        />
        <MetricCard
          title="Fear & Greed"
          value={overview?.fear_greed_label || 'N/A'}
          subtitle={`Index: ${overview?.fear_greed_index || 0}`}
          icon={<Zap className="h-5 w-5 text-yellow-400" />}
        />
        <MetricCard
          title="24h Volume"
          value={formatCurrency((overview?.total_volume_24h || 0) / 1e9) + 'B'}
          icon={<Activity className="h-5 w-5 text-blue-400" />}
        />
        <MetricCard
          title="Open Interest"
          value={formatCurrency((overview?.total_open_interest || 0) / 1e9) + 'B'}
          subtitle={`Funding: ${(overview?.funding_rate_avg || 0) * 10000} bps`}
          icon={<AlertTriangle className="h-5 w-5 text-purple-400" />}
        />
      </div>

      {/* Market Regime */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Market Regime Analysis</CardTitle>
          <Badge variant="secondary" className={getRegimeColor(regime?.btc_regime || 'unknown')}>
            BTC: {regime?.btc_regime || 'unknown'}
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <RegimeCard title="BTC Regime" value={regime?.btc_regime || 'unknown'} color="blue" />
            <RegimeCard title="Altcoin Regime" value={regime?.altcoin_regime || 'unknown'} color="yellow" />
            <RegimeCard title="Volatility" value={regime?.volatility_state || 'unknown'} color="red" />
          </div>

          {regime?.key_levels && (
            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">BTC Support</p>
                <p className="font-mono font-bold">${regime.key_levels.btc_support?.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">BTC Resistance</p>
                <p className="font-mono font-bold">${regime.key_levels.btc_resistance?.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">ETH Support</p>
                <p className="font-mono font-bold">${regime.key_levels.eth_support?.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">ETH Resistance</p>
                <p className="font-mono font-bold">${regime.key_levels.eth_resistance?.toLocaleString()}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabbed Opportunities */}
      <div className="space-y-4">
        {/* Tabs */}
        <div className="flex gap-1 bg-muted p-1 rounded-lg" role="tablist">
          {[
            { id: 'overview', label: 'Overview', icon: null },
            { id: 'scan', label: 'All Signals', icon: Zap },
            { id: 'long', label: 'LONG', icon: TrendingUp },
            { id: 'short', label: 'SHORT', icon: TrendingDown },
          ].map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.icon && <tab.icon className="h-4 w-4" />}
              {tab.label}
              {tab.id === 'long' && longData?.opportunities && (
                <span className="ml-1 px-2 py-0.5 text-xs bg-green-500/10 text-green-400 rounded-full">
                  {longData.opportunities.length}
                </span>
              )}
              {tab.id === 'short' && shortData?.opportunities && (
                <span className="ml-1 px-2 py-0.5 text-xs bg-red-500/10 text-red-400 rounded-full">
                  {shortData.opportunities.length}
                </span>
              )}
              {tab.id === 'scan' && scanData?.opportunities && (
                <span className="ml-1 px-2 py-0.5 text-xs bg-blue-500/10 text-blue-400 rounded-full">
                  {scanData.opportunities.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && <OverviewTab overview={overview} />}
        {activeTab === 'scan' && <ScannerTab data={scanData} loading={scanLoading} />}
        {activeTab === 'long' && <OpportunityTab title="LONG Opportunities" data={longData} direction="LONG" />}
        {activeTab === 'short' && <OpportunityTab title="SHORT Opportunities" data={shortData} direction="SHORT" />}
      </div>
    </div>
  );
}

// Helper Components
function MetricCard({
  title,
  value,
  icon,
  subtitle,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  subtitle?: string;
}) {
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

function RegimeCard({ title, value, color }: { title: string; value: string; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-500/10 text-blue-400',
    yellow: 'bg-yellow-500/10 text-yellow-400',
    red: 'bg-red-500/10 text-red-400',
    green: 'bg-green-500/10 text-green-400',
    purple: 'bg-purple-500/10 text-purple-400',
  };

  return (
    <div className="p-4 rounded-lg bg-muted/50">
      <p className="text-xs text-muted-foreground">{title}</p>
      <p className="text-lg font-bold mt-1 capitalize">{value}</p>
      <div className="mt-2 h-1 w-full bg-muted rounded overflow-hidden">
        <div className={`h-full ${colorMap[color] || colorMap.blue}`} style={{ width: '65%' }} />
      </div>
    </div>
  );
}

function OverviewTab({ overview }: { overview: any }) {
  if (!overview) return <div className="text-center py-12 text-muted-foreground">Loading market overview...</div>;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Top Gainer" value={overview.top_gainer?.symbol} change={`${overview.top_gainer?.change_pct}%`} positive />
        <StatCard label="Top Loser" value={overview.top_loser?.symbol} change={`${overview.top_loser?.change_pct}%`} />
        <StatCard label="Top Volume" value={overview.top_volume?.symbol} value2={`${(overview.top_volume?.volume / 1e9).toFixed(1)}B`} />
        <StatCard label="Liquidations 24h" value={`${(overview.liquidations_24h?.long / 1e6).toFixed(0)}M L / ${(overview.liquidations_24h?.short / 1e6).toFixed(0)}M S`} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <Button variant="outline" onClick={() => window.location.href = '/market/scanner'}>
            <Search className="h-4 w-4 mr-2" />
            Run Full Scan
          </Button>
          <Button variant="outline" onClick={() => window.location.href = '/market/long'}>
            <TrendingUp className="h-4 w-4 mr-2 text-green-400" />
            View LONG Setups
          </Button>
          <Button variant="outline" onClick={() => window.location.href = '/market/short'}>
            <TrendingDown className="h-4 w-4 mr-2 text-red-400" />
            View SHORT Setups
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({ label, value, value2, change, positive }: { label: string; value: string; value2?: string; change?: string; positive?: boolean }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-lg font-bold font-mono mt-1">{value}</p>
        {value2 && <p className="text-sm text-muted-foreground mt-1">{value2}</p>}
        {change && (
          <span className={cn('text-xs font-medium mt-1 inline-block', positive ? 'text-green-400' : 'text-red-400')}>
            {change}
          </span>
        )}
      </CardContent>
    </Card>
  );
}

function ScannerTab({ data, loading }: { data?: OpportunityResponse; loading: boolean }) {
  const opportunities = data?.opportunities || [];

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>All Scanned Opportunities</CardTitle>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Scanned: {data?.total_scanned || 0}</span>
          <span>•</span>
          <span>Duration: {data?.scan_duration_ms || 0}ms</span>
          <span>•</span>
          <span>Found: {opportunities.length}</span>
        </div>
      </CardHeader>
      <CardContent>
        <OpportunityTable opportunities={opportunities} />
      </CardContent>
    </Card>
  );
}

function OpportunityTab({ title, data, direction }: { title: string; data?: OpportunityResponse; direction: 'LONG' | 'SHORT' }) {
  const opportunities = data?.opportunities || [];
  const isLong = direction === 'LONG';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          {isLong ? <TrendingUp className="h-5 w-5 text-green-400" /> : <TrendingDown className="h-5 w-5 text-red-400" />}
          {title}
        </CardTitle>
        <Badge variant="secondary" className={getDirectionColor(direction)}>
          {opportunities.length} setups
        </Badge>
      </CardHeader>
      <CardContent>
        <OpportunityTable opportunities={opportunities} />
      </CardContent>
    </Card>
  );
}

function OpportunityTable({ opportunities }: { opportunities: ScannerResult[] }) {
  if (opportunities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Zap className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium">No Opportunities Found</h3>
        <p className="text-muted-foreground mt-1">Adjust filters or wait for next scan</p>
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
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {opportunities.map((opp) => (
            <TableRow key={`${opp.symbol}-${opp.exchange}-${opp.strategy}`}>
              <TableCell className="font-mono font-medium">{opp.symbol}</TableCell>
              <TableCell>{opp.exchange}</TableCell>
              <TableCell className="max-w-[120px] truncate">{opp.strategy}</TableCell>
              <TableCell className="text-center">
                <Badge variant="secondary" className={getDirectionColor(opp.direction)}>
                  {opp.direction}
                </Badge>
              </TableCell>
              <TableCell className="font-mono font-medium">{opp.signal_score.toFixed(1)}</TableCell>
              <TableCell>
                <Badge variant="secondary" className={getRegimeColor(opp.regime)}>
                  {opp.regime}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-mono">{opp.entry_price.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{opp.stop_loss.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{opp.tp1.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{opp.tp2.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono">{opp.tp3.toLocaleString()}</TableCell>
              <TableCell className="text-right font-mono font-medium">{opp.risk_reward.toFixed(1)}</TableCell>
              <TableCell className="text-right font-mono">{opp.suggested_leverage}x</TableCell>
              <TableCell className="text-right font-mono">${opp.required_margin.toFixed(0)}</TableCell>
              <TableCell className="text-center">
                {opp.htf_alignment ? (
                  <span className="text-green-400">✓</span>
                ) : (
                  <span className="text-red-400">✗</span>
                )}
              </TableCell>
              <TableCell className="text-center">
                {opp.btc_alignment ? (
                  <span className="text-green-400">✓</span>
                ) : (
                  <span className="text-red-400">✗</span>
                )}
              </TableCell>
              <TableCell>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// Need to import Badge

function getDirectionColor(direction?: string): string {
  const d = (direction || '').toUpperCase();
  if (d === 'LONG') return 'bg-green-500/10 text-green-500';
  if (d === 'SHORT') return 'bg-red-500/10 text-red-500';
  return 'bg-muted text-muted-foreground';
}

function getRegimeColor(regime?: string): string {
  switch ((regime || '').toLowerCase()) {
    case 'trending': return 'bg-blue-500/10 text-blue-500';
    case 'ranging':
    case 'sideways': return 'bg-gray-500/10 text-gray-400';
    case 'volatile': return 'bg-orange-500/10 text-orange-500';
    case 'breakout': return 'bg-purple-500/10 text-purple-500';
    case 'reversal': return 'bg-yellow-500/10 text-yellow-500';
    case 'low_volatility': return 'bg-teal-500/10 text-teal-500';
    default: return 'bg-muted text-muted-foreground';
  }
}

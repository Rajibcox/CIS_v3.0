import React, { useState } from 'react';
import { useStrategies, useIndicators, useCreateStrategy, useValidateStrategy } from '../hooks/useStrategies';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/common/Table';
import { Badge } from '../components/common/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/common/Tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/common/Dialog';
import { Input } from '../components/common/Input';
import { Label } from '../components/common/Label';
import { useForm, type UseFormReturn } from 'react-hook-form';
import { Zap, Plus, Edit, Trash2, BarChart2, Settings, Copy, CheckCircle, AlertTriangle, ExternalLink, X } from 'lucide-react';
import { cn } from '../utils/cn';
import type { StrategyResponse, StrategyCreate, IndicatorInfo, RuleCondition, RuleGroup, StrategyRuleSet } from '../types/api';

export function StrategiesPage() {
  const { data: strategies, isLoading } = useStrategies(false, true);
  const { data: indicators } = useIndicators();
  const createStrategy = useCreateStrategy();
  const validateStrategy = useValidateStrategy();

  const [activeTab, setActiveTab] = useState<'list' | 'builder' | 'indicators'>('list');
  const [editingStrategy, setEditingStrategy] = useState<StrategyResponse | null>(null);
  const [builderMode, setBuilderMode] = useState<'entry' | 'exit' | 'long' | 'short'>('entry');

  const strategyForm = useForm<StrategyCreate>({
    defaultValues: {
      name: '',
      description: '',
      version: '1.0.0',
      is_active: true,
      direction: 'BOTH',
      weight: 1.0,
      risk_multiplier: 1.0,
      timeframes: ['15m', '1h'],
      symbols: [],
      min_signal_score: 70,
      rule_set: {
        entry_rules: { operator: 'AND', conditions: [], groups: [] },
        exit_rules: { operator: 'AND', conditions: [], groups: [] },
      },
    },
  });

  const handleSaveStrategy = (data: StrategyCreate) => {
    createStrategy.mutate(data, {
      onSuccess: () => {
        strategyForm.reset();
        setEditingStrategy(null);
        setActiveTab('list');
      },
    });
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Strategy Center</h1>
          <p className="text-muted-foreground">Manage and create trading strategies</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => { strategyForm.reset(); setEditingStrategy(null); setActiveTab('builder'); }}>
            <Plus className="h-4 w-4 mr-2" />
            New Strategy
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="list" onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="list">
            <Zap className="h-4 w-4 mr-2" />
            Strategies ({(strategies?.length || 0)})
          </TabsTrigger>
          <TabsTrigger value="builder">
            <Settings className="h-4 w-4 mr-2" />
            Visual Builder
          </TabsTrigger>
          <TabsTrigger value="indicators">
            <BarChart2 className="h-4 w-4 mr-2" />
            Indicators
          </TabsTrigger>
        </TabsList>

        {/* Strategies List */}
        <TabsContent value="list">
          <StrategiesTable
            strategies={strategies || []}
            onEdit={setEditingStrategy}
            onClone={(s) => { /* clone logic */ }}
            onDelete={(id) => { /* delete logic */ }}
          />
        </TabsContent>

        {/* Visual Builder */}
        <TabsContent value="builder">
          <StrategyBuilder
            initialStrategy={editingStrategy}
            indicators={indicators || []}
            strategyForm={strategyForm}
            onSave={(data) => handleSaveStrategy(data)}
            onCancel={() => { setEditingStrategy(null); setActiveTab('list'); }}
          />
        </TabsContent>

        {/* Indicators List */}
        <TabsContent value="indicators">
          <IndicatorsTable indicators={indicators || []} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StrategiesTable({
  strategies,
  onEdit,
  onClone,
  onDelete,
}: {
  strategies: StrategyResponse[];
  onEdit: (s: StrategyResponse) => void;
  onClone: (s: StrategyResponse) => void;
  onDelete: (id: number) => void;
}) {
  if (strategies.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Zap className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium">No Strategies</h3>
          <p className="text-muted-foreground mt-1">Create your first strategy using the Visual Builder</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Strategy Library</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Timeframes</TableHead>
                <TableHead>Win Rate (30d)</TableHead>
                <TableHead>Profit Factor</TableHead>
                <TableHead>Expectancy</TableHead>
                <TableHead>Signals (24h)</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strategies.map((strategy) => (
                <TableRow key={strategy.id}>
                  <TableCell className="font-medium">{strategy.name}</TableCell>
                  <TableCell className="font-mono">{strategy.version}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={strategy.direction === 'LONG' ? 'bg-green-500/10 text-green-400' : strategy.direction === 'SHORT' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}>
                      {strategy.direction}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={strategy.is_active ? 'success' : 'secondary'}>
                      {strategy.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </TableCell>
                  <TableCell>{strategy.timeframes.join(', ')}</TableCell>
                  <TableCell className="font-mono">{strategy.win_rate_30d?.toFixed(1) || '0'}%</TableCell>
                  <TableCell className="font-mono">{strategy.profit_factor_30d?.toFixed(2) || '0.00'}</TableCell>
                  <TableCell className="font-mono">{strategy.expectancy_30d?.toFixed(2) || '0.00'}</TableCell>
                  <TableCell className="font-mono">{strategy.signal_count_24h || 0}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(strategy)}>
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onClone(strategy)}>
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-400 hover:text-red-300" onClick={() => onDelete(strategy.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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

function IndicatorsTable({ indicators }: { indicators: IndicatorInfo[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Available Indicators</CardTitle>
        <CardDescription>Technical indicators available for strategy building</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Default Params</TableHead>
                <TableHead>Timeframes</TableHead>
                <TableHead>Repainting Risk</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {indicators.map((ind) => (
                <TableRow key={ind.name}>
                  <TableCell className="font-mono font-medium">{ind.display_name} ({ind.name})</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="capitalize">{ind.category}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">{ind.description}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {JSON.stringify(ind.default_params)}
                  </TableCell>
                  <TableCell>{ind.supports_timeframes.join(', ')}</TableCell>
                  <TableCell>
                    <Badge variant={
                      ind.repainting_risk === 'none' ? 'success' :
                      ind.repainting_risk === 'low' ? 'warning' : 'destructive'
                    }>
                      {ind.repainting_risk}
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

function StrategyBuilder({
  initialStrategy,
  indicators,
  strategyForm,
  onSave,
  onCancel,
}: {
  initialStrategy: StrategyResponse | null;
  indicators: IndicatorInfo[];
  strategyForm: UseFormReturn<StrategyCreate>;
  onSave: (data: StrategyCreate) => void;
  onCancel: () => void;
}) {
  const validateStrategy = useValidateStrategy();
  const [activeSection, setActiveSection] = useState<'entry' | 'exit' | 'long' | 'short'>('entry');
  const [ruleGroups, setRuleGroups] = useState<StrategyRuleSet>({
    entry_rules: { operator: 'AND', conditions: [], groups: [] },
    exit_rules: { operator: 'AND', conditions: [], groups: [] },
    long_rules: { operator: 'AND', conditions: [], groups: [] },
    short_rules: { operator: 'AND', conditions: [], groups: [] },
  });
  const [showValidation, setShowValidation] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);

  // Load initial strategy rules if editing
  React.useEffect(() => {
    if (initialStrategy) {
      // In real app, fetch rule_set from backend
      // setRuleGroups(initialStrategy.rule_set);
    }
  }, [initialStrategy]);

  const handleValidate = async () => {
    const result = await validateStrategy.mutateAsync(ruleGroups);
    setValidationResult(result);
    setShowValidation(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">Visual Strategy Builder</h2>
          <p className="text-muted-foreground">Create strategies using drag-and-drop rule builder</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleValidate}>
            <CheckCircle className="h-4 w-4 mr-2" />
            Validate
          </Button>
          <Button variant="outline" onClick={onCancel}>
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button onClick={() => onSave({ ...strategyForm.getValues(), rule_set: ruleGroups })}>
            <Zap className="h-4 w-4 mr-2" />
            Save Strategy
          </Button>
        </div>
      </div>

      {/* Validation Result */}
      {showValidation && validationResult && (
        <Card className={cn(validationResult.valid ? 'border-green-500/20' : 'border-red-500/20')}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-2">
              {validationResult.valid ? (
                <CheckCircle className="h-5 w-5 text-green-400" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-400" />
              )}
              <span className="font-medium">
                {validationResult.valid ? 'Strategy Valid' : 'Validation Errors'}
              </span>
            </div>
            {validationResult.errors.length > 0 && (
              <ul className="list-disc list-inside space-y-1 text-sm text-red-400">
                {validationResult.errors.map((e: string, i: number) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
            {validationResult.warnings.length > 0 && (
              <ul className="list-disc list-inside space-y-1 text-sm text-yellow-400 mt-2">
                {validationResult.warnings.map((w: string, i: number) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {/* Strategy Meta */}
      <Card>
        <CardHeader>
          <CardTitle>Strategy Configuration</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div className="space-y-2">
            <Label>Strategy Name</Label>
            <Input placeholder="My Strategy" />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Input placeholder="Strategy description" />
          </div>
          <div className="space-y-2">
            <Label>Direction</Label>
            <select className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="BOTH">Both</option>
              <option value="LONG">Long Only</option>
              <option value="SHORT">Short Only</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label>Min Signal Score</Label>
            <Input type="number" min="0" max="100" defaultValue={70} />
          </div>
        </CardContent>
      </Card>

      {/* Rule Sections Tabs */}
      <Tabs defaultValue="entry" onValueChange={setActiveSection}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="entry">Entry Rules</TabsTrigger>
          <TabsTrigger value="exit">Exit Rules</TabsTrigger>
          <TabsTrigger value="long">LONG Rules</TabsTrigger>
          <TabsTrigger value="short">SHORT Rules</TabsTrigger>
        </TabsList>

        <TabsContent value="entry">
          <RuleBuilder
            ruleGroup={ruleGroups.entry_rules}
            indicators={indicators}
            onChange={(group) => setRuleGroups(prev => ({ ...prev, entry_rules: group }))}
          />
        </TabsContent>

        <TabsContent value="exit">
          <RuleBuilder
            ruleGroup={ruleGroups.exit_rules}
            indicators={indicators}
            onChange={(group) => setRuleGroups(prev => ({ ...prev, exit_rules: group }))}
          />
        </TabsContent>

        <TabsContent value="long">
          <RuleBuilder
            ruleGroup={ruleGroups.long_rules || { operator: 'AND', conditions: [], groups: [] }}
            indicators={indicators}
            onChange={(group) => setRuleGroups(prev => ({ ...prev, long_rules: group }))}
          />
        </TabsContent>

        <TabsContent value="short">
          <RuleBuilder
            ruleGroup={ruleGroups.short_rules || { operator: 'AND', conditions: [], groups: [] }}
            indicators={indicators}
            onChange={(group) => setRuleGroups(prev => ({ ...prev, short_rules: group }))}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function RuleBuilder({
  ruleGroup,
  indicators,
  onChange,
}: {
  ruleGroup: RuleGroup;
  indicators: IndicatorInfo[];
  onChange: (group: RuleGroup) => void;
}) {
  const [conditions, setConditions] = useState<RuleCondition[]>(ruleGroup.conditions);
  const [subGroups, setSubGroups] = useState<RuleGroup[]>(ruleGroup.groups);
  const [operator, setOperator] = useState<RuleGroup['operator']>(ruleGroup.operator);

  React.useEffect(() => {
    onChange({ operator, conditions, groups: subGroups });
  }, [operator, conditions, subGroups, onChange]);

  const addCondition = () => {
    setConditions(prev => [...prev, {
      indicator: undefined,
      operator: '>',
      threshold: 0,
    }]);
  };

  const updateCondition = (index: number, updates: Partial<RuleCondition>) => {
    setConditions(prev => prev.map((c, i) => i === index ? { ...c, ...updates } : c));
  };

  const removeCondition = (index: number) => {
    setConditions(prev => prev.filter((_, i) => i !== index));
  };

  const addGroup = () => {
    setSubGroups(prev => [...prev, { operator: 'AND', conditions: [], groups: [] }]);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <select
            value={operator}
            onChange={(e) => setOperator(e.target.value as any)}
            className="h-8 rounded-md border border-input bg-background px-3 py-1 text-sm"
          >
            <option value="AND">AND (all conditions must be true)</option>
            <option value="OR">OR (any condition can be true)</option>
          </select>
        </CardTitle>
        <Button variant="outline" size="sm" onClick={addCondition}>
          <Plus className="h-4 w-4 mr-2" />
          Add Condition
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Conditions List */}
        {conditions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No conditions added yet. Click "Add Condition" to start building.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {conditions.map((condition, index) => (
              <ConditionEditor
                key={index}
                condition={condition}
                index={index}
                indicators={indicators}
                onUpdate={(updates) => updateCondition(index, updates)}
                onRemove={() => removeCondition(index)}
              />
            ))}
          </div>
        )}

        {/* Sub-groups */}
        {subGroups.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="font-medium mb-3">Sub-Groups</h4>
            {subGroups.map((group, groupIndex) => (
              <div key={groupIndex} className="border-l-2 border-muted pl-4 ml-4 my-2">
                <RuleBuilder
                  ruleGroup={group}
                  indicators={indicators}
                  onChange={(updatedGroup) => {
                    setSubGroups(prev => prev.map((g, i) => i === groupIndex ? updatedGroup : g));
                  }}
                />
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={addGroup}>
              <Plus className="h-4 w-4 mr-2" />
              Add Sub-Group
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ConditionEditor({
  condition,
  index,
  indicators,
  onUpdate,
  onRemove,
}: {
  condition: RuleCondition;
  index: number;
  indicators: IndicatorInfo[];
  onUpdate: (updates: Partial<RuleCondition>) => void;
  onRemove: () => void;
}) {
  const [type, setType] = useState<'indicator_value' | 'indicator_indicator' | 'price_action' | 'volume' | 'trend' | 'regime'>(
    condition.indicator ? 'indicator_value' :
    condition.indicator_a && condition.indicator_b ? 'indicator_indicator' :
    condition.price_relation ? 'price_action' :
    condition.volume_condition ? 'volume' :
    condition.trend_condition ? 'trend' : 'regime'
  );

  const handleIndicatorChange = (indicatorName: string) => {
    const indicator = indicators.find(i => i.name === indicatorName);
    if (type === 'indicator_value') {
      onUpdate({ indicator: { name: indicatorName, params: indicator?.default_params || {}, source: 'close' } });
    } else if (type === 'indicator_indicator') {
      // Handle two indicators
    }
  };

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border bg-muted/50">
      <span className="text-xs text-muted-foreground mt-1">#{index + 1}</span>

      {/* Type Selector */}
      <select
        value={type}
        onChange={(e) => {
          setType(e.target.value as any);
          onUpdate({}); // Reset condition when type changes
        }}
        className="h-8 rounded-md border border-input bg-background px-2 text-sm min-w-[180px]"
      >
        <option value="indicator_value">Indicator vs Value</option>
        <option value="indicator_indicator">Indicator vs Indicator</option>
        <option value="price_action">Price Action</option>
        <option value="volume">Volume</option>
        <option value="trend">Trend</option>
        <option value="regime">Market Regime</option>
      </select>

      {/* Condition Fields based on type */}
      {type === 'indicator_value' && (
        <div className="flex-1 flex items-center gap-2">
          <select
            value={condition.indicator?.name || ''}
            onChange={(e) => handleIndicatorChange(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm flex-1"
          >
            <option value="">Select Indicator</option>
            {indicators.map(ind => (
              <option key={ind.name} value={ind.name}>{ind.display_name}</option>
            ))}
          </select>
          <select
            value={condition.operator || '>'}
            onChange={(e) => onUpdate({ operator: e.target.value as any })}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm w-24"
          >
            <option value=">">{'>'}</option>
            <option value="<">{'<'}</option>
            <option value=">=">{'>='}</option>
            <option value="<=">{'<='}</option>
            <option value="==">==</option>
            <option value="crosses_above">Crosses Above</option>
            <option value="crosses_below">Crosses Below</option>
          </select>
          <Input
            type="number"
            step="any"
            value={condition.threshold || 0}
            onChange={(e) => onUpdate({ threshold: parseFloat(e.target.value) || 0 })}
            className="w-24"
            placeholder="Threshold"
          />
        </div>
      )}

      {type === 'price_action' && (
        <div className="flex-1 flex items-center gap-2">
          <select
            value={condition.price_relation || ''}
            onChange={(e) => onUpdate({ price_relation: e.target.value })}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm flex-1"
          >
            <option value="">Select Condition</option>
            <option value="above_vwap">Price Above VWAP</option>
            <option value="below_vwap">Price Below VWAP</option>
            <option value="breakout_high">Breakout High</option>
            <option value="breakout_low">Breakout Low</option>
            <option value="retest_support">Retest Support</option>
            <option value="retest_resistance">Retest Resistance</option>
          </select>
        </div>
      )}

      {type === 'volume' && (
        <div className="flex-1 flex items-center gap-2">
          <select
            value={condition.volume_condition || ''}
            onChange={(e) => onUpdate({ volume_condition: e.target.value })}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm flex-1"
          >
            <option value="">Select Condition</option>
            <option value="volume_spike">Volume Spike</option>
            <option value="volume_dry_up">Volume Dry Up</option>
            <option value="increasing_volume">Increasing Volume</option>
            <option value="decreasing_volume">Decreasing Volume</option>
          </select>
          <Input
            type="number"
            step="0.1"
            value={condition.volume_multiplier || 2}
            onChange={(e) => onUpdate({ volume_multiplier: parseFloat(e.target.value) || 2 })}
            className="w-24"
            placeholder="Multiplier"
          />
        </div>
      )}

      {type === 'trend' && (
        <div className="flex-1 flex items-center gap-2">
          <select
            value={condition.trend_condition || ''}
            onChange={(e) => onUpdate({ trend_condition: e.target.value })}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm flex-1"
          >
            <option value="">Select Condition</option>
            <option value="strong_uptrend">Strong Uptrend</option>
            <option value="weak_uptrend">Weak Uptrend</option>
            <option value="strong_downtrend">Strong Downtrend</option>
            <option value="weak_downtrend">Weak Downtrend</option>
            <option value="adx_above">ADX Above</option>
          </select>
          <Input
            type="number"
            step="1"
            value={condition.adx_threshold || 25}
            onChange={(e) => onUpdate({ adx_threshold: parseInt(e.target.value) || 25 })}
            className="w-24"
            placeholder="ADX Threshold"
          />
        </div>
      )}

      {type === 'regime' && (
        <div className="flex-1 flex items-center gap-2">
          <select
            value={condition.regime || ''}
            onChange={(e) => onUpdate({ regime: e.target.value })}
            className="h-8 rounded-md border border-input bg-background px-2 text-sm flex-1"
          >
            <option value="">Select Regime</option>
            <option value="trending">Trending</option>
            <option value="ranging">Ranging</option>
            <option value="volatile">Volatile</option>
            <option value="breakout">Breakout</option>
            <option value="reversal">Reversal</option>
          </select>
        </div>
      )}

      {/* Remove Button */}
      <button
        onClick={onRemove}
        className="p-2 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
        title="Remove condition"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

// Need to import icons
import { formatCurrency } from '../utils/format';
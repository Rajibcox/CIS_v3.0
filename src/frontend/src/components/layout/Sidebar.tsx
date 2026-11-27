import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';
import {
  LayoutDashboard,
  BarChart2,
  Search,
  TrendingUp,
  TrendingDown,
  Zap,
  Clock,
  List,
  Settings,
  Layers,
  Brain,
  BarChart3,
  Shield,
  Terminal,
  FileText,
  LineChart,
  FlaskConical,
  MessageSquare,
  Cpu,
  HardDrive,
  RotateCcw,
  Activity,
  ShieldCheck,
  Database,
  Bell,
  User,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  {
    name: 'Market Intelligence',
    icon: BarChart2,
    children: [
      { name: 'Market Overview', href: '/market' },
      { name: 'Scanner', href: '/market/scanner' },
      { name: 'LONG Opportunities', href: '/market/long' },
      { name: 'SHORT Opportunities', href: '/market/short' },
    ],
  },
  {
    name: 'Signals',
    icon: Zap,
    children: [
      { name: 'Signal Center', href: '/signals' },
      { name: 'Signal History', href: '/signals/history' },
    ],
  },
  {
    name: 'Strategies',
    icon: Layers,
    children: [
      { name: 'Strategy Center', href: '/strategies' },
      { name: 'Visual Builder', href: '/strategies/builder' },
      { name: 'Indicators', href: '/strategies/indicators' },
    ],
  },
  {
    name: 'Risk Management',
    icon: Shield,
    children: [
      { name: 'Leverage Intelligence', href: '/risk/leverage' },
      { name: 'Position Sizing', href: '/risk/position-sizing' },
      { name: 'Risk Limits', href: '/risk/limits' },
      { name: 'TP/SL Intelligence', href: '/risk/tp-sl' },
      { name: 'Profit Protection', href: '/risk/profit-protection' },
    ],
  },
  {
    name: 'Trading',
    icon: Terminal,
    children: [
      { name: 'Paper Trading', href: '/trading/paper' },
      { name: 'Portfolio', href: '/trading/portfolio' },
      { name: 'Open Positions', href: '/trading/positions' },
      { name: 'Order Management', href: '/trading/orders' },
      { name: 'Trade History', href: '/trading/history' },
    ],
  },
  {
    name: 'Analytics',
    icon: LineChart,
    children: [
      { name: 'PnL Analytics', href: '/analytics/pnl' },
      { name: 'Performance', href: '/analytics/performance' },
      { name: 'Backtesting', href: '/analytics/backtest' },
      { name: 'Walk-Forward', href: '/analytics/walkforward' },
      { name: 'Monte Carlo', href: '/analytics/montecarlo' },
    ],
  },
  {
    name: 'System',
    icon: Cpu,
    children: [
      { name: 'Exchange Connections', href: '/system/exchanges' },
      { name: 'Telegram Config', href: '/system/telegram' },
      { name: 'Notifications', href: '/system/notifications' },
      { name: 'Live Trading', href: '/system/live' },
      { name: 'Storage', href: '/system/storage' },
      { name: 'Backup & Restore', href: '/system/backup' },
      { name: 'System Health', href: '/system/health' },
      { name: 'Settings', href: '/system/settings' },
      { name: 'Audit Logs', href: '/system/audit' },
    ],
  },
];

interface SidebarProps {
  isCollapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ isCollapsed = false, onToggle }: SidebarProps) {
  const location = useLocation();

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  const isChildActive = (children: { href: string }[]) => {
    return children.some((child) => isActive(child.href));
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className={cn('flex h-16 items-center justify-center border-b px-4', isCollapsed && 'justify-center')}>
          {!isCollapsed && (
            <NavLink to="/" className="flex items-center space-x-2">
              <Activity className="h-6 w-6 text-primary" />
              <span className="font-bold text-xl">QUANTUM TRADER</span>
            </NavLink>
          )}
          {isCollapsed && <Activity className="h-6 w-6 text-primary" />}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1" role="navigation" aria-label="Main navigation">
          {navigation.map((item) => {
            const Icon = item.icon;
            const hasChildren = 'children' in item;

            if (!hasChildren) {
              const active = isActive(item.href);
              return (
                <NavLink
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    active
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isCollapsed && 'justify-center'
                  )}
                  title={isCollapsed ? item.name : undefined}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                  {!isCollapsed && <span>{item.name}</span>}
                </NavLink>
              );
            }

            const childActive = isChildActive(item.children);
            return (
              <div key={item.name} className={cn('group', isCollapsed && 'relative')}>
                <button
                  className={cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    childActive
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isCollapsed && 'justify-center'
                  )}
                  aria-expanded={!isCollapsed && childActive}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                  {!isCollapsed && <span>{item.name}</span>}
                  {!isCollapsed && (
                    <ChevronRight
                      className={cn(
                        'ml-auto h-4 w-4 transition-transform',
                        childActive && 'rotate-90'
                      )}
                      aria-hidden="true"
                    />
                  )}
                </button>

                {!isCollapsed && (
                  <div
                    className={cn(
                      'overflow-hidden transition-all duration-200',
                      childActive ? 'max-h-60 opacity-100' : 'max-h-0 opacity-0'
                    )}
                  >
                    <div className="mt-1 ml-8 space-y-0.5 border-l border-border pl-2">
                      {item.children.map((child) => {
                        const active = isActive(child.href);
                        return (
                          <NavLink
                            key={child.name}
                            to={child.href}
                            className={cn(
                              'block rounded-md px-2 py-1.5 text-xs font-medium transition-colors',
                              active
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                            )}
                            aria-current={active ? 'page' : undefined}
                          >
                            {child.name}
                          </NavLink>
                        );
                      })}
                    </div>
                  </div>
                )}

                {isCollapsed && childActive && (
                  <div className="absolute left-16 top-0 z-50 w-48 rounded-md border bg-popover p-1 shadow-lg animate-fade-in">
                    {item.children.map((child) => {
                      const active = isActive(child.href);
                      return (
                        <NavLink
                          key={child.name}
                          to={child.href}
                          className={cn(
                            'block rounded-md px-3 py-2 text-sm font-medium',
                            active
                              ? 'bg-primary text-primary-foreground'
                              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                          )}
                        >
                          {child.name}
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Footer - Version & Toggle */}
        <div className="border-t p-3">
          {!isCollapsed && (
            <div className="text-xs text-muted-foreground text-center">
              v1.0.0 | Paper Mode
            </div>
          )}
          <button
            onClick={onToggle}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors',
              isCollapsed && 'justify-center'
            )}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <>
                <ChevronLeft className="h-5 w-5" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
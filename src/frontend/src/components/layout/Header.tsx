import React from 'react';
import { cn } from '../../utils/cn';
import { Button } from '../common/Button';
import {
  Menu,
  Bell,
  Moon,
  Sun,
  Monitor,
  Wifi,
  WifiOff,
  AlertTriangle,
  Info,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Zap,
  Settings,
  LogOut,
  User,
  ChevronDown,
} from 'lucide-react';

interface HeaderProps {
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
  onThemeToggle: () => void;
  theme: 'light' | 'dark' | 'system';
}

export function Header({ onMenuClick, sidebarCollapsed, onThemeToggle, theme }: HeaderProps) {
  // Mock data - would come from useQuickStats hook
  const stats = {
    equity: 100.00,
    dailyPnl: 0.00,
    dailyPnlPct: 0.00,
    openPositions: 0,
    mode: 'paper' as const,
    status: 'healthy' as const,
  };

  const getPnlColor = (pnl: number) => (pnl >= 0 ? 'text-green-400' : 'text-red-400');
  const getPnlPrefix = (pnl: number) => (pnl >= 0 ? '+' : '');

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-30 h-16 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 transition-all duration-300',
        sidebarCollapsed ? 'left-16' : 'left-64'
      )}
    >
      <div className="flex h-full items-center justify-between px-4 gap-4">
        {/* Left: Menu + System Status */}
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="md:hidden"
            aria-label="Toggle menu"
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="hidden md:flex items-center gap-3">
            {/* Connection Status */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="absolute inset-0 rounded-full bg-green-500 animate-pulse" />
                <span className="relative rounded-full bg-green-500" />
              </span>
              <span className="text-muted-foreground">Connected</span>
            </div>

            {/* Trading Mode Badge */}
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                stats.mode === 'live' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'
              )}
            >
              {stats.mode.toUpperCase()}
            </span>

            {/* System Health */}
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                stats.status === 'healthy' ? 'bg-green-500/10 text-green-400' :
                stats.status === 'degraded' ? 'bg-yellow-500/10 text-yellow-400' :
                'bg-red-500/10 text-red-400'
              )}
            >
              {stats.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Center: Portfolio Quick Stats */}
        <div className="flex flex-1 items-center justify-center gap-6 md:gap-8">
          {/* Equity */}
          <div className="text-center">
            <p className="text-xs text-muted-foreground">EQUITY</p>
            <p className="text-lg font-mono font-semibold">{stats.equity.toFixed(2)} USDT</p>
          </div>

          {/* Daily PnL */}
          <div className="text-center">
            <p className="text-xs text-muted-foreground">DAILY P&L</p>
            <p className={cn('text-lg font-mono font-semibold', getPnlColor(stats.dailyPnl))}>
              {getPnlPrefix(stats.dailyPnl)}{stats.dailyPnl.toFixed(2)} ({getPnlPrefix(stats.dailyPnlPct)}{stats.dailyPnlPct.toFixed(2)}%)
            </p>
          </div>

          {/* Open Positions */}
          <div className="text-center">
            <p className="text-xs text-muted-foreground">POSITIONS</p>
            <p className="text-lg font-mono font-semibold">{stats.openPositions} / 2</p>
          </div>
        </div>

        {/* Right: Theme, Notifications, User */}
        <div className="flex items-center gap-2">
          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onThemeToggle}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          {/* Notifications */}
          <div className="relative">
            <Button variant="ghost" size="icon" aria-label="Notifications">
              <Bell className="h-5 w-5" />
            </Button>
            {/* Notification badge would go here */}
          </div>

          {/* User Menu */}
          <div className="relative">
            <Button variant="ghost" size="sm" className="gap-2" aria-label="User menu">
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                <User className="h-4 w-4 text-primary" />
              </div>
              <span className="hidden sm:block">Admin</span>
              <ChevronDown className="h-4 w-4" />
            </Button>

            {/* Dropdown would be implemented here */}
          </div>
        </div>
      </div>
    </header>
  );
}
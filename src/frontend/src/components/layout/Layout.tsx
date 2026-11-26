import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { cn } from '../../utils/cn';
import { useTheme } from '../../hooks/useTheme';

interface LayoutProps {
  children?: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { theme, toggleTheme } = useTheme();

  // Persist sidebar state
  useEffect(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    if (saved !== null) {
      setSidebarCollapsed(JSON.parse(saved));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(sidebarCollapsed));
  }, [sidebarCollapsed]);

  const handleSidebarToggle = () => {
    setSidebarCollapsed((prev) => !prev);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar isCollapsed={sidebarCollapsed} onToggle={handleSidebarToggle} />

      {/* Main Content */}
      <div className={cn('transition-all duration-300', sidebarCollapsed ? 'ml-16' : 'ml-64')}>
        {/* Header */}
        <Header
          onMenuClick={handleSidebarToggle}
          sidebarCollapsed={sidebarCollapsed}
          onThemeToggle={toggleTheme}
          theme={theme}
        />

        {/* Page Content */}
        <main
          className={cn(
            'pt-16 min-h-[calc(100vh-4rem)] transition-all duration-300',
            sidebarCollapsed ? 'ml-0' : 'ml-0'
          )}
        >
          <div className="p-4 md:p-6 lg:p-8">
            {children || <Outlet />}
          </div>
        </main>
      </div>
    </div>
  );
}
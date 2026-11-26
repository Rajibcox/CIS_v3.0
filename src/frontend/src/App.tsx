import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Layout } from './components/layout/Layout';
import { OverviewPage } from './pages/Overview';
import { MarketPage } from './pages/Market';
import { SignalsPage } from './pages/Signals';
import { StrategiesPage } from './pages/Strategies';
import { TradingPage } from './pages/Trading';
import { AnalyticsPage } from './pages/Analytics';
import { SystemPage } from './pages/System';
import { ConfigurationPage } from './pages/Configuration';
import { LoginPage } from './pages/Login';
import { ToastProvider, Toaster } from './components/common/Toast';
import { AuthProvider, useAuth } from './hooks/useAuth';

// Create QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: window.location.pathname }} replace />;
  }

  return <>{children}</>;
}

// Public Route (redirects if authenticated)
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<OverviewPage />} />
        <Route path="market" element={<MarketPage />} />
        <Route path="signals" element={<SignalsPage />} />
        <Route path="strategies" element={<StrategiesPage />} />
        <Route path="trading" element={<TradingPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="system" element={<SystemPage />} />
        <Route path="config" element={<ConfigurationPage />} />
        {/* Other routes will be added here */}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <AppRoutes />
            <Toaster />
            <ReactQueryDevtools initialIsOpen={false} />
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
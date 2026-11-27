import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface User {
  id: string;
  username: string;
  role: string;
  email?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          // In a real app, validate token with backend
          // For now, just set a mock user
          setUser({
            id: '1',
            username: 'admin',
            role: 'admin',
            email: 'admin@quantumtrader.local',
          });
        } catch {
          localStorage.removeItem('auth_token');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    // Mock login - in real app, call backend API
    // const response = await api.post('/auth/login', { username, password });
    // localStorage.setItem('auth_token', response.data.access_token);

    // Mock validation
    if (username === 'admin' && password === 'admin') {
      const mockUser: User = {
        id: '1',
        username: 'admin',
        role: 'admin',
        email: 'admin@quantumtrader.local',
      };
      localStorage.setItem('auth_token', 'mock-jwt-token-' + Date.now());
      setUser(mockUser);
    } else {
      throw new Error('Invalid credentials');
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setUser(null);
  }, []);

  const refreshToken = useCallback(async () => {
    // Mock refresh - in real app, call backend refresh endpoint
    const token = localStorage.getItem('auth_token');
    if (token) {
      // localStorage.setItem('auth_token', newToken);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, logout, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

interface User {
  id: string;
  username: string;
  role: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
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

function getApiErrorMessage(error: unknown): string {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error
  ) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === 'string') {
      return response.data.detail;
    }
  }
  return error instanceof Error ? error.message : 'Authentication failed';
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const initAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const currentUser = await api.get<User>('/auth/me');
          if (active) setUser(currentUser);
        } catch {
          localStorage.removeItem('auth_token');
          if (active) setUser(null);
        }
      }
      if (active) setIsLoading(false);
    };

    void initAuth();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await api.post<AuthResponse>('/auth/login', { username, password });
      if (!response.access_token || response.token_type.toLowerCase() !== 'bearer') {
        throw new Error('The authentication server returned an invalid response');
      }
      localStorage.setItem('auth_token', response.access_token);
      setUser(response.user);
    } catch (error) {
      localStorage.removeItem('auth_token');
      setUser(null);
      throw new Error(getApiErrorMessage(error));
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setUser(null);
  }, []);

  // The current backend issues short-lived access tokens but has no refresh
  // token endpoint. This method therefore revalidates the current session.
  const refreshToken = useCallback(async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setUser(null);
      return;
    }
    try {
      const currentUser = await api.get<User>('/auth/me');
      setUser(currentUser);
    } catch (error) {
      localStorage.removeItem('auth_token');
      setUser(null);
      throw new Error(getApiErrorMessage(error));
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

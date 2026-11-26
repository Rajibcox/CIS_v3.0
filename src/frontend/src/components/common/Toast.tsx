import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { cn } from '../../utils/cn';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';

// Types
interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success';
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
}

type ToastAction =
  | { type: 'ADD_TOAST'; toast: Toast }
  | { type: 'REMOVE_TOAST'; id: string };

const ToastContext = createContext<{
  toasts: Toast[];
  toast: (props: Omit<Toast, 'id'>) => void;
  dismiss: (id: string) => void;
} | null>(null);

// Reducer
function toastReducer(state: ToastState, action: ToastAction): ToastState {
  switch (action.type) {
    case 'ADD_TOAST':
      return { toasts: [...state.toasts, action.toast] };
    case 'REMOVE_TOAST':
      return { toasts: state.toasts.filter((t) => t.id !== action.id) };
    default:
      return state;
  }
}

// Provider
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(toastReducer, { toasts: [] });

  const toast = React.useCallback((props: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = { id, ...props };
    dispatch({ type: 'ADD_TOAST', toast: newToast });

    // Auto dismiss
    setTimeout(() => {
      dispatch({ type: 'REMOVE_TOAST', id });
    }, props.duration || 5000);
  }, []);

  const dismiss = React.useCallback((id: string) => {
    dispatch({ type: 'REMOVE_TOAST', id });
  }, []);

  return (
    <ToastContext.Provider value={{ toasts: state.toasts, toast, dismiss }}>
      {children}
      <ToastViewport toasts={state.toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Toast Viewport
function ToastViewport({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 gap-2 sm:max-w-[420px]">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

// Toast Item
function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const icons = {
    default: <Info className="h-5 w-5 text-blue-400" />,
    destructive: <AlertCircle className="h-5 w-5 text-red-400" />,
    success: <CheckCircle className="h-5 w-5 text-green-400" />,
  };

  const variantClasses = {
    default: 'border-l-4 border-blue-500',
    destructive: 'border-l-4 border-red-500',
    success: 'border-l-4 border-green-500',
  };

  return (
    <div
      className={cn(
        'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-4 pr-8 shadow-lg animate-in fade-in-80 slide-in-from-top-2',
        variantClasses[toast.variant || 'default']
      )}
    >
      <div className="grid gap-1">
        <div className="flex items-center gap-2">
          {icons[toast.variant || 'default']}
          <ToastTitle>{toast.title}</ToastTitle>
        </div>
        {toast.description && <ToastDescription>{toast.description}</ToastDescription>}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

function ToastTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-sm font-semibold">{children}</div>;
}

function ToastDescription({ children }: { children: React.ReactNode }) {
  return <div className="text-sm opacity-90">{children}</div>;
}

// Simple Toaster component for App.tsx
export function Toaster() {
  const { toasts } = useToast();
  return <ToastViewport toasts={toasts} onDismiss={() => {}} />;
}
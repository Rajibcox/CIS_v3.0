import { useState, useEffect, useCallback, useRef } from 'react';

interface WSMessage {
  type: string;
  channel: string;
  data: any;
  timestamp: string;
  request_id?: string;
}

interface UseWebSocketOptions {
  url?: string;
  onOpen?: () => void;
  onClose?: (event?: CloseEvent) => void;
  onError?: (error: Event) => void;
  onMessage?: (message: any) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  autoConnect?: boolean;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = 'ws://localhost:8000/ws',
    onOpen,
    onClose,
    onError,
    onMessage,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
    autoConnect = true
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<any>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const messageHandlersRef = useRef<Map<string, (data: any) => void>>(new Map());
  const requestCallbacksRef = useRef<Map<string, (data: any) => void>>(new Map());
  const requestIdCounter = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket('ws://localhost:8000/ws');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        console.log('WebSocket connected');

        // Subscribe to default channels
        subscribe('ticker:BTCUSDT');
        subscribe('ticker:ETHUSDT');
        subscribe('signal');
        subscribe('trade');
        subscribe('position');
        subscribe('pnl');
        subscribe('system');

        if (onOpen) onOpen();
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        console.log('WebSocket disconnected:', event.code, event.reason);
        if (onClose) onClose(event);

        // Attempt reconnection
        if (reconnectAttemptsRef.current < 10) {
          setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, 5000);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (onError) onError(error);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle response to request
          if (message.request_id && requestCallbacksRef.current.has(message.request_id)) {
            const callback = requestCallbacksRef.current.get(message.request_id);
            if (callback) {
              callback(message);
              requestCallbacksRef.current.delete(message.request_id);
            }
          }

          // Handle channel messages
          if (message.channel && messageHandlersRef.current.has(message.channel)) {
            messageHandlersRef.current.get(message.channel)!(message.data);
          }

          // Handle by type
          if (message.type && messageHandlersRef.current.has(message.type)) {
            messageHandlersRef.current.get(message.type)!(message.data);
          }

          // Default handler
          if (onMessage) onMessage(message);

          setLastMessage(message);
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }, []);

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
  };

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const subscribe = useCallback((channel: string, params?: any) => {
    return send({
      type: 'subscribe',
      channel,
      params: params || {}
    });
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    return send({
      type: 'unsubscribe',
      channel
    });
  }, []);

  const request = useCallback((payload: any): Promise<any> => {
    return new Promise((resolve, reject) => {
      const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const message = { ...payload, request_id: payload.request_id || requestId };

      const timeout = setTimeout(() => {
        requestCallbacksRef.current.delete(message.request_id);
        reject(new Error('Request timeout'));
      }, 10000);

      requestCallbacksRef.current.set(message.request_id, (response: any) => {
        clearTimeout(timeout);
        resolve(response);
      });

      if (!send({ ...message, request_id: message.request_id })) {
        clearTimeout(timeout);
        requestCallbacksRef.current.delete(message.request_id);
        reject(new Error('Not connected'));
      }
    });
  }, []);

  const on = useCallback((eventType: string, handler: (data: any) => void) => {
    messageHandlersRef.current.set(eventType, handler);
    return () => messageHandlersRef.current.delete(eventType);
  }, []);

  const onChannel = useCallback((channel: string, handler: (data: any) => void) => {
    messageHandlersRef.current.set(channel, handler);
    return () => messageHandlersRef.current.delete(channel);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect]);

  // Reconnection logic
  useEffect(() => {
    if (!autoConnect) return;

    const interval = setInterval(() => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        connect();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [autoConnect]);

  return {
    isConnected,
    connectionError,
    lastMessage,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    request,
    on,
    onChannel,
    isReady: wsRef.current?.readyState === WebSocket.OPEN
  };
}

// Hook for subscribing to specific channels with typed data
export function useChannel<T>(channel: string, initialData?: T) {
  const [data, setData] = useState<T | undefined>(initialData);
  const { onChannel, subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    subscribe(channel);

    return () => {
      unsubscribe(channel);
    };
  }, [isConnected]);

  return data;
}

// Hook for real-time ticker data
export function useTicker(symbol: string) {
  const [ticker, setTicker] = useState<any>(null);
  const { onChannel, subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const channel = `ticker:${symbol}`;
    const unsubscribeHandler = onChannel(channel, (data: any) => {
      setTicker(data);
    });

    subscribe(channel);

    return () => {
      unsubscribe(channel);
    };
  }, [isConnected, symbol]);

  return ticker;
}

// Hook for real-time signals
export function useSignals() {
  const [signals, setSignals] = useState<any[]>([]);
  const { onChannel, subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeHandler = onChannel('signal', (data: any) => {
      setSignals(prev => [data, ...prev.slice(0, 49)]); // Keep last 50
    });

    subscribe('signal');

    return () => {
      unsubscribe('signal');
    };
  }, [isConnected]);

  return signals;
}

// Hook for real-time positions
export function usePositions() {
  const [positions, setPositions] = useState<any[]>([]);
  const { onChannel, subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeHandler = onChannel('position', (data: any) => {
      setPositions(prev => {
        // Update or add position
        const exists = prev.findIndex(p => p.position_id === data.position_id);
        if (exists >= 0) {
          const newPositions = [...prev];
          newPositions[exists] = data;
          return newPositions;
        }
        return [data, ...prev];
      });
    });

    subscribe('position');

    return () => {
      unsubscribe('position');
    };
  }, [isConnected]);

  return positions;
}

// Hook for real-time PnL
export function usePnL() {
  const [pnl, setPnL] = useState<any>(null);
  const { onChannel, subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeHandler = onChannel('pnl', (data: any) => {
      setPnL(data);
    });

    subscribe('pnl');

    return () => {
      unsubscribe('pnl');
    };
  }, [isConnected]);

  return pnl;
}

// Hook for system status
export function useSystemStatus() {
  const [status, setStatus] = useState<any>(null);
  const { onChannel, subscribe, unsubscribe, isConnected } = useWebSocket();

  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeHandler = onChannel('system', (data: any) => {
      setStatus(data);
    });

    subscribe('system');

    return () => {
      unsubscribe('system');
    };
  }, [isConnected]);

  return status;
}

export default useWebSocket;
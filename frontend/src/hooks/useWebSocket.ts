import { useEffect, useRef, useState } from 'react';

export interface UseWebSocketReturn {
  sendMessage: (message: string) => void;
  lastMessage: MessageEvent | null;
  connectionStatus: 'Connecting' | 'Open' | 'Closing' | 'Closed';
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [connectionStatus, setConnectionStatus] = useState<'Connecting' | 'Open' | 'Closing' | 'Closed'>('Closed');
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!url) return;

    ws.current = new WebSocket(url);
    setConnectionStatus('Connecting');

    ws.current.onopen = () => {
      setConnectionStatus('Open');
    };

    ws.current.onclose = () => {
      setConnectionStatus('Closed');
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onmessage = (event) => {
      setLastMessage(event);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendMessage = (message: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message);
    } else {
      console.warn('WebSocket is not open. Ready state:', ws.current?.readyState);
    }
  };

  return {
    sendMessage,
    lastMessage,
    connectionStatus
  };
};
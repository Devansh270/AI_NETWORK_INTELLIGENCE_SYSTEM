import { useEffect, useMemo, useState } from "react";
import { createMockMetricsStream, createMockTopologyStream, shouldUseMockData } from '../services/mockData';

const socketStores = new Map();

function getStore(path) {
  if (!socketStores.has(path)) {
    socketStores.set(path, {
      socket: null,
      data: null,
      connected: false,
      connectionStatus: "connecting",
      messageHistory: [],
      listeners: new Set(),
    });
  }

  return socketStores.get(path);
}

function notify(store) {
  store.listeners.forEach((listener) => listener());
}

function resetStore(store) {
  store.data = null;
  store.connected = false;
  store.connectionStatus = "connecting";
  store.messageHistory = [];
  if (store.socket) {
    try {
      store.socket.close();
    } catch (error) {
      console.warn("Failed to close WebSocket during reset", error);
    }
    store.socket = null;
  }
}

export function useWebSocket(path) {
  const store = useMemo(() => getStore(path), [path]);
  const [, forceRender] = useState(0);

  useEffect(() => {
    const listener = () => forceRender((value) => value + 1);
    store.listeners.add(listener);

    if (!store.socket) {
      if (shouldUseMockData()) {
        console.log("[useWebSocket] Mock mode enabled for", path);
        store.connected = true;
        store.connectionStatus = "connected";
        notify(store);

        const mockStream = path.includes('/topology/ws')
          ? createMockTopologyStream((payload) => {
              store.data = payload;
              store.messageHistory = [...store.messageHistory, payload].slice(-100);
              notify(store);
            })
          : createMockMetricsStream((payload) => {
              store.data = payload;
              store.messageHistory = [...store.messageHistory, payload].slice(-100);
              notify(store);
            });

        store.socket = { close: () => mockStream() };
        notify(store);
      } else {
        const ws = new WebSocket(path);
        store.socket = ws;
        store.connectionStatus = "connecting";
        notify(store);

        ws.onopen = () => {
          store.connected = true;
          store.connectionStatus = "connected";
          notify(store);
        };

        ws.onmessage = (event) => {
          let parsed = null;
          try {
            parsed = JSON.parse(event.data);
          } catch (error) {
            console.warn("WebSocket message was not valid JSON", error);
            parsed = null;
          }

          store.data = parsed;
          store.messageHistory = [...store.messageHistory, parsed].slice(-100);
          notify(store);
        };

        ws.onclose = () => {
          store.connected = false;
          store.connectionStatus = "disconnected";
          notify(store);
        };

        ws.onerror = () => {
          store.connected = false;
          store.connectionStatus = "error";
          notify(store);
        };
      }
    } else {
      notify(store);
    }

    return () => {
      store.listeners.delete(listener);
      if (store.listeners.size === 0) {
        resetStore(store);
      }
    };
  }, [path, store]);

  return {
    data: store.data,
    connected: store.connected,
    lastMessage: store.data,
    connectionStatus: store.connectionStatus,
    messageHistory: store.messageHistory,
  };
}
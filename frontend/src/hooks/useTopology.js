import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL, WS_BASE_URL } from "../services/config";
import { mockTopology, shouldUseMockData } from "../services/mockData";
import { useWebSocket } from "./useWebSocket";

export function useTopology() {
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const { lastMessage, connectionStatus } = useWebSocket(`${WS_BASE_URL}/topology/ws`);

  useEffect(() => {
    if (lastMessage && typeof lastMessage === "object" && "nodes" in lastMessage) {
      setTopology(lastMessage);
    }
  }, [lastMessage]);

  useEffect(() => {
    let cancelled = false;

    if (shouldUseMockData()) {
      setTopology(mockTopology);
      return () => {
        cancelled = true;
      };
    }

    fetch(`${API_BASE_URL}/topology`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Topology request failed: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!cancelled && data && typeof data === "object" && "nodes" in data) {
          setTopology(data);
        }
      })
      .catch((error) => {
        console.warn("[topology] REST fallback failed", error);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectNode = useCallback((node) => {
    setSelectedNode((prev) => (prev?.id === node?.id ? null : node));
  }, []);

  return {
    topology,
    selectedNode,
    selectNode,
    connectionStatus,
  };
}
import { useRef, useCallback, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useTopology } from "../hooks/useTopology";

const UTILIZATION_COLOR = (util) => {
  if (util < 0.4) return "#22c55e";   // green
  if (util < 0.7) return "#f59e0b";   // amber
  return "#ef4444";                    // red
};

const NODE_COLOR = (node) => {
  if (node.type === "switch") return "#6366f1"; // indigo
  return "#3b82f6";                              // blue
};

export default function TopologyGraph() {
  const graphRef = useRef();
  const { topology, connectionStatus } = useTopology();
  const [selectedNode, setSelectedNode] = useState(null);

  const selectNode = useCallback((node) => {
    setSelectedNode((prev) => (prev?.id === node?.id ? null : node));
  }, []);

  const graphData = {
    nodes: (topology.nodes || []).map((n) => ({ ...n, label: n.label || n.id })),
    links: (topology.edges || []).map((e) => ({
      source: e.source,
      target: e.target,
      utilization: e.utilization ?? 0,
      bandwidth: e.bw_mbps ?? e.bandwidth ?? 10,
    })),
  };

  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      setTimeout(() => graphRef.current.zoomToFit(400), 300);
    }
  }, [topology.nodes?.length]);

  const handleNodeClick = useCallback(
    (node) => {
      console.log("[topology] node clicked:", node);
      selectNode(node);
    },
    [selectNode]
  );

  const drawNode = useCallback(
    (node, ctx, globalScale) => {
      const radius = node.type === "switch" ? 10 : 7;
      const isSelected = selectedNode?.id === node.id;

      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = NODE_COLOR(node);
      ctx.fill();

      const label = node.label;
      const fontSize = Math.max(10 / globalScale, 4);
      ctx.font = `${fontSize}px Sans-Serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#ffffff";
      ctx.fillText(label, node.x, node.y + radius + fontSize + 1);
    },
    [selectedNode]
  );

  const drawLink = useCallback((link, ctx) => {
    const util = link.utilization ?? 0;
    ctx.strokeStyle = UTILIZATION_COLOR(util);
    ctx.lineWidth = 2 + util * 3;
    ctx.beginPath();
    ctx.moveTo(link.source.x, link.source.y);
    ctx.lineTo(link.target.x, link.target.y);
    ctx.stroke();

    const mx = (link.source.x + link.target.x) / 2;
    const my = (link.source.y + link.target.y) / 2;
    ctx.fillStyle = UTILIZATION_COLOR(util);
    ctx.font = "8px Sans-Serif";
    ctx.textAlign = "center";
    ctx.fillText(`${Math.round(util * 100)}%`, mx, my);
  }, []);

  return (
    <div className="relative w-full h-full bg-gray-900 rounded-xl overflow-hidden border border-gray-700" style={{ minHeight: "500px" }}>
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${
            connectionStatus === "connected"
              ? "bg-green-400"
              : connectionStatus === "reconnecting"
              ? "bg-yellow-400 animate-pulse"
              : "bg-red-400"
          }`}
        />
        <span className="text-xs text-gray-400">
          {connectionStatus === "connected"
            ? `${topology.nodes?.length || 0} nodes - ${topology.edges?.length || 0} links`
            : connectionStatus}
        </span>
      </div>

      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1 bg-gray-800 rounded-lg p-2 text-xs text-gray-300">
        <div className="flex items-center gap-2">
          <span className="w-3 h-1 rounded" style={{ background: "#22c55e" }} />
          &lt; 40% utilized
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-1 rounded" style={{ background: "#f59e0b" }} />
          40-70%
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-1 rounded" style={{ background: "#ef4444" }} />
          &gt; 70% (congested)
        </div>
      </div>

      {graphData.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
          Waiting for topology data...
        </div>
      )}

      {selectedNode && (
        <div className="absolute bottom-4 left-4 z-10 bg-gray-800 border border-gray-600 rounded-xl p-4 w-56 shadow-xl">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-white font-semibold">{selectedNode.id}</h3>
            <button
              onClick={() => selectNode(null)}
              className="text-gray-400 hover:text-white text-xs"
            >
              X
            </button>
          </div>
          <div className="space-y-1 text-xs text-gray-300">
            <div>
              <span className="text-gray-500">Type: </span>
              <span className="capitalize">{selectedNode.type}</span>
            </div>
            {selectedNode.ip && (
              <div>
                <span className="text-gray-500">IP: </span>
                {selectedNode.ip}
              </div>
            )}
          </div>
        </div>
      )}

      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeCanvasObject={drawNode}
        linkCanvasObject={drawLink}
        nodeCanvasObjectMode={() => "replace"}
        linkCanvasObjectMode={() => "replace"}
        nodePointerAreaPaint={(node, color, ctx) => {
          const radius = node.type === "switch" ? 10 : 7;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI);
          ctx.fill();
        }}
        onNodeClick={handleNodeClick}
        backgroundColor="#111827"
        cooldownTicks={100}
        nodeRelSize={6}
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleColor={(link) =>
          UTILIZATION_COLOR(link.utilization ?? 0)
        }
      />
    </div>
  );
}

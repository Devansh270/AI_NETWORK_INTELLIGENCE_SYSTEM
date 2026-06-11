import { useState, useEffect } from "react";

const severityStyle = {
  normal:    "bg-green-100 text-green-800",
  warning:   "bg-yellow-100 text-yellow-800",
  critical:  "bg-red-100 text-red-800",
  CONGESTED: "bg-orange-100 text-orange-800",
  NORMAL:    "bg-green-100 text-green-800",
};

function Gauge({ score, label }) {
  const pct   = Math.min(Math.round(score * 100), 100);
  const color = pct < 50 ? "#22c55e" : pct < 75 ? "#f59e0b" : "#ef4444";
  const dash  = pct * 2.51;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="12" />
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeDasharray={`${dash} 251`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold" style={{ color }}>{pct}%</span>
        </div>
      </div>
      <span className="text-xs text-gray-500 font-medium text-center">{label}</span>
    </div>
  );
}

export default function PredictionsPanel() {
  const [history, setHistory]     = useState([]);
  const [congestion, setCongestion] = useState(null);
  const [anomaly, setAnomaly]       = useState(null);
  const [wsStatus, setWsStatus]     = useState("connecting");

  // Load last 20 predictions on mount
  useEffect(() => {
    fetch("/api/predict/predictions/latest")
      .then(r => r.json())
      .then(data => {
        setHistory(data);
        const c = data.find(p => p.model === "xgboost-congestion");
        const a = data.find(p => p.model === "lstm-anomaly");
        if (c) setCongestion(c);
        if (a) setAnomaly(a);
      })
      .catch(err => console.warn("Could not load predictions:", err));
  }, []);

  // Live updates from Redis via WebSocket
  useEffect(() => {
    const host = window.location.hostname;
    const ws   = new WebSocket(`ws://${host}:8000/ws/predictions`);

    ws.onopen    = () => setWsStatus("live");
    ws.onclose   = () => setWsStatus("disconnected");
    ws.onerror   = () => setWsStatus("error");

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const entry = {
          model:     msg.model,
          score:     msg.score,
          is_alert:  msg.is_alert,
          severity:  msg.severity ?? (msg.is_alert ? "warning" : "normal"),
          timestamp: msg.ts,
        };

        if (msg.model === "xgboost-congestion") setCongestion(entry);
        if (msg.model === "lstm-anomaly")       setAnomaly(entry);

        setHistory(prev => [entry, ...prev].slice(0, 20));
      } catch {}
    };

    return () => ws.close();
  }, []);

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">ML Predictions</h2>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          wsStatus === "live" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"
        }`}>
          {wsStatus}
        </span>
      </div>

      {/* Gauges */}
      <div className="flex justify-around mb-5">
        <Gauge score={congestion?.score ?? 0} label="Congestion Risk" />
        <Gauge score={anomaly?.score ?? 0}    label="Anomaly Score"   />
      </div>

      {/* Current severity badges */}
      <div className="flex gap-2 flex-wrap mb-4">
        {congestion && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${severityStyle[congestion.severity] ?? "bg-gray-100 text-gray-600"}`}>
            Congestion: {congestion.severity?.toUpperCase()}
          </span>
        )}
        {anomaly && (
          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${severityStyle[anomaly.severity] ?? "bg-gray-100 text-gray-600"}`}>
            Anomaly: {anomaly.severity?.toUpperCase()}
          </span>
        )}
      </div>

      {/* History list */}
      <div>
        <p className="text-xs font-medium text-gray-400 mb-1">Recent</p>
        <div className="space-y-1 max-h-36 overflow-y-auto">
          {history.length === 0 && (
            <p className="text-xs text-gray-400">Waiting for first inference cycle (5s)...</p>
          )}
          {history.map((p, i) => (
            <div key={i} className="flex items-center justify-between text-xs border-b pb-1 last:border-0">
              <span className="font-mono text-gray-500 truncate w-36">{p.model}</span>
              <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${severityStyle[p.severity] ?? "bg-gray-100 text-gray-500"}`}>
                {(p.score * 100).toFixed(1)}%
              </span>
              <span className="text-gray-300 text-xs">
                {p.timestamp ? new Date(p.timestamp).toLocaleTimeString() : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
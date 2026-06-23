import { useEffect, useState } from "react";

const STATUS_COLORS = {
  ok: "#22c55e",
  degraded: "#eab308",
  down: "#ef4444",
};

export default function SystemHealth({ pollIntervalMs = 5000 }) {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/health");
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setHealth(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }

    poll();
    const id = setInterval(poll, pollIntervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollIntervalMs]);

  if (error) {
    return <div className="text-sm text-red-500">Health check unreachable: {error}</div>;
  }
  if (!health) {
    return <div className="text-sm text-gray-400">Checking system health...</div>;
  }

  return (
    <div className="flex gap-4 items-center p-3 rounded-lg border border-gray-700">
      {Object.entries(health.services).map(([name, info]) => (
        <div key={name} className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full inline-block"
            style={{ backgroundColor: STATUS_COLORS[info.status] || "#6b7280" }}
          />
          <span className="text-sm capitalize">{name}</span>
        </div>
      ))}
    </div>
  );
}
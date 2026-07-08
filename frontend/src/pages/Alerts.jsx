import { useEffect, useState } from "react";
import { mockAlerts, shouldUseMockData } from '../services/mockData';

const SEVERITY_STYLES = {
  critical: "bg-red-500/15 text-red-400 border border-red-500/30",
  warning: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
  info: "bg-sky-500/15 text-sky-400 border border-sky-500/30",
};

function SeverityBadge({ severity }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${style}`}>
      {severity}
    </span>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadAlerts() {
      setLoading(true);
      setError(null);
      try {
        if (shouldUseMockData()) {
          if (!cancelled) {
            setAlerts(mockAlerts);
            setTotal(mockAlerts.length);
          }
          return;
        }

        const skip = (page - 1) * pageSize;
        const res = await fetch(`/api/alerts?skip=${skip}&limit=${pageSize}`);
        if (!res.ok) {
          throw new Error(`API error: ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setAlerts(data.alerts || []);
          setTotal(data.alerts?.length ? data.alerts.length + skip : 0);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAlerts();
    const timer = window.setInterval(() => {
      loadAlerts();
    }, 15000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [page, pageSize]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="text-white p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Alerts</h1>
        {!loading && !error && (
          <span className="text-sm text-white/50">{total} total</span>
        )}
      </div>

      {loading && (
        <div className="text-white/60 text-sm">Loading alerts…</div>
      )}

      {!loading && error && (
        <div className="rounded border border-red-500/30 bg-red-500/10 text-red-400 text-sm px-4 py-3">
          Failed to load alerts: {error}
        </div>
      )}

      {!loading && !error && alerts.length === 0 && (
        <div className="text-white/60 text-sm">No alerts yet.</div>
      )}

      {!loading && !error && alerts.length > 0 && (
        <>
          <div className="overflow-x-auto rounded border border-white/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/50 border-b border-white/10">
                  <th className="px-4 py-2 font-medium">Time</th>
                  <th className="px-4 py-2 font-medium">Type</th>
                  <th className="px-4 py-2 font-medium">Severity</th>
                  <th className="px-4 py-2 font-medium">Score</th>
                  <th className="px-4 py-2 font-medium">Message</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id} className="border-b border-white/5 last:border-0">
                    <td className="px-4 py-2 whitespace-nowrap text-white/70">
                      {new Date(a.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 capitalize">{a.type}</td>
                    <td className="px-4 py-2">
                      <SeverityBadge severity={a.severity} />
                    </td>
                    <td className="px-4 py-2 font-mono text-white/80">
                      {a.score?.toFixed ? a.score.toFixed(2) : a.score}
                    </td>
                    <td className="px-4 py-2 text-white/70">{a.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4 text-sm text-white/60">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 rounded border border-white/10 disabled:opacity-30 hover:bg-white/5"
            >
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded border border-white/10 disabled:opacity-30 hover:bg-white/5"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
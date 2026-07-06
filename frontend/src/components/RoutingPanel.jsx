import { useState, useEffect } from "react";
import { API_BASE_URL } from "../services/config";

const API_BASE = "/api";

const PRIORITY_LABELS = {
  1: "Critical",
  2: "High",
  3: "Normal",
  4: "Low",
  5: "Background",
};

const PRIORITY_COLORS = {
  1: "bg-red-500",
  2: "bg-orange-400",
  3: "bg-yellow-400",
  4: "bg-blue-400",
  5: "bg-gray-400",
};

export default function RoutingPanel() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    protocol: "TCP",
    dst_port: "",
    priority: 3,
    bandwidth_limit_kbps: "",
    active: true,
  });

  const fetchRules = async () => {
    try {
      const res = await fetch(`${API_BASE}/routing-rules/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRules(data);
    } catch (e) {
      console.error("Failed to fetch rules:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
    const interval = setInterval(fetchRules, 5000);
    return () => clearInterval(interval);
  }, []);

  const createRule = async () => {
    if (!form.name.trim()) {
      alert("Rule name is required");
      return;
    }
    const payload = {
      ...form,
      dst_port: form.dst_port ? parseInt(form.dst_port) : null,
      bandwidth_limit_kbps: form.bandwidth_limit_kbps
        ? parseInt(form.bandwidth_limit_kbps)
        : null,
      priority: parseInt(form.priority),
    };
    try {
      const res = await fetch(`${API_BASE}/routing-rules/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowForm(false);
      setForm({
        name: "",
        protocol: "TCP",
        dst_port: "",
        priority: 3,
        bandwidth_limit_kbps: "",
        active: true,
      });
      fetchRules();
    } catch (e) {
      console.error("Failed to create rule:", e);
      alert("Failed to create rule. Check console.");
    }
  };

  const toggleRule = async (rule) => {
    try {
      await fetch(`${API_BASE}/routing-rules/${rule.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...rule, active: !rule.active }),
      });
      fetchRules();
    } catch (e) {
      console.error("Failed to toggle rule:", e);
    }
  };

  const deleteRule = async (id) => {
    if (!window.confirm("Delete this rule?")) return;
    try {
      await fetch(`${API_BASE}/routing-rules/${id}`, { method: "DELETE" });
      fetchRules();
    } catch (e) {
      console.error("Failed to delete rule:", e);
    }
  };

  if (loading) {
    return <div className="p-4 text-gray-400">Loading rules...</div>;
  }

  return (
    <div className="p-4 bg-gray-900 rounded-lg text-white">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Traffic Routing Rules</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
        >
          {showForm ? "Cancel" : "+ New Rule"}
        </button>
      </div>

      {showForm && (
        <div className="mb-4 p-3 bg-gray-800 rounded space-y-2">
          <input
            className="w-full bg-gray-700 rounded px-2 py-1 text-sm"
            placeholder="Rule name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <div className="flex gap-2 flex-wrap">
            <select
              className="bg-gray-700 rounded px-2 py-1 text-sm"
              value={form.protocol}
              onChange={(e) => setForm({ ...form, protocol: e.target.value })}
            >
              <option>TCP</option>
              <option>UDP</option>
              <option>ICMP</option>
            </select>
            <input
              className="bg-gray-700 rounded px-2 py-1 text-sm w-28"
              placeholder="Port (opt)"
              value={form.dst_port}
              onChange={(e) => setForm({ ...form, dst_port: e.target.value })}
            />
            <select
              className="bg-gray-700 rounded px-2 py-1 text-sm"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
            >
              {[1, 2, 3, 4, 5].map((p) => (
                <option key={p} value={p}>
                  Priority {p} - {PRIORITY_LABELS[p]}
                </option>
              ))}
            </select>
          </div>
          <input
            className="w-full bg-gray-700 rounded px-2 py-1 text-sm"
            placeholder="Bandwidth limit kbps (optional)"
            value={form.bandwidth_limit_kbps}
            onChange={(e) =>
              setForm({ ...form, bandwidth_limit_kbps: e.target.value })
            }
          />
          <div className="flex gap-2">
            <button
              onClick={createRule}
              className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-sm"
            >
              Save Rule
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {rules.length === 0 && (
          <p className="text-gray-500 text-sm">No rules configured.</p>
        )}
        {rules.map((rule) => (
          <div
            key={rule.id}
            className={`flex items-center justify-between p-3 rounded ${
              rule.active ? "bg-gray-800" : "bg-gray-800 opacity-50"
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`w-2 h-2 rounded-full ${
                  rule.active ? "bg-green-400" : "bg-gray-500"
                }`}
              />
              <div>
                <p className="text-sm font-medium">{rule.name}</p>
                <p className="text-xs text-gray-400">
                  {rule.protocol}
                  {rule.dst_port ? `:${rule.dst_port}` : " (all ports)"}
                  {rule.bandwidth_limit_kbps
                    ? ` - ${rule.bandwidth_limit_kbps} kbps limit`
                    : ""}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold ${
                  PRIORITY_COLORS[rule.priority]
                }`}
              >
                P{rule.priority} {PRIORITY_LABELS[rule.priority]}
              </span>
              <button
                onClick={() => toggleRule(rule)}
                className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
              >
                {rule.active ? "Disable" : "Enable"}
              </button>
              <button
                onClick={() => deleteRule(rule.id)}
                className="text-xs px-2 py-1 bg-red-800 hover:bg-red-700 rounded"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

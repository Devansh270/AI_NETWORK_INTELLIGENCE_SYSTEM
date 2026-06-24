import { useEffect, useState } from "react";

export default function TelemetryExport() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const interval = setInterval(async () => {
      const res = await fetch("/api/telemetry/logs");
      const data = await res.json();
      setLogs(data);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-black text-green-400 font-mono text-xs p-3 rounded h-64 overflow-y-scroll">
      {logs.map((line, i) => (
        <div key={i}>{JSON.stringify(line)}</div>
      ))}
    </div>
  );
}
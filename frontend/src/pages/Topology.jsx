import TopologyGraph from "../components/TopologyGraph";

export default function TopologyPage() {
  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Network Topology</h1>
        <p className="text-gray-400 text-sm mt-1">
          Live view of the simulated network. Click any node to inspect it. Edge color shows link utilization.
        </p>
      </div>
      <div className="flex-1 min-h-0" style={{ minHeight: "500px" }}>
        <TopologyGraph />
      </div>
    </div>
  );
}

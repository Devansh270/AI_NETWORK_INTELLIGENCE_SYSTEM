import MetricsPanel from '../components/MetricsPanel'
import ProtocolBreakdown from '../components/ProtocolBreakdown'
import PredictionsPanel from "../components/PredictionsPanel";


export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <MetricsPanel />
      <ProtocolBreakdown />
      <PredictionsPanel />
    </div>
  )
}
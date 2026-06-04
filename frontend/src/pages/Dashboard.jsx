import MetricsPanel from '../components/MetricsPanel'
import ProtocolBreakdown from '../components/ProtocolBreakdown'

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <MetricsPanel />
      <ProtocolBreakdown />
    </div>
  )
}
import { useState, useEffect, useRef } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'
import { useWebSocket } from '../hooks/useWebSocket';
import { WS_BASE_URL } from '../services/config';

const WS_URL = `${WS_BASE_URL}/ws/metrics`
const WINDOW_SECONDS = 60

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

export default function MetricsPanel() {
  const [dataPoints, setDataPoints] = useState([])

  const {
    lastMessage,
    connected,
  } = useWebSocket(WS_URL)

  const counterRef = useRef(0)

  useEffect(() => {
    if (!lastMessage) return

    const parsed = lastMessage
    counterRef.current += 1

    const now = Date.now()

    const newPoint = {
      ts: now,
      time: formatTime(now),
      pps: parsed.packets_per_sec ?? parsed.pps ?? counterRef.current,
      bytes: parsed.bytes_per_sec ?? parsed.bytes ?? 0,
    }

    setDataPoints(prev => {
      const cutoff = now - WINDOW_SECONDS * 1000
      return [...prev.filter(p => p.ts > cutoff), newPoint]
    })
  }, [lastMessage])

  return (
    <div
      data-testid="metrics-panel"
      className="bg-gray-800 rounded-xl p-5"
    >
      {!connected && (
        <span>Disconnected</span>
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-medium text-sm">
          Packets / second
        </h2>

        <span className="text-gray-400 text-xs">
          Rolling 60 s
        </span>
      </div>

      <div data-testid="metrics-chart">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart
            data={dataPoints}
            margin={{ top: 4, right: 12, bottom: 0, left: -8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#374151"
            />

            <XAxis
              dataKey="time"
              tick={{ fill: '#9CA3AF', fontSize: 10 }}
              tickLine={false}
              interval="preserveStartEnd"
            />

            <YAxis
              tick={{ fill: '#9CA3AF', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />

            <Tooltip
              contentStyle={{
                background: '#1F2937',
                border: 'none',
                borderRadius: 6
              }}
              labelStyle={{
                color: '#9CA3AF',
                fontSize: 11
              }}
              itemStyle={{
                color: '#60A5FA',
                fontSize: 11
              }}
            />

            <Line
              type="monotone"
              dataKey="pps"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
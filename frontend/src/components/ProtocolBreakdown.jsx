import { useState, useEffect } from 'react'
import {
    PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { useWebSocket } from '../hooks/useWebSocket'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/metrics'

const COLORS = {
    TCP: '#3B82F6',
    UDP: '#10B981',
    ICMP: '#F59E0B',
    OTHER: '#6B7280',
}

const RADIAN = Math.PI / 180
function CustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
    if (percent < 0.05) return null
    const r = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + r * Math.cos(-midAngle * RADIAN)
    const y = cy + r * Math.sin(-midAngle * RADIAN)
    return (
        <text x={x} y={y} fill="#fff" textAnchor="middle"
            dominantBaseline="central" fontSize={11} fontWeight={500}>
            {`${(percent * 100).toFixed(0)}%`}
        </text>
    )
}

export default function ProtocolBreakdown() {
    const [counts, setCounts] = useState({ TCP: 0, UDP: 0, ICMP: 0, OTHER: 0 })
    const { lastMessage } = useWebSocket(WS_URL)

    useEffect(() => {
        if (!lastMessage) return
       const parsed = lastMessage
if (!parsed) return

const proto = (parsed.protocol ?? 'OTHER').toUpperCase()
        const key = counts.hasOwnProperty(proto) ? proto : 'OTHER'
        setCounts(prev => ({ ...prev, [key]: prev[key] + 1 }))
    }, [lastMessage])

    const total = Object.values(counts).reduce((a, b) => a + b, 0)
    const data = Object.entries(counts)
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value }))

    return (
        <div className="bg-gray-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-medium text-sm">Protocol breakdown</h2>
                <span className="text-gray-400 text-xs">{total} packets total</span>
            </div>
            {data.length === 0 ? (
                <div className="h-[220px] flex items-center justify-center text-gray-500 text-sm">
                    Waiting for traffic…
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            outerRadius={80}
                            dataKey="value"
                            labelLine={false}
                            label={CustomLabel}
                        >
                            {data.map(entry => (
                                <Cell key={entry.name} fill={COLORS[entry.name] ?? COLORS.OTHER} />
                            ))}
                        </Pie>
                        <Tooltip
                            contentStyle={{ background: '#1F2937', border: 'none', borderRadius: 6 }}
                            labelStyle={{ color: '#9CA3AF', fontSize: 11 }}
                            itemStyle={{ color: '#E5E7EB', fontSize: 11 }}
                        />
                        <Legend
                            iconType="circle"
                            iconSize={8}
                            formatter={(value) => (
                                <span style={{ color: '#9CA3AF', fontSize: 11 }}>{value}</span>
                            )}
                        />
                    </PieChart>
                </ResponsiveContainer>
            )}
        </div>
    )
}
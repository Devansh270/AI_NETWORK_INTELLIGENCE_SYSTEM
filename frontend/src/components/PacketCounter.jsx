import { useState, useEffect } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { WS_BASE_URL } from '../services/config'

const WS_URL = `${WS_BASE_URL}/ws/metrics`;

function PacketCounter() {

const { lastMessage, connectionStatus, messageHistory } =
    useWebSocket(WS_URL);

    const [packetCount, setPacketCount] = useState(0)

    useEffect(() => {
        if (lastMessage !== null) {
            setPacketCount((prev) => prev + 1)
        }
    }, [lastMessage])

    // Pick the color of the status dot based on connection state
    const dotColor =
        connectionStatus === 'connected'
            ? 'bg-green-500'
            : connectionStatus === 'connecting'
                ? 'bg-yellow-500'
                : 'bg-red-500'

    return (
        <div className="p-6 max-w-md bg-white rounded-lg shadow-md border border-gray-200">
            {/* Header with status dot */}
            <div className="flex items-center gap-2 mb-4">
                <div className={`w-3 h-3 rounded-full ${dotColor}`}></div>
                <h2 className="text-lg font-semibold text-gray-800">
                    Live Packet Counter
                </h2>
                <span className="text-sm text-gray-500 ml-auto">
                    {connectionStatus}
                </span>
            </div>

            {/* Big counter number */}
            <div className="text-center my-6">
                <div className="text-6xl font-bold text-blue-600">{packetCount}</div>
                <p className="text-sm text-gray-500 mt-2">
                    packets captured since connection opened
                </p>
            </div>

            {/* Mini log of last 5 packets */}
            <div className="border-t pt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                    Recent packets
                </h3>
                {messageHistory.length === 0 ? (
                    <p className="text-xs text-gray-400">No packets yet…</p>
                ) : (
                    <ul className="text-xs text-gray-600 space-y-1 font-mono">
                        {messageHistory.slice(-5).map((msg, i) => (
                            <li key={i}>
                                {msg.src || '?'} → {msg.dst || '?'} | {msg.proto || msg.protocol || '?'} | {msg.length || msg.packet_length || '?'} bytes
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    )
}

export default PacketCounter
// frontend/src/hooks/__tests__/useWebSocket.test.ts

import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Must mock WebSocket BEFORE importing the hook
class MockWebSocket {
  url: string
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((event: unknown) => void) | null = null
  readyState = 0 // CONNECTING — use number directly, not WebSocket.CONNECTING

  constructor(url: string) {
    this.url = url
    setTimeout(() => {
      this.readyState = 1 // OPEN
      this.onopen?.()
    }, 0)
  }

  close() {
    this.readyState = 3 // CLOSED
    this.onclose?.()
  }

  simulateMessage(data: string) {
    this.onmessage?.({ data })
  }
}

vi.stubGlobal('WebSocket', MockWebSocket)

import { useWebSocket } from '../useWebSocket'

describe('useWebSocket', () => {

  it('starts with connecting status', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))
    // before the setTimeout fires, status is still 'connecting'
    expect(result.current.connectionStatus).toBe('connecting')
  })

  it('returns connected status after connection opens', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))
    await act(async () => {
      await new Promise(r => setTimeout(r, 10)) // let the setTimeout in MockWebSocket fire
    })
    expect(result.current.connectionStatus).toBe('connected')
  })

  it('starts with null lastMessage', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))
    expect(result.current.lastMessage).toBeNull()
  })

  it('starts with empty messageHistory', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))
    expect(result.current.messageHistory).toEqual([])
  })

  it('updates lastMessage when a valid JSON message arrives', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 10)) // wait for onopen
      const ws = (globalThis.WebSocket as unknown as { lastInstance: MockWebSocket }).lastInstance
      ws?.simulateMessage(JSON.stringify({ packets: 42, protocol: 'TCP' }))
    })

    expect(result.current.lastMessage).toEqual({ packets: 42, protocol: 'TCP' })
  })

  it('appends to messageHistory on each message', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 10))
      const ws = (globalThis.WebSocket as unknown as { lastInstance: MockWebSocket }).lastInstance
      ws?.simulateMessage(JSON.stringify({ id: 1 }))
      ws?.simulateMessage(JSON.stringify({ id: 2 }))
    })

    expect(result.current.messageHistory).toHaveLength(2)
  })

  it('does not crash on malformed JSON message', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 10))
      const ws = (globalThis.WebSocket as unknown as { lastInstance: MockWebSocket }).lastInstance
      ws?.simulateMessage('NOT_VALID_JSON')
    })

    // lastMessage stays null, no crash
    expect(result.current.lastMessage).toBeNull()
  })

  it('closes WebSocket on unmount without crashing', async () => {
    const { unmount } = renderHook(() => useWebSocket('ws://localhost:8000/ws/metrics'))
    await act(async () => {
      await new Promise(r => setTimeout(r, 10))
    })
    expect(() => unmount()).not.toThrow()
  })

})
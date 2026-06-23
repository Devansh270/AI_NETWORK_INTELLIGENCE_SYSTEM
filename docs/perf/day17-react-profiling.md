# Day 17 – React Rendering Profiling

## Goal

Identify unnecessary React re-renders caused by live WebSocket updates and optimize rendering performance.

## Profiling Setup

* Used React DevTools Profiler.
* Recorded dashboard activity for approximately 30 seconds with active WebSocket traffic.
* Examined Flame Graph and Ranked views.

## Findings

* No significant re-render cascades detected.
* Sidebar, Layout, BrowserRouter, and DashboardPage were not major contributors to render cost.
* Most render activity originated from chart-related components:

  * MetricsPanel
  * ProtocolBreakdown
  * Recharts internals (CartesianGrid, PieSectors, Tooltip, Legend, PolarChart)

## Optimization Applied

### ProtocolBreakdown

Memoized derived chart calculations:

```js
const total = useMemo(..., [counts]);
const data = useMemo(..., [counts]);
```

Reason:

* Prevent repeated recreation of chart datasets when unrelated values remain unchanged.
* Reduce unnecessary recalculation before passing data into Recharts components.

## useWebSocket Review

Investigated the custom hook.
The hook returns a new object on each render, but profiling did not reveal major re-render cascades attributable to object identity changes.

## Result

* Commit durations generally remained below 10ms.
* Dashboard remained responsive under continuous WebSocket updates.
* No critical rendering bottlenecks were identified.

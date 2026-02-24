"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { PipelineEventMessage } from "@/lib/types";

export function usePipelineWebSocket(jobId: string | null) {
  const [events, setEvents] = useState<PipelineEventMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!jobId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Connect to FastAPI directly on port 8000 for WebSocket
    const ws = new WebSocket(`${protocol}//localhost:8000/ws/pipeline/${jobId}`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      const msg: PipelineEventMessage = JSON.parse(event.data);
      if (msg.type !== "heartbeat") {
        setEvents((prev) => [...prev.slice(-200), msg]); // Keep last 200
      }
    };

    wsRef.current = ws;
    return () => ws.close();
  }, [jobId]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  const latestProgress = events
    .filter((e) => e.type === "progress")
    .at(-1)?.data;

  return { events, connected, latestProgress };
}

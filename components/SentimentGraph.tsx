"use client";
import React, { useEffect, useRef, useState } from "react";
import { debounce } from "lodash";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

type SentimentData = {
  timestamp: string;
  positive: number;
  negative: number;
  threat: number;
};

export const SentimentGraph: React.FC = () => {
  const [data, setData] = useState<SentimentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);

  const updateDataRef = useRef(
    debounce((newData: SentimentData) => {
      setData((prev) => [...prev.slice(-19), newData]);
    }, 500),
  );

  useEffect(() => {
    setStreaming(true);
    setLoading(true);

  const apiUrl = (globalThis as any).process?.env?.NEXT_PUBLIC_API_URL || "";
    const url = apiUrl ? `${apiUrl}/api/logs` : "/api/logs";

    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setStreaming(false);
      setLoading(false);
    };

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data || "{}");
        const newPoint: SentimentData = {
          timestamp: new Date().toLocaleTimeString(),
          positive: Number(parsed.sentiment_positive) || 0,
          negative: Number(parsed.sentiment_negative) || 0,
          threat: Number(parsed.threat_level) || 0,
        };

        updateDataRef.current(newPoint);
      } catch (err) {
        // ignore malformed events
        // but log for debugging
        // eslint-disable-next-line no-console
        console.error("Error parsing event data:", err);
      }
    };

    eventSource.onerror = (err) => {
      // eslint-disable-next-line no-console
      console.error("EventSource connection error. Retrying...", err);
      setStreaming(true);
      // let browser handle reconnects; no manual retry here
    };

    return () => {
      eventSource.close();
      // cancel any pending debounced updates
      updateDataRef.current.cancel && updateDataRef.current.cancel();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mt-6 w-full h-64">
      {loading && <div className="text-blue-500">Loading logs...</div>}
      {streaming && <div className="text-orange-500">Streaming logs...</div>}

      <h2 className="text-lg font-semibold mb-2">Sentiment & Threat Trends</h2>

      <div className="w-full h-52">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis domain={[0, 1]} />
            <Tooltip />
            <Legend />

            <Line
              type="monotone"
              dataKey="positive"
              name="Positive"
              stroke={data.some((d) => d.positive > 0.8) ? "#22c55e" : "#4ade80"}
            />

            <Line
              type="monotone"
              dataKey="negative"
              name="Negative"
              stroke={data.some((d) => d.negative > 0.8) ? "#dc2626" : "#f87171"}
            />

            <Line
              type="monotone"
              dataKey="threat"
              name="Threat"
              stroke={data.some((d) => d.threat > 0.5) ? "#eab308" : "#facc15"}
              strokeDasharray="5 5"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SentimentGraph;

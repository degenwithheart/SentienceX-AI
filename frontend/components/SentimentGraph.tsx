'use client';
import React, { useEffect, useState } from 'react';
import { debounce } from 'lodash';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

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

  const updateData = debounce((newData) => {
    setData(prev => [
      ...prev.slice(-19),
      newData
    ]);
  }, 1000); // Throttle updates to once per second

  useEffect(() => {
    setStreaming(true);
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/logs`);
    setLoading(true); = new EventSource(`${apiUrl}/api/logs`); = new EventSource(`${apiUrl}/api/logs`);
    setLoading(true);    setLoading(true);
    eventSource.onopen = () => {
      setStreaming(false);) => {) => {
      setLoading(false);););
    };setLoading(false);setLoading(false);
    };    };

    eventSource.onmessage = (event) => {urce.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data); = JSON.parse(event.data);
        updateData({
          timestamp: new Date().toLocaleTimeString(),),
          positive: parsed.sentiment_positive || 0,
          negative: parsed.sentiment_negative || 0,ve || 0,
          threat: parsed.threat_level || 0,hreat: parsed.threat_level || 0,
        });
      } catch (error) {
        console.error("Error parsing event data:", error); console.error("Error parsing event data:", error);
      }}
    };    };

    eventSource.onerror = () => {
      console.error("EventSource connection error. Retrying...");Source connection error.");
      setTimeout(() => {
        const newEventSource = new EventSource(`${apiUrl}/api/logs`);eventSource.close();
        setStreaming(true);    };
      }, 5000);
    };n () => eventSource.close();
  }, []);
    return () => eventSource.close();
  }, []);

  return (
    <div className="mt-6 w-full h-64">
      {loading && <div className="text-blue-500">Loading logs...</div>}ment & Threat Trends</h2>
      {streaming && <div className="text-orange-500">Streaming logs...</div>}h="100%" height="100%">
      <h2 className="text-lg font-semibold mb-2">Sentiment & Threat Trends</h2>
      <ResponsiveContainer width="100%" height="100%">y="3 3" />
        <LineChart data={data}>" />
          <CartesianGrid strokeDasharray="3 3" />in={[0, 1]} />
          <XAxis dataKey="timestamp" />>
          <YAxis domain={[0, 1]} />nd />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"me(d => d.positive > 0.8) ? "#22c55e" : "#4ade80"}
            dataKey="positive"name="Positive"
            stroke={data.some(d => d.positive > 0.8) ? "#22c55e" : "#4ade80"}
            name="Positive"
          />
          <Line
            type="monotone"me(d => d.negative > 0.8) ? "#dc2626" : "#f87171"}
            dataKey="negative"name="Negative"
            stroke={data.some(d => d.negative > 0.8) ? "#dc2626" : "#f87171"}
            name="Negative"
          />
          <Line
            type="monotone"some(d => d.threat > 0.5) ? "#eab308" : "#facc15"}
            dataKey="threat"
            stroke={data.some(d => d.threat > 0.5) ? "#eab308" : "#facc15"}strokeDasharray="5 5"
            name="Threat"
            strokeDasharray="5 5"
          />sponsiveContainer>
        </LineChart></div>
      </ResponsiveContainer>);
    </div>};



};  );
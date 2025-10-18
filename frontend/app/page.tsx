'use client';
import React, { useState, useEffect } from 'react';
import { SentimentGraph } from '../components/SentimentGraph';
import { Toaster, toast } from 'sonner';

export default function Home() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [sentiment, setSentiment] = useState(null);
  const [threat, setThreat] = useState(null);
  const [sarcasm, setSarcasm] = useState(null);
  const [audioSrc, setAudioSrc] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchWithRetry = async (url, options, retries = 3, timeout = 5000) => {
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(id);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        return await response.json();
      } catch (error) {
        if (attempt === retries - 1) throw error;
      }
    }
  };

  const clearChat = () => {
    setInput('');
    setResponse('');
    setSentiment(null);
    setThreat(null);
    setSarcasm(null);
    setAudioSrc('');
    toast('Chat cleared successfully!', { type: 'success' });
  };

  const sendMessage = async () => {
    setLoading(true);
    try {
      const data = await fetchWithRetry(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.NEXT_PUBLIC_AUTH_TOKEN}` },
        body: JSON.stringify({ text: input })
      });
      setResponse(data.response);
      setSentiment(data.sentiment);
      setThreat(data.threat);
      setSarcasm(data.sarcasm);
      setAudioSrc(`data:audio/wav;base64,${data.audio}`);
      toast('Message sent successfully!', { type: 'success' });
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("An error occurred while sending the message.");
    } finally {
      setLoading(false);
    }
  };

  const triggerRetrain = async () => {
    try {
      const data = await fetchWithRetry(`${process.env.NEXT_PUBLIC_API_URL}/api/retrain`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${process.env.NEXT_PUBLIC_AUTH_TOKEN}` }
      });
      toast(data.msg, { type: 'success' });
    } catch (error) {
      console.error("Error triggering retraining:", error);
      toast.error("An error occurred while triggering retraining.");
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/logs`, {
        headers: { Authorization: `Bearer ${process.env.NEXT_PUBLIC_AUTH_TOKEN}` }
      });
      const logs = await response.json();
      logs.forEach(log => toast(log.message));
    } catch (error) {
      console.error("Error fetching logs:", error);
      toast.error("An error occurred while fetching logs.");
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <main className="p-4">
      <Toaster position="top-right" />
      <h1 className="text-2xl font-bold">SentienceX-AI Chat</h1>
      <textarea value={input} onChange={e => setInput(e.target.value)} className="w-full border p-2 my-2" />
      <div className="flex gap-2">
        <button onClick={sendMessage} className="bg-blue-500 text-white px-4 py-2">Send</button>
        <button onClick={triggerRetrain} className="bg-orange-500 text-white px-4 py-2">Retrain</button>
        <button onClick={clearChat} className="bg-gray-500 text-white px-4 py-2">Clear</button>
      </div>
      {loading && <div className="spinner">Loading...</div>}
      {response && <div className="mt-4"><b>Response:</b> {response}</div>}
      {sentiment && <div><b>Sentiment:</b> {JSON.stringify(sentiment)}</div>}
      {threat && <div><b>Threat:</b> {JSON.stringify(threat)}</div>}
      {sarcasm && <div><b>Sarcasm:</b> {JSON.stringify(sarcasm)}</div>}
      {audioSrc && <audio controls src={audioSrc} className="mt-2" />}
      <SentimentGraph />
    </main>
  );
}
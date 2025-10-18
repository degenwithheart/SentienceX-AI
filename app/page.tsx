'use client';
import React, { useState, useEffect, useRef } from 'react';
import { SentimentGraph } from '../components/SentimentGraph';
import ThreatPanel from '../components/ThreatPanel';
import { Toaster, toast } from 'sonner';

export default function Home() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [sentiment, setSentiment] = useState(null);
  const [threat, setThreat] = useState(null);
  const [sarcasm, setSarcasm] = useState(null);
  const [audioSrc, setAudioSrc] = useState('');
  const [loading, setLoading] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showThreat, setShowThreat] = useState(false);

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
    toast.success('Chat cleared successfully!');
  };

  const sendMessage = async () => {
    setLoading(true);
    try {
  const apiUrl = (globalThis as any).process?.env?.NEXT_PUBLIC_API_URL || '';
  const data = await fetchWithRetry(`${apiUrl}/api/chat`, {
        method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${(globalThis as any).process?.env?.NEXT_PUBLIC_AUTH_TOKEN}` },
        body: JSON.stringify({ text: input })
      });
      setResponse(data.response);
      setSentiment(data.sentiment);
      setThreat(data.threat);
      setSarcasm(data.sarcasm);
      setAudioSrc(`data:audio/wav;base64,${data.audio}`);
      toast.success('Message sent successfully!');
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("An error occurred while sending the message.");
    } finally {
      setLoading(false);
    }
  };

  const triggerRetrain = async () => {
    try {
    const apiUrl = (globalThis as any).process?.env?.NEXT_PUBLIC_API_URL || '';
    const data = await fetchWithRetry(`${apiUrl}/api/retrain`, {
        method: 'POST',
  headers: { Authorization: `Bearer ${(globalThis as any).process?.env?.NEXT_PUBLIC_AUTH_TOKEN}` }
      });
      toast.success(data.msg);
    } catch (error) {
      console.error("Error triggering retraining:", error);
      toast.error("An error occurred while triggering retraining.");
    }
  };

  const fetchLogs = async () => {
    try {
      const apiUrl3 = (globalThis as any).process?.env?.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${apiUrl3}/api/logs`, {
        headers: { Authorization: `Bearer ${(globalThis as any).process?.env?.NEXT_PUBLIC_AUTH_TOKEN}` }
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

  // Touch / swipe handling: horizontal swipes on main chat open side panels;
  // vertical swipe-down on slide panels closes them.
  const touchStartX = useRef(null);
  const touchStartY = useRef(null);
  const touchDeltaX = useRef(0);
  const touchDeltaY = useRef(0);

  const handleMainTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    touchStartX.current = t.clientX;
    touchStartY.current = t.clientY;
    touchDeltaX.current = 0;
    touchDeltaY.current = 0;
  };

  const handleMainTouchMove = (e: React.TouchEvent) => {
    if (!touchStartX.current) return;
    const t = e.touches[0];
    touchDeltaX.current = t.clientX - touchStartX.current;
    touchDeltaY.current = t.clientY - (touchStartY.current ?? 0);
  };

  const handleMainTouchEnd = () => {
    const threshold = 60; // px
    if (Math.abs(touchDeltaX.current) > Math.abs(touchDeltaY.current)) {
      if (touchDeltaX.current > threshold) {
        // swipe right -> open analytics
        setShowAnalytics(true);
        if (navigator?.vibrate) navigator.vibrate(8);
      } else if (touchDeltaX.current < -threshold) {
        // swipe left -> open threat
        setShowThreat(true);
        if (navigator?.vibrate) navigator.vibrate(8);
      }
    }
    touchStartX.current = null;
    touchStartY.current = null;
    touchDeltaX.current = 0;
    touchDeltaY.current = 0;
  };

  // Slide panel swipe-down to close
  const panelTouchStartY = useRef(null);
  const panelDeltaY = useRef(0);

  const handlePanelTouchStart = (e: React.TouchEvent) => {
    panelTouchStartY.current = e.touches[0].clientY;
    panelDeltaY.current = 0;
  };

  const handlePanelTouchMove = (e: React.TouchEvent) => {
    if (!panelTouchStartY.current) return;
    panelDeltaY.current = e.touches[0].clientY - panelTouchStartY.current;
  };

  const handlePanelTouchEnd = (closeFn: () => void) => {
    const threshold = 60; // px vertical to close
    if (panelDeltaY.current > threshold) {
      closeFn();
      if (navigator?.vibrate) navigator.vibrate(6);
    }
    panelTouchStartY.current = null;
    panelDeltaY.current = 0;
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#071124_0%,#0d1220_100%)]">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(8,10,18,0.9)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255,255,255,0.04)',
            color: '#e6eef8',
            borderRadius: '10px',
          },
        }}
      />

      {/* Compact Hero */}
      <header className="py-12">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h1 className="text-4xl md:text-5xl font-bold gradient-text">SentienceX AI</h1>
          <p className="mt-3 text-base md:text-lg text-gray-300 max-w-2xl mx-auto">Real-time sentiment analysis, threat detection, and conversational AI — designed for clarity and focus.</p>
        </div>
      </header>

      {/* Main Content - three column on desktop, single on mobile */}
      <main className="max-w-6xl mx-auto px-4 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8" onTouchStart={handleMainTouchStart} onTouchMove={handleMainTouchMove} onTouchEnd={handleMainTouchEnd}>
          {/* Left analytics column - always visible on desktop */}
          <div className="md:col-span-3">
            <div className="glass-card h-full">
              <h4 className="text-lg font-semibold mb-3">Analytics</h4>

              <div className="flex flex-col gap-3 mb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="metric-badge bg-green-600/30">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-4 h-4 text-green-300" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                    <div>
                      <div className="text-sm text-gray-200">Positive</div>
                      <div className="metric-value text-lg font-semibold">{sentiment?.positive ?? '--'}</div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="metric-badge bg-red-600/30">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-4 h-4 text-red-300" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 6L6 18M6 6l12 12" />
                      </svg>
                    </span>
                    <div>
                      <div className="text-sm text-gray-200">Negative</div>
                      <div className="metric-value text-lg font-semibold">{sentiment?.negative ?? '--'}</div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="metric-badge bg-yellow-600/30">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-4 h-4 text-yellow-300" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 2a10 10 0 100 20 10 10 0 000-20z" />
                      </svg>
                    </span>
                    <div>
                      <div className="text-sm text-gray-200">Threat</div>
                      <div className="metric-value text-lg font-semibold">{threat?.level ?? '--'}</div>
                    </div>
                  </div>
                </div>
              </div>

              <SentimentGraph />
            </div>
          </div>

          {/* Center chat column */}
          <section className="md:col-span-6">
            <div className="glass-card">
              <div className="mb-6">
                <h2 className="text-2xl font-semibold">Start a Conversation</h2>
                <p className="text-sm text-gray-400">Type below to chat with SentienceX AI.</p>
              </div>

              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                className="w-full glass-input mb-6 resize-none h-40"
                placeholder="What would you like to discuss with SentienceX AI?"
              />

              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1 flex gap-3">
                  <button onClick={sendMessage} disabled={loading} className="glass-button primary-button flex-1">
                    {loading ? 'Sending...' : 'Send Message'}
                  </button>
                  <button onClick={clearChat} className="glass-button">Clear</button>
                </div>
                <div className="flex items-center gap-2 md:hidden">
                  <button onClick={() => setShowAnalytics(true)} className="glass-button">Analytics</button>
                  <button onClick={triggerRetrain} className="glass-button">Retrain</button>
                  <button onClick={() => setShowThreat(true)} className="glass-button">Threat</button>
                </div>
              </div>
            </div>

            <div className="mt-6">
              {response && (
                <div className="response-card">
                  <h3 className="text-lg font-semibold text-blue-200 mb-2">AI Response</h3>
                  <p className="text-gray-200 leading-relaxed">{response}</p>
                </div>
              )}

              {sentiment && (
                <div className="response-card">
                  <h3 className="text-lg font-semibold text-green-200 mb-2">Sentiment Analysis</h3>
                  <pre className="text-gray-200 text-sm bg-black/20 p-4 rounded-md overflow-x-auto">{JSON.stringify(sentiment, null, 2)}</pre>
                </div>
              )}

              {threat && (
                <div className="response-card">
                  <h3 className="text-lg font-semibold text-red-200 mb-2">Threat Detection</h3>
                  <pre className="text-gray-200 text-sm bg-black/20 p-4 rounded-md overflow-x-auto">{JSON.stringify(threat, null, 2)}</pre>
                </div>
              )}

              {sarcasm && (
                <div className="response-card">
                  <h3 className="text-lg font-semibold text-yellow-200 mb-2">Sarcasm Detection</h3>
                  <pre className="text-gray-200 text-sm bg-black/20 p-4 rounded-md overflow-x-auto">{JSON.stringify(sarcasm, null, 2)}</pre>
                </div>
              )}

              {audioSrc && (
                <div className="response-card">
                  <h3 className="text-lg font-semibold text-purple-200 mb-2">Audio Response</h3>
                  <audio controls src={audioSrc} className="w-full" />
                </div>
              )}
            </div>
          </section>

          {/* Right threat column - always visible on desktop */}
          <div className="md:col-span-3">
            <div className="glass-card h-full">
              <h4 className="text-lg font-semibold mb-3">Threat</h4>
              <ThreatPanel threat={threat} />
            </div>
          </div>
        </div>
      </main>

      {/* Mobile overlays */}
      {showAnalytics && (
        <div className="overlay-backdrop" onClick={() => setShowAnalytics(false)}>
          <div className="slide-panel-left" onClick={e => e.stopPropagation()} onTouchStart={handlePanelTouchStart} onTouchMove={handlePanelTouchMove} onTouchEnd={() => handlePanelTouchEnd(() => setShowAnalytics(false))}>
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2">Analytics</h3>
              <SentimentGraph />
            </div>
          </div>
        </div>
      )}

      {showThreat && (
        <div className="overlay-backdrop" onClick={() => setShowThreat(false)}>
          <div className="slide-panel-right" onClick={e => e.stopPropagation()} onTouchStart={handlePanelTouchStart} onTouchMove={handlePanelTouchMove} onTouchEnd={() => handlePanelTouchEnd(() => setShowThreat(false))}>
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2">Threat</h3>
              <ThreatPanel threat={threat} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
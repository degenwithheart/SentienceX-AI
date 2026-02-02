import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import { TopNav } from "../lib/layout";
import { notifyError, notifyInfo } from "../lib/notify";
import { useRouter } from "next/router";
import { hasProfile } from "../lib/profile";

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState(null);

  async function refresh() {
    try {
      const h = await apiGet("/health");
      setData(h);
      notifyInfo("Health refreshed");
    } catch (e) {
      notifyError(e, "Health request failed");
    }
  }

  useEffect(() => {
    (async () => {
      const ok = await hasProfile();
      if (!ok) router.replace("/setup");
    })();
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [router]);

  return (
    <main className="container">
      <TopNav />
      <header className="header">
        <div>
          <h1>Dashboard</h1>
          <div className="muted">Health, memory, resources</div>
        </div>
        <button className="btn" onClick={refresh}>Refresh</button>
      </header>

      {!data ? (
        <div className="muted">Loading…</div>
      ) : (
        <div className="grid">
          <div className="card">
            <div className="label">Uptime</div>
            <div className="value">{Math.round(data.uptime_sec)}s</div>
            <div className="muted small">locale: {data.locale}</div>
          </div>
          <div className="card">
            <div className="label">CPU</div>
            <div className="value">{data.resources.cpu_percent.toFixed(1)}%</div>
            <div className="muted small">RSS: {data.resources.rss_mb.toFixed(1)} MB</div>
          </div>
          <div className="card">
            <div className="label">Memory</div>
            <div className="muted small">
              stm turns: {data.memory.stm_turns}
              <br />
              facts: {data.memory.facts}
              <br />
              topics: {data.memory.topics}
              <br />
              episodes: {data.memory.episodes}
              <br />
              index docs: {data.memory.index_docs}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/router";
import { TopNav } from "../lib/layout";
import { hasProfile } from "../lib/profile";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    (async () => {
      const ok = await hasProfile();
      if (!ok) router.replace("/setup");
    })();
  }, [router]);
  return (
    <main className="container">
      <TopNav />
      <header className="header">
        <div>
          <h1>Neutral companion UI</h1>
          <div className="muted">
            Glassmorphism theme with Light/Dark mode. Mobile-first layout.
          </div>
        </div>
      </header>

      <section className="grid">
        <div className="card">
          <div className="label">Chat</div>
          <div className="muted small">Short, thoughtful replies and feedback signals.</div>
          <div className="row" style={{ marginTop: 10 }}>
            <Link className="btn primary" href="/chat">Open chat</Link>
          </div>
        </div>
        <div className="card">
          <div className="label">Dashboard</div>
          <div className="muted small">CPU/RAM, memory sizes, health signals.</div>
          <div className="row" style={{ marginTop: 10 }}>
            <Link className="btn primary" href="/dashboard">Open dashboard</Link>
          </div>
        </div>
        <div className="card">
          <div className="label">Training</div>
          <div className="muted small">Run training modules and view status; alerts use Sonner toasts.</div>
          <div className="row" style={{ marginTop: 10 }}>
            <Link className="btn primary" href="/training">Open training</Link>
          </div>
        </div>
      </section>
    </main>
  );
}

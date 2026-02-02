import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { TopNav } from "../lib/layout";
import { notifyError, notifyInfo, notifyOk } from "../lib/notify";
import { useRouter } from "next/router";
import { hasProfile } from "../lib/profile";

const DEFAULT_MODULES = [
  "weak_labels",
  "supervised",
  "stories",
  "topics",
  "skills",
  "conversations",
  "style_bootstrap"
];

export default function TrainingPage() {
  const router = useRouter();
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [forceFull, setForceFull] = useState(false);
  const [modules, setModules] = useState(DEFAULT_MODULES);
  const modulesStr = useMemo(() => modules.join(", "), [modules]);

  async function refresh() {
    try {
      const s = await apiGet("/training/status");
      setStatus(s);
    } catch (e) {
      if ((e.message || "").includes("401")) {
        notifyError(e, "Admin mode required. In chat, send: admin:<your_token>");
      } else {
        notifyError(e, "Training status unavailable (is training enabled on the API?)");
      }
    }
  }

  async function run() {
    if (busy) return;
    setBusy(true);
    notifyInfo("Training started");
    try {
      const res = await apiPost("/training/run", {
        modules,
        force_full: forceFull
      });
      notifyOk("Training finished");
      await refresh();
      return res;
    } catch (e) {
      if ((e.message || "").includes("401")) {
        notifyError(e, "Admin mode required. In chat, send: admin:<your_token>");
      } else {
        notifyError(e, "Training run failed");
      }
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    (async () => {
      const ok = await hasProfile();
      if (!ok) router.replace("/setup");
    })();
    refresh();
  }, [router]);

  return (
    <main className="container">
      <TopNav />
      <header className="header">
        <div>
          <h1>Training</h1>
          <div className="muted">
            Runs learning pipelines on the API and writes only small artifacts to{" "}
            <code>models/</code>, <code>cognition/</code>, <code>knowledge/</code>.
          </div>
        </div>
        <div className="row">
          <button className="btn" onClick={refresh} disabled={busy}>
            Refresh
          </button>
          <button className="btn primary" onClick={run} disabled={busy}>
            {busy ? "Running…" : "Run"}
          </button>
        </div>
      </header>

      <section className="card">
        <div className="label">Modules</div>
        <div className="muted small" style={{ marginTop: 8 }}>
          {modulesStr}
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <button
            className="btn"
            onClick={() => setModules(DEFAULT_MODULES)}
            disabled={busy}
          >
            Reset defaults
          </button>
          <label className="pill" style={{ cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={forceFull}
              onChange={(e) => setForceFull(e.target.checked)}
              disabled={busy}
              style={{ marginRight: 8 }}
            />
            Force full reprocess
          </label>
        </div>
      </section>

      <section className="grid" style={{ marginTop: 12 }}>
        <div className="card">
          <div className="label">Status</div>
          {!status ? (
            <div className="muted" style={{ marginTop: 8 }}>
              Loading…
            </div>
          ) : (
            <div className="muted small" style={{ marginTop: 8 }}>
              train_dir: {status.train_dir}
              <br />
              data_dir: {status.data_dir}
              <br />
              tracked_files: {status.tracked_files}
            </div>
          )}
        </div>
        <div className="card">
          <div className="label">Last Runs</div>
          {!status ? (
            <div className="muted" style={{ marginTop: 8 }}>
              —
            </div>
          ) : (
            <div className="muted small" style={{ marginTop: 8 }}>
              {Object.keys(status.last_runs || {}).length === 0
                ? "—"
                : Object.entries(status.last_runs).map(([k, v]) => (
                    <div key={k}>
                      {k}: {new Date(v * 1000).toLocaleString()}
                    </div>
                  ))}
            </div>
          )}
        </div>
        <div className="card">
          <div className="label">Notes</div>
          <div className="muted small" style={{ marginTop: 8 }}>
            Use <code>TRAIN/</code> inputs (generated or your own). Alerts and errors
            surface as Sonner toasts.
          </div>
        </div>
      </section>
    </main>
  );
}

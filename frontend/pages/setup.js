import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { apiGet, apiPost } from "../lib/api";
import { TopNav } from "../lib/layout";
import { notifyError, notifyOk } from "../lib/notify";

export default function SetupPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [location, setLocation] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await apiGet("/user/profile");
        if (res && res.exists && res.profile) {
          router.replace("/chat");
        }
      } catch (e) {
        // If API is down, user can still fill; save will error with toast.
      }
    })();
  }, [router]);

  async function save() {
    if (busy) return;
    const n = name.trim();
    const d = dob.trim();
    const l = location.trim();
    if (!n || !d || !l) return;
    setBusy(true);
    try {
      await apiPost("/user/profile", { name: n, dob: d, location: l });
      notifyOk("Saved");
      router.replace("/chat");
    } catch (e) {
      notifyError(e, "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container">
      <TopNav />
      <header className="header">
        <div>
          <h1>First-time setup</h1>
          <div className="muted">
            This is stored locally on your machine so the companion can remember basics.
          </div>
        </div>
      </header>

      <section className="card">
        <div className="row" style={{ width: "100%" }}>
          <div style={{ flex: 1, minWidth: 220 }}>
            <div className="label">Name</div>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              inputMode="text"
            />
          </div>
          <div style={{ flex: 1, minWidth: 220 }}>
            <div className="label">DOB</div>
            <input
              className="input"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              placeholder="YYYY-MM-DD"
              inputMode="numeric"
            />
          </div>
        </div>

        <div style={{ marginTop: 12 }}>
          <div className="label">Location</div>
          <input
            className="input"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="City, state/country"
            inputMode="text"
          />
        </div>

        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn primary" onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </section>
    </main>
  );
}


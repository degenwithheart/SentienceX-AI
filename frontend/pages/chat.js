import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
import { TopNav } from "../lib/layout";
import { notifyError, notifyOk } from "../lib/notify";
import { clearChatState, loadChatState, saveChatState } from "../lib/state";
import { hasProfile } from "../lib/profile";
import { useRouter } from "next/router";

function nowId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function ChatPage() {
  const router = useRouter();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState([]);
  const [hydrated, setHydrated] = useState(false);
  const [adminMode, setAdminMode] = useState(false);
  const [lastActivity, setLastActivity] = useState(Date.now());

  const lastAi = useMemo(() => {
    for (let i = turns.length - 1; i >= 0; i--) {
      if (turns[i].role === "assistant") return turns[i];
    }
    return null;
  }, [turns]);

  useEffect(() => {
    (async () => {
      const ok = await hasProfile();
      if (!ok) router.replace("/setup");
    })();
  }, [router]);

  useEffect(() => {
    // Client-side resume: prefer local storage; fallback to backend resume.
    const local = loadChatState();
    if (local && Array.isArray(local.turns) && local.turns.length) {
      setTurns(local.turns);
      setHydrated(true);
      return;
    }
    (async () => {
      try {
        const res = await apiGet("/session/resume?n=40");
        if (res && Array.isArray(res.turns) && res.turns.length) {
          const mapped = res.turns.map((t) => ({
            id: `t${t.turn_id}`,
            role: t.role,
            text: t.text,
            meta: t.meta || {},
            tone: (t.meta || {}).tone,
            template_id: (t.meta || {}).template_id,
            brevity: (t.meta || {}).brevity
          }));
          setTurns(mapped);
        }
      } catch (e) {
        // Resume is a best-effort fail-safe.
      } finally {
        setHydrated(true);
      }
    })();
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    // Persist compact state for hard refresh survival (never persist admin chat).
    if (!adminMode) {
      saveChatState({
        turns: turns.slice(-80),
        updated_at: Date.now()
      });
    }
  }, [turns, hydrated]);

  useEffect(() => {
    if (!adminMode) return;
    if (busy) return;

    const now = Date.now();
    const delay = Math.max(0, 15000 - (now - lastActivity));
    const id = setTimeout(async () => {
      if (!adminMode || busy) return;
      try {
        const res = await apiPost("/chat", { message: "admin:exit", client: { ui: "nextjs" } });
        // The normal response handler expects send(); we do minimal restore here.
        setAdminMode(false);
        clearChatState();
        try {
          const resume = await apiGet("/session/resume?n=40");
          if (resume?.turns?.length) {
            const mapped = resume.turns.map((t) => ({
              id: `t${t.turn_id}`,
              role: t.role,
              text: t.text,
              meta: t.meta || {},
              tone: (t.meta || {}).tone,
              template_id: (t.meta || {}).template_id,
              brevity: (t.meta || {}).brevity
            }));
            setTurns(mapped);
          } else {
            setTurns([{ id: nowId(), role: "assistant", text: res.reply }]);
          }
        } catch {
          setTurns([{ id: nowId(), role: "assistant", text: "Admin mode exited." }]);
        }
      } catch {
        // If the API is unreachable, just drop local admin mode and restore local chat state.
        setAdminMode(false);
        const local = loadChatState();
        if (local?.turns?.length) setTurns(local.turns);
      }
    }, delay);

    return () => clearTimeout(id);
  }, [adminMode, busy, lastActivity]);

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setBusy(true);
    setLastActivity(Date.now());
    setInput("");
    const display = msg.toLowerCase().startsWith("admin:") ? "admin:[redacted]" : msg;
    const userTurn = { id: nowId(), role: "user", text: display };
    setTurns((t) => [...t, userTurn]);
    try {
      const res = await apiPost("/chat", {
        message: msg,
        client: { ui: "nextjs" }
      });
      const aiTurn = {
        id: nowId(),
        role: "assistant",
        text: res.reply,
        tone: res.tone,
        template_id: res.template_id,
        brevity: res.brevity,
        meta: res.meta
      };
      setLastActivity(Date.now());
      // Mode switching based on backend meta.
      if (res?.meta?.mode === "admin" && res?.meta?.admin?.enabled) {
        setAdminMode(true);
        setLastActivity(Date.now());
        setTurns([aiTurn]); // secure chat: start fresh
      } else if (res?.meta?.mode === "user" && res?.meta?.admin?.exited) {
        setAdminMode(false);
        clearChatState();
        try {
          const resume = await apiGet("/session/resume?n=40");
          if (resume?.turns?.length) {
            const mapped = resume.turns.map((t) => ({
              id: `t${t.turn_id}`,
              role: t.role,
              text: t.text,
              meta: t.meta || {},
              tone: (t.meta || {}).tone,
              template_id: (t.meta || {}).template_id,
              brevity: (t.meta || {}).brevity
            }));
            setTurns(mapped);
          } else {
            setTurns([aiTurn]);
          }
        } catch {
          setTurns([aiTurn]);
        }
      } else {
        setTurns((t) => [...t, aiTurn]);
      }
    } catch (e) {
      notifyError(e, "Chat request failed");
    } finally {
      setBusy(false);
    }
  }

  async function rate(rating) {
    if (!lastAi) return;
    try {
      await apiPost("/feedback", {
        rating,
        template_id: lastAi.template_id,
        tone: lastAi.tone
      });
      notifyOk(rating > 0 ? "Feedback recorded" : "Feedback recorded");
    } catch (e) {
      notifyError(e, "Feedback failed");
    }
  }

  return (
    <main className="container">
      <TopNav />
      <header className="header">
        <div>
          <h1>Chat</h1>
          <div className="muted">
            Short, thoughtful, local. No transformers.
          </div>
        </div>
        <div className="row">
          <button className="btn ghost" onClick={() => { clearChatState(); setTurns([]); }} disabled={busy}>
            Clear UI
          </button>
          {adminMode ? (
            <button className="btn" onClick={() => { setInput("admin:exit"); }} disabled={busy}>
              Exit admin
            </button>
          ) : null}
          <button className="btn" onClick={() => rate(1)} disabled={!lastAi || busy}>
            Helpful
          </button>
          <button className="btn" onClick={() => rate(-1)} disabled={!lastAi || busy}>
            Not helpful
          </button>
        </div>
      </header>

      <section className="chat glass">
        {turns.length === 0 ? (
          <div className="muted">
            Say what’s on your mind. I’ll keep it short and stay with you.
          </div>
        ) : null}
        {turns.map((t) => (
          <div key={t.id} className={`bubble ${t.role}`}>
            <div className="text">{t.text}</div>
            {t.role === "assistant" ? (
              <div className="meta">
                tone: {t.tone} · {t.brevity} · {t.template_id}
              </div>
            ) : null}
          </div>
        ))}
      </section>

      <footer className="composer">
        <textarea
          className="input"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (adminMode && !busy) setLastActivity(Date.now());
          }}
          placeholder="Type here…"
          rows={2}
          onKeyDown={(e) => {
            if (adminMode && !busy) setLastActivity(Date.now());
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") send();
          }}
        />
        <div className="row">
          <button className="btn primary" onClick={send} disabled={busy}>
            {busy ? "Thinking…" : "Send"}
          </button>
          <div className="muted small">Ctrl/⌘ + Enter</div>
        </div>
      </footer>
    </main>
  );
}

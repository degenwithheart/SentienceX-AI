import Link from "next/link";
import { useTheme } from "./theme";

export function TopNav() {
  const { theme, setTheme } = useTheme();
  return (
    <nav className="nav glass">
      <div className="navLeft">
        <Link className="brand" href="/">SentienceX</Link>
        <span className="pill">local · self-contained</span>
      </div>
      <div className="navRight">
        <div className="navLinks">
          <Link className="btn" href="/chat">Chat</Link>
          <Link className="btn" href="/dashboard">Dashboard</Link>
          <Link className="btn" href="/training">Training</Link>
        </div>
        <button
          className="btn"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? "Dark" : "Light"}
        </button>
      </div>
    </nav>
  );
}


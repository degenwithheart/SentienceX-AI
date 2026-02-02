import { createContext, useContext, useEffect, useMemo, useState } from "react";

const ThemeContext = createContext({
  theme: "dark",
  setTheme: () => {}
});

function getPreferredTheme() {
  if (typeof window === "undefined") return "dark";
  try {
    const saved = window.localStorage.getItem("sx_theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {}
  try {
    const prefersDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
  } catch {}
  return "dark";
}

function applyTheme(theme) {
  if (typeof document === "undefined") return;
  const t = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    const t = getPreferredTheme();
    setTheme(t);
    applyTheme(t);
  }, []);

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem("sx_theme", theme);
    } catch {}
  }, [theme]);

  const value = useMemo(() => ({ theme, setTheme }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}


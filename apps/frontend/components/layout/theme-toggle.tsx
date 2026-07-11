"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

const storageKey = "plos-theme";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    const isDark = stored
      ? stored === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;

    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    const frame = requestAnimationFrame(() => setDark(isDark));
    return () => cancelAnimationFrame(frame);
  }, []);

  function toggleTheme() {
    const nextDark = !dark;
    setDark(nextDark);
    document.documentElement.dataset.theme = nextDark ? "dark" : "light";
    localStorage.setItem(storageKey, nextDark ? "dark" : "light");
  }

  return (
    <button
      className="icon-button theme-toggle"
      onClick={toggleTheme}
      aria-label="Переключить тему"
      type="button"
    >
      {dark ? <Sun /> : <Moon />}
    </button>
  );
}

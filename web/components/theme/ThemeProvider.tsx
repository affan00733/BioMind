"use client";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

type ThemeChoice = "system" | "light" | "dark";

type ThemeContextValue = {
  choice: ThemeChoice;
  effective: "light" | "dark";
  setTheme: (t: ThemeChoice) => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY = "biomind-theme";

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [choice, setChoice] = useState<ThemeChoice>(() => {
    if (typeof window === "undefined") return "system";
    return (localStorage.getItem(STORAGE_KEY) as ThemeChoice) || "system";
  });

  const [system, setSystem] = useState<"light" | "dark">(getSystemTheme());

  // Listen to system changes
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setSystem(mq.matches ? "dark" : "light");
    mq.addEventListener?.("change", handler);
    return () => mq.removeEventListener?.("change", handler);
  }, []);

  const effective: "light" | "dark" = useMemo(() => (choice === "system" ? system : choice), [choice, system]);

  // Apply to <html> dataset and color-scheme
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = effective; // used by CSS variables
    // Help native UI pick correct palette for form controls
    (root.style as any).colorScheme = effective;
  }, [effective]);

  const setTheme = useCallback((t: ThemeChoice) => {
    setChoice(t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {}
  }, []);

  const value = useMemo(() => ({ choice, effective, setTheme }), [choice, effective, setTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

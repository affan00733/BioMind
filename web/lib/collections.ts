"use client";
import { useCallback, useEffect, useMemo, useState } from "react";

const COLLECTIONS_KEY = "collections";

function loadCollections(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(COLLECTIONS_KEY);
    if (!raw) return ["My Collection", "Untitled"];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : ["My Collection", "Untitled"];
  } catch {
    return ["My Collection", "Untitled"];
  }
}

function saveCollections(cols: string[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(COLLECTIONS_KEY, JSON.stringify(cols));
}

export function useCollections() {
  const [collections, setCollections] = useState<string[]>([]);

  useEffect(() => {
    setCollections(loadCollections());
  }, []);

  useEffect(() => {
    if (collections.length) saveCollections(collections);
  }, [collections]);

  const addCollection = useCallback((name?: string) => {
    const base = (name || "Untitled").trim() || "Untitled";
    // Ensure uniqueness by appending a number if needed
    const existing = new Set(collections);
    let candidate = base;
    let i = 1;
    while (existing.has(candidate)) {
      candidate = `${base} ${++i}`;
    }
    setCollections((prev) => [...prev, candidate]);
    return candidate;
  }, [collections]);

  const value = useMemo(() => ({ collections, addCollection }), [collections, addCollection]);
  return value;
}

export type CollectionsHook = ReturnType<typeof useCollections>;

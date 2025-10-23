"use client";
import React, { useMemo, useRef, useState } from "react";
import { getSourceById } from "@/lib/api";

export type Provenance = {
  sources?: Array<{
    source_id: string;
    score?: number;
    url?: string;
    metadata?: { source?: string } & Record<string, any>;
  }>;
};

function extractCitations(text: string) {
  const cites: string[] = [];
  const re = /\[Source ID:\s*([^\]]+)\]/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const inside = m[1];
    inside
      .split(/[ ,]+/)
      .map((s) => s.trim().replace(/[,.;]+$/, ""))
      .filter(Boolean)
      .forEach((id) => cites.push(id));
  }
  return Array.from(new Set(cites));
}

function stripCitations(text: string) {
  return text.replace(/\s*\[Source ID:[^\]]+\]/g, "").trim();
}

function splitIntoSentences(line: string): string[] {
  // Split by sentence end punctuation while preserving abbreviations to a basic extent
  // This is a simple heuristic and should be sufficient here
  const parts: string[] = [];
  let buf = "";
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    buf += ch;
    if (/[.!?]/.test(ch)) {
      // Lookahead for space or end
      const next = line[i + 1];
      if (!next || /\s/.test(next)) {
        parts.push(buf.trim());
        buf = "";
      }
    }
  }
  if (buf.trim()) parts.push(buf.trim());
  return parts;
}

export default function CitedText({ text, provenance }: { text: string; provenance?: Provenance }) {
  const provIndex = useMemo(() => {
    const m = new Map<string, { url?: string; src?: string; score?: number }>();
    for (const s of provenance?.sources || []) {
      m.set(String(s.source_id), { url: s.url, src: s.metadata?.source, score: s.score });
    }
    return m;
  }, [provenance?.sources]);

  const cacheRef = useRef(new Map<string, { text?: string; url?: string; src?: string }>());
  const [popover, setPopover] = useState<{
    id: string | null;
    x: number;
    y: number;
    text?: string;
    url?: string;
    src?: string;
    loading?: boolean;
    visible: boolean;
  }>({ id: null, x: 0, y: 0, visible: false });

  async function showPreview(id: string, target: HTMLElement) {
    const rect = target.getBoundingClientRect();
    const meta = cacheRef.current.get(id) || {};
    setPopover({ id, x: rect.left + window.scrollX, y: rect.bottom + window.scrollY + 6, text: meta.text, url: meta.url, src: meta.src, loading: !meta.text, visible: true });
    if (!meta.text) {
      try {
        const data = await getSourceById(id);
        const txt: string = data?.text || "";
        const src = data?.metadata?.source || provIndex.get(id)?.src || "";
        const url = data?.metadata?.url || provIndex.get(id)?.url || "";
        const snippet = txt ? (txt.length > 420 ? txt.slice(0, 420) + "…" : txt) : "No preview text available.";
        cacheRef.current.set(id, { text: snippet, url, src });
        setPopover((p) => (p.id === id ? { ...p, text: snippet, url, src, loading: false, visible: true } : p));
      } catch {
        setPopover((p) => (p.id === id ? { ...p, text: "Preview unavailable.", loading: false, visible: true } : p));
      }
    }
  }

  function hidePreview() {
    setPopover((p) => ({ ...p, visible: false }));
  }

  const lines = useMemo(() => text.split(/\r?\n/), [text]);

  return (
    <div className="text-text">
      {lines.map((line, idx) => {
        if (!line.trim()) return <div key={idx} className="h-3"/>;
        const sentences = splitIntoSentences(line);
        return (
          <p key={idx} className="mb-2">
            {sentences.map((s, i) => {
              const ids = extractCitations(s);
              const clean = stripCitations(s);
              // Confidence criterion: exactly one citation and it's known in provenance
              if (ids.length === 1 && provIndex.has(ids[0])) {
                const id = ids[0];
                const meta = provIndex.get(id);
                const dotted = "underline decoration-dotted underline-offset-2 cursor-help";
                const title = `${id}${meta?.src ? ` — ${meta.src}` : ""}${typeof meta?.score === "number" ? ` (score ${meta.score.toFixed(3)})` : ""}${meta?.url ? `\n${meta.url}` : ""}`;
                return (
                  <span
                    key={i}
                    onMouseEnter={(e) => showPreview(id, e.currentTarget as HTMLElement)}
                    onMouseLeave={hidePreview}
                    title={title}
                    className={dotted}
                  >
                    {clean}{i < sentences.length - 1 ? " " : ""}
                  </span>
                );
              }
              return <span key={i}>{clean}{i < sentences.length - 1 ? " " : ""}</span>;
            })}
          </p>
        );
      })}

      {popover.visible && (
        <div
          className="fixed z-50 max-w-[32rem] p-3 rounded-md shadow-lg border border-border bg-surface text-sm"
          style={{ left: popover.x, top: popover.y }}
          onMouseEnter={() => setPopover((p) => ({ ...p, visible: true }))}
          onMouseLeave={hidePreview}
        >
          <div className="text-xs text-muted mb-1">{popover.src ? popover.src : "source"} {popover.url && (
            <a className="text-[var(--accent)] underline ml-1" href={popover.url} target="_blank" rel="noreferrer">open</a>
          )}</div>
          <div className="whitespace-pre-wrap">{popover.loading ? "Loading preview…" : (popover.text || "Preview unavailable.")}</div>
        </div>
      )}
    </div>
  );
}

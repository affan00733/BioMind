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

function extractSection(text: string, header: string, nextHeaderStartsWith: string) {
  const idx = text.indexOf(header);
  if (idx === -1) return "";
  const rest = text.slice(idx + header.length);
  const endIdx = rest.indexOf(nextHeaderStartsWith);
  return (endIdx === -1 ? rest : rest.slice(0, endIdx)).trim();
}

function parseBullets(sectionText: string) {
  const lines = sectionText.split(/\r?\n/);
  const bullets: string[] = [];
  let cur: string[] = [];
  for (const line of lines) {
    if (/^\s*\*/.test(line)) {
      if (cur.length) bullets.push(cur.join(" ").trim());
      cur = [line.replace(/^\s*\*\s*/, "").trim()];
    } else if (line.trim()) {
      cur.push(line.trim());
    }
  }
  if (cur.length) bullets.push(cur.join(" ").trim());
  return bullets;
}

function extractCitations(text: string) {
  // Matches [Source ID: 12345] or multiple inside brackets
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

export default function Hypotheses({
  response,
  provenance,
  onCiteClick,
}: {
  response: string;
  provenance: Provenance | undefined;
  onCiteClick?: (id: string) => void;
}) {
  const section = extractSection(response, "2) Testable hypotheses", "3)");
  if (!section) return null;
  const bullets = parseBullets(section);
  const provIndex = new Map<string, { url?: string; src?: string; score?: number }>();
  for (const s of provenance?.sources || []) {
    provIndex.set(String(s.source_id), {
      url: s.url,
      src: s.metadata?.source,
      score: s.score,
    });
  }

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
        setPopover((p) => p.id === id ? { ...p, text: snippet, url, src, loading: false, visible: true } : p);
      } catch {
        setPopover((p) => p.id === id ? { ...p, text: "Preview unavailable.", loading: false, visible: true } : p);
      }
    }
  }

  function hidePreview() {
    setPopover((p) => ({ ...p, visible: false }));
  }

  return (
    <div className="card">
      <div className="font-semibold mb-2">Hypotheses (interactive)</div>
      <ul className="space-y-3">
        {bullets.map((b, i) => {
          const ids = extractCitations(b);
          const clean = stripCitations(b);
          return (
            <li key={i} className="text-sm leading-relaxed">
              <div className="mb-1">• {clean}</div>
              {ids.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {ids.map((id) => {
                    const meta = provIndex.get(id);
                    const color = meta?.src === "pubmed_articles" ? "#3b82f6" : meta?.src === "uniprot_records" ? "#10b981" : "#a855f7";
                    const title = `${id}${meta?.src ? ` — ${meta.src}` : ""}${typeof meta?.score === "number" ? ` (score ${meta.score.toFixed(3)})` : ""}${meta?.url ? `\n${meta.url}` : ""}`;
                    return (
                      <button
                        key={id}
                        onClick={() => onCiteClick?.(id)}
                        onMouseEnter={(e) => showPreview(id, e.currentTarget as HTMLElement)}
                        onMouseLeave={hidePreview}
                        title={title}
                        className="px-2 py-0.5 rounded-full text-xs text-white"
                        style={{ backgroundColor: color }}
                      >
                        [{id}] {meta?.src || "source"}
                      </button>
                    );
                  })}
                </div>
              )}
            </li>
          );
        })}
      </ul>

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

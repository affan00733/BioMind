"use client";
import AppShell from "@/components/AppShell";
import Segmented from "@/components/ui/Segmented";
import Button from "@/components/ui/Button";
import { useCallback, useMemo, useRef, useState } from "react";
import { searchRag, searchRagUpload, type ModelChoice } from "@/lib/api";
import Hypotheses from "@/components/agents/Hypotheses";
import CitedText from "@/components/agents/CitedText";

export default function SearchPage() {
  const [mode, setMode] = useState("General");
  const [model, setModel] = useState<ModelChoice>("Gemini (Balanced)");
  const [query, setQuery] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const canSubmit = useMemo(() => query.trim().length > 0 || files.length > 0, [query, files.length]);

  const onPickFiles = useCallback(() => fileInputRef.current?.click(), []);

  const onFilesSelected = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files;
    if (!list) return;
    const arr = Array.from(list);
    setFiles(prev => [...prev, ...arr].slice(0, 5)); // limit to 5
    e.target.value = ""; // reset
  }, []);

  const removeFile = useCallback((idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const doSubmit = useCallback(async () => {
    if (!canSubmit || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const opts = { mode, model } as const;
      const data = files.length > 0
        ? await searchRagUpload(query.trim(), files, opts)
        : await searchRag(query.trim(), opts);
      setResult(data);
    } catch (e: any) {
      setError(e?.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }, [canSubmit, files, loading, mode, model, query]);

  const onKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      doSubmit();
    }
  }, [doSubmit]);

  return (
    <AppShell>
      <h1 className="text-5xl font-extrabold text-center text-text">What are you searching for?</h1>
      <p className="text-center text-muted mt-2">Get accurate answers with line-by-line source citations</p>
      <div className="max-w-3xl mx-auto mt-8 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <Segmented options={["General", "Scholar"]} value={mode} onChange={setMode} />
            <div className="relative">
              <select
                className="card pr-8 pl-3 py-2 text-sm text-text bg-surface border border-border rounded-md focus:outline-none focus:ring-2 ring-offset-0 ring-[var(--focus)]"
                value={model}
                onChange={(e) => setModel(e.target.value as ModelChoice)}
              >
                <option>Gemini (Fast)</option>
                <option>Gemini (Balanced)</option>
                <option>Gemini (Advanced)</option>
              </select>
            </div>
          </div>

          <div className="relative">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              className="w-full card min-h-[140px] pr-12 text-text placeholder:text-muted"
              placeholder="Ask anything (Press Enter to send, Shift+Enter for newline)"
            />
            <button
              aria-label="Send query"
              disabled={!canSubmit || loading}
              onClick={doSubmit}
              className="absolute bottom-4 right-4 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center w-9 h-9 rounded-full bg-[var(--accent)] text-white shadow hover:opacity-90 focus:outline-none focus:ring-2 ring-offset-0 ring-white/30"
              title="Send"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <input ref={fileInputRef} type="file" multiple className="hidden" onChange={onFilesSelected} accept=".txt,.pdf,.docx" />
              <Button data-variant="subtle" onClick={onPickFiles}>Attach files</Button>
              <span className="text-sm text-muted">PDF, DOCX, or TXT (max 5 files)</span>
            </div>
            <Button data-variant="primary" disabled={!canSubmit || loading} onClick={doSubmit}>{loading ? "Searching..." : "Search"}</Button>
          </div>

          {files.length > 0 && (
            <div className="card">
              <div className="text-sm font-medium text-text mb-2">Attached files</div>
              <ul className="space-y-1">
                {files.map((f, i) => (
                  <li key={i} className="flex items-center justify-between text-sm">
                    <span className="truncate max-w-[80%]">{f.name}</span>
                    <button onClick={() => removeFile(i)} className="text-muted hover:text-text" aria-label={`Remove ${f.name}`}>Remove</button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && <div className="card text-red-500">{error}</div>}
          {result && (
            <div className="card space-y-4">
              <div className="text-sm text-muted">Model: {result?.diagnostics?.effective_model || result?.metadata?.model}</div>
              {/* Response with sentence-level hover previews */}
              <CitedText text={result.response || ""} provenance={result.provenance} />

              {/* Confidence & Diagnostics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="card">
                  <div className="font-semibold mb-2">Confidence</div>
                  <ul className="text-sm space-y-1">
                    <li>Validation passed: {String(result?.validation?.passed ?? result?.confidence_metrics?.validation_passed ?? false)}</li>
                    <li>Source coverage: {Math.round(100 * (result?.validation?.source_coverage ?? result?.confidence_metrics?.source_coverage ?? 0))}%</li>
                    <li>Avg source score: {typeof result?.confidence_metrics?.average_source_score === 'number' ? result.confidence_metrics.average_source_score.toFixed(3) : '—'}</li>
                    {result?.confidence_metrics?.detailed && (
                      <>
                        <li className="mt-2 font-medium">Detailed breakdown</li>
                        <li>Overall confidence: {typeof result.confidence_metrics.detailed.confidence_percentage === 'number' ? Math.round(result.confidence_metrics.detailed.confidence_percentage) + '%' : '—'}</li>
                        <li>Evidence score: {result.confidence_metrics.detailed.breakdown?.evidence_score?.toFixed ? (result.confidence_metrics.detailed.breakdown.evidence_score.toFixed(3)) : '—'}</li>
                        <li>Consistency score: {result.confidence_metrics.detailed.breakdown?.consistency_score?.toFixed ? (result.confidence_metrics.detailed.breakdown.consistency_score.toFixed(3)) : '—'}</li>
                        <li>Novelty score: {result.confidence_metrics.detailed.breakdown?.novelty_score?.toFixed ? (result.confidence_metrics.detailed.breakdown.novelty_score.toFixed(3)) : '—'}</li>
                      </>
                    )}
                  </ul>
                </div>
                <div className="card">
                  <div className="font-semibold mb-2">Diagnostics</div>
                  <ul className="text-sm space-y-1">
                    <li>Neighbors: {result?.diagnostics?.neighbors ?? '—'}</li>
                    <li>Mapped docs: {result?.diagnostics?.mapped_docs ?? '—'}</li>
                    <li>Hybrid: {String(result?.diagnostics?.hybrid ?? false)}</li>
                    <li>Corpus: {result?.diagnostics?.corpus_source ?? '—'}</li>
                    {result?.diagnostics?.timings_ms && (
                      <li className="mt-1 text-xs text-muted">
                        Timings (ms): embed {result.diagnostics.timings_ms.embed}, retrieve {result.diagnostics.timings_ms.retrieve}, generate {result.diagnostics.timings_ms.generate}, total {result.diagnostics.timings_ms.total}
                      </li>
                    )}
                  </ul>
                </div>
              </div>

              {/* Interactive Hypotheses */}
              <Hypotheses
                response={result.response || ""}
                provenance={result.provenance}
                onCiteClick={(id) => {
                  const el = document.getElementById(`src-${id}`);
                  if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    el.classList.add('ring-2','ring-[var(--accent)]');
                    setTimeout(() => el.classList.remove('ring-2','ring-[var(--accent)]'), 1200);
                  }
                }}
              />

              {/* Removed explicit Sources list: hover previews on sentences now show provenance */}
            </div>
          )}
      </div>
    </AppShell>
  );
}

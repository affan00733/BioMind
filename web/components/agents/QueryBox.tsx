"use client";
import { useState } from "react";
import Button from "@/components/ui/Button";
import { searchRag } from "@/lib/api";

export default function QueryBox({ placeholder, primaryCta }: { placeholder: string; primaryCta: string }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);

  async function onSubmit() {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await searchRag(text.trim());
      // Expecting { response: string, provenance?: { sources?: any[] }, diagnostics?: any }
      const msg = res?.response || JSON.stringify(res);
      setAnswer(msg);
    } catch (e: any) {
      setError(e?.message || "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <textarea
        className="w-full bg-transparent outline-none min-h-[140px]"
        placeholder={placeholder}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="mt-3 flex items-center justify-between">
        <div className="text-sm text-gray-500">
          {loading && <span>Thinking…</span>}
          {!loading && error && <span className="text-red-500">{error}</span>}
        </div>
        <Button data-variant="primary" onClick={onSubmit} disabled={loading}>
          {loading ? "Asking…" : primaryCta}
        </Button>
      </div>
      {answer && (
        <div className="mt-4 rounded-md border border-gray-200 p-3 text-sm whitespace-pre-wrap">
          {answer}
        </div>
      )}
    </div>
  );
}

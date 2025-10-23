export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type ModelChoice = "Gemini (Fast)" | "Gemini (Balanced)" | "Gemini (Advanced)";

function normalizeModelParam(model?: ModelChoice): string | undefined {
  if (!model) return undefined;
  const m = model.toLowerCase();
  if (m.includes("fast")) return "gemini-2.5-flash-lite";
  if (m.includes("balanced")) return "gemini-2.5-flash";
  if (m.includes("advanced")) return "gemini-1.5-pro";
  return undefined;
}

export async function searchRag(query: string, opts?: { mode?: string; model?: ModelChoice; k?: number; threshold?: number; temperature?: number }) {
  const res = await fetch(`${API_BASE}/api/rag/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      mode: opts?.mode || "General",
      k: opts?.k ?? 20,
      min_score_threshold: opts?.threshold ?? 0.2,
      temperature: opts?.temperature ?? 0.3,
      model: normalizeModelParam(opts?.model),
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = "";
    try {
      // Try to extract server error body for better UI messages
      detail = await res.text();
    } catch {}
    throw new Error(`Search failed: ${res.status}${detail ? ` — ${detail}` : ""}`);
  }
  return res.json();
}

export async function searchRagUpload(query: string, files: File[], opts?: { mode?: string; model?: ModelChoice; k?: number; threshold?: number; temperature?: number }) {
  const form = new FormData();
  form.append("query", query);
  form.append("mode", opts?.mode || "General");
  form.append("k", String(opts?.k ?? 20));
  form.append("min_score_threshold", String(opts?.threshold ?? 0.2));
  form.append("temperature", String(opts?.temperature ?? 0.3));
  const modelParam = normalizeModelParam(opts?.model);
  if (modelParam) form.append("model", modelParam);
  for (const f of files) {
    form.append("files", f);
  }
  const res = await fetch(`${API_BASE}/api/rag/search_upload`, {
    method: "POST",
    body: form,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = "";
    try { detail = await res.text(); } catch {}
    throw new Error(`Upload search failed: ${res.status}${detail ? ` — ${detail}` : ""}`);
  }
  return res.json();
}

export async function health() {
  const res = await fetch(`${API_BASE}/healthz`, { cache: "no-store" });
  return { ok: res.ok };
}

export async function getSourceById(id: string) {
  const res = await fetch(`${API_BASE}/api/sources/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Source ${id} not found`);
  }
  return res.json();
}

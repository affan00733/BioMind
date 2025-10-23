"use client";
import { useCallback, useRef, useState } from "react";
import { ChevronLeft, Share2, Plus, X } from "lucide-react";

export default function CollectionDetail({ name }: { name: string }) {
  const [openAdd, setOpenAdd] = useState(false);
  const [isOver, setIsOver] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsOver(false);
    const dropped = Array.from(e.dataTransfer.files || []);
    if (dropped.length) setFiles((prev) => [...prev, ...dropped]);
  }, []);

  const onBrowse = useCallback(() => inputRef.current?.click(), []);

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => (window.location.href = "/collections")} className="p-2 rounded-md hover:bg-[rgba(255,255,255,0.06)]">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <h1 className="text-2xl font-semibold">{name}</h1>
          <span className="ml-2 text-muted">⚙️</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="card flex items-center gap-2"><Share2 className="h-4 w-4" /> Share</button>
          <button className="card flex items-center gap-2" onClick={() => setOpenAdd(true)}><Plus className="h-4 w-4" /> Add source</button>
        </div>
      </div>

      {/* Sources table header */}
      <div className="mt-6 text-sm text-muted">1 source</div>
      <div className="mt-3 grid grid-cols-2 md:grid-cols-[1fr_200px_60px] text-sm text-muted px-0.5">
        <div>Name</div>
        <div className="hidden md:block">Date uploaded</div>
        <div className="hidden md:block" />
      </div>
      <div className="mt-2 border-t border-border" />
      {/* Example row (static demo) */}
      {files.length > 0 && files.map((f, i) => (
        <div key={`${f.name}-${i}`} className="grid grid-cols-2 md:grid-cols-[1fr_200px_60px] items-center py-3 border-b border-border/60">
          <div className="truncate">📄 {f.name}</div>
          <div className="hidden md:block text-sm text-muted">Just now</div>
          <div className="hidden md:block text-right">⋯</div>
        </div>
      ))}

      {/* Add sources modal */}
      {openAdd && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm grid place-items-center z-50">
          <div className="w-[90vw] max-w-2xl rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">Add sources</div>
              <button className="p-2 rounded-md hover:bg-[rgba(255,255,255,0.06)]" onClick={() => setOpenAdd(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <div
              className={`mt-4 rounded-xl border-2 border-dashed ${isOver ? "border-accent bg-[#141a14]" : "border-border"} p-8 text-center`}
              onDragOver={(e) => { e.preventDefault(); setIsOver(true); }}
              onDragLeave={() => setIsOver(false)}
              onDrop={onDrop}
            >
              <div className="text-base font-medium">Drag & drop files to upload sources</div>
              <div className="text-sm text-muted mt-1">Supported files: PDF, DOCX, TXT (up to 25MB per a file)</div>
              <div className="mt-4">
                <button className="card" onClick={onBrowse}>Choose files</button>
                <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" multiple hidden onChange={(e) => {
                  const picked = Array.from(e.target.files || []);
                  if (picked.length) setFiles((prev) => [...prev, ...picked]);
                }} />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
              <button className="card py-3">Add link</button>
              <button className="card py-3">Add text</button>
            </div>
          </div>
        </div>
      )}

      {/* Bottom query dock */}
      <div className="fixed left-[288px] right-6 bottom-4">
        <div className="rounded-xl border border-border bg-[rgba(255,255,255,0.03)] p-3">
          <div className="text-xs text-muted mb-1">Answers based on {files.length || 0} source</div>
          <div className="flex items-center gap-2">
            <input className="flex-1 px-3 py-2 rounded-md bg-transparent outline-none" placeholder="Ask question using the sources uploaded" />
            <button className="card">Expand search ▾</button>
            <button className="card">➤</button>
          </div>
        </div>
      </div>
    </div>
  );
}

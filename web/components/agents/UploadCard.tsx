"use client";
import { useRef, useState } from "react";

export default function UploadCard({ label }: { label: string }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  return (
    <div className="card min-h-[200px] flex flex-col items-center justify-center text-center border-dashed">
      <div className="text-2xl">📄</div>
      <div className="mt-2 font-medium">{label}</div>
      <div className="text-sm text-muted">Drag and drop PDF or choose a file</div>
      <div className="mt-3">
        <button className="card" onClick={() => inputRef.current?.click()}>Choose a file</button>
        <input ref={inputRef} type="file" accept=".pdf" multiple hidden onChange={(e) => {
          const picked = Array.from(e.target.files || []);
          if (picked.length) setFiles(picked);
        }} />
      </div>
      <div className="text-xs text-muted mt-3">Uploaded files remain private and are not used to train models.</div>
      {files.length > 0 && (
        <div className="mt-3 w-full text-left">
          <div className="text-sm font-medium">Selected files</div>
          <ul className="text-sm text-muted list-disc pl-5 mt-1">
            {files.map((f, i) => <li key={`${f.name}-${i}`}>{f.name}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

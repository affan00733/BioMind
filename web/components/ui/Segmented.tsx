"use client";
import clsx from "classnames";

export default function Segmented({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex bg-surface border border-border rounded-full p-1">
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange(o)}
          className={clsx(
            "px-4 py-2 text-sm rounded-full transition-colors focus:outline-none",
            value === o ? "bg-[rgba(66,133,244,0.10)] text-[var(--accent)] border border-border" : "hover:bg-[rgba(66,133,244,0.08)]"
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

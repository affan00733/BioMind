"use client";
import { useMemo } from "react";

// Google-inspired playful palette
const GOOGLE_COLORS = ["#4285F4", "#EA4335", "#FBBC05", "#34A853"]; // blue, red, yellow, green

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export default function PopTitle({
  text = "BioMind",
  fontSize = "text-6xl md:text-7xl",
  weight = "font-extrabold",
  cycleMs = 2000,
  mode = "wave", // "wave" | "random"
  peakScale = 1.26,
  peakLiftPx = 4,
  baseScale = 0.94,
}: {
  text?: string;
  fontSize?: string; // tailwind size classes
  weight?: string; // tailwind weight classes
  cycleMs?: number; // base animation duration
  mode?: "wave" | "random";
  peakScale?: number;
  peakLiftPx?: number;
  baseScale?: number;
}) {
  const letters = useMemo(() => text.split(""), [text]);

  return (
    <h1
      className={`relative inline-flex items-end ${fontSize} ${weight}`}
      aria-label={text}
      style={{
        // CSS vars for keyframes
        // @ts-ignore - CSS custom properties
        "--peak-scale": peakScale as any,
        // @ts-ignore
        "--peak-lift": `${peakLiftPx}px` as any,
        // @ts-ignore
        "--base-scale": baseScale as any,
      }}
    >
      {letters.map((ch, idx) => {
        if (ch === " ") return <span key={`space-${idx}`} className="inline-block w-2" aria-hidden />;
        const color = GOOGLE_COLORS[idx % GOOGLE_COLORS.length];
        const delay = mode === "wave" ? idx * (cycleMs / 10) : rand(0, cycleMs * 0.6);
        const duration = cycleMs + (mode === "wave" ? 0 : rand(-150, 150));
        return (
          <span
            key={`${ch}-${idx}`}
            className="inline-block pop-letter"
            style={{
              color,
              animationDelay: `${delay}ms`,
              animationDuration: `${duration}ms`,
              textShadow: `0 4px 28px ${color}66`,
            }}
          >
            {ch}
          </span>
        );
      })}
      <style jsx>{`
        .pop-letter {
          transform-origin: 50% 80%;
          animation-name: popCycle;
          animation-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
          animation-iteration-count: infinite;
        }
        @keyframes popCycle {
          0% { opacity: 0.9; transform: translateY(0) scale(var(--base-scale, 0.94)); filter: saturate(0.9); }
          12% { opacity: 1; transform: translateY(calc(var(--peak-lift, 4px) * -1)) scale(var(--peak-scale, 1.26)); filter: saturate(1.25) brightness(1.06); }
          24% { opacity: 1; transform: translateY(0) scale(1.02); }
          60% { opacity: 1; transform: translateY(0) scale(1.00); }
          100% { opacity: 0.92; transform: translateY(0) scale(0.98); }
        }
        @media (prefers-reduced-motion: reduce) {
          .pop-letter { animation: none !important; }
        }
      `}</style>
    </h1>
  );
}

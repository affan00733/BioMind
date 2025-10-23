"use client";
import { useEffect, useMemo, useRef, useState } from "react";

const PALETTE = [
  "#a78bfa", // purple-300
  "#6366f1", // indigo-500
  "#06b6d4", // cyan-500
  "#22d3ee", // cyan-400
  "#34d399", // emerald-400
  "#f472b6", // pink-400
];

function random(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export default function DynamicWords({
  words = [
    "BioMind",
    "Vertex AI",
    "RAG",
    "Gemini",
    "Matching Engine",
    "PubMed",
    "UniProt",
    "Agents",
    "Collections",
  ],
  density = 8,
}: {
  words?: string[];
  density?: number; // how many simultaneous pops
}) {
  const [items, setItems] = useState<
    { id: number; word: string; x: number; y: number; color: string; size: number; life: number }[]
  >([]);
  const idRef = useRef(0);

  // Generate a new item
  function spawn() {
    const id = ++idRef.current;
    const word = words[Math.floor(Math.random() * words.length)];
    const color = PALETTE[Math.floor(Math.random() * PALETTE.length)];
    const x = random(10, 90); // vw
    const y = random(10, 70); // vh
    const size = random(16, 40); // px
    const life = random(1800, 3000); // ms
    setItems((prev) => [...prev, { id, word, x, y, color, size, life }]);
    // auto-remove after life
    setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), life);
  }

  useEffect(() => {
    // initial fill
    for (let i = 0; i < density; i++) spawn();
    // cadence spawn
    const t = setInterval(() => {
      spawn();
    }, 650);
    return () => clearInterval(t);
  }, [density]);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {items.map((i) => (
        <span
          key={i.id}
          style={{
            position: "absolute",
            left: `${i.x}vw`,
            top: `${i.y}vh`,
            color: i.color,
            fontWeight: 800,
            fontSize: `${i.size}px`,
            textShadow: `0 2px 20px ${i.color}40`,
            transform: `translate(-50%, -50%) scale(1)`,
            animation: `popfade ${i.life}ms ease-out forwards`,
            whiteSpace: "nowrap",
          }}
        >
          {i.word}
        </span>
      ))}
      <style jsx>{`
        @keyframes popfade {
          0% { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
          10% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
          80% { opacity: 1; transform: translate(-50%, -55%) scale(1.02); }
          100% { opacity: 0; transform: translate(-50%, -55%) scale(1.02); }
        }
      `}</style>
    </div>
  );
}

"use client";
import { useState } from "react";
import AppShell from "@/components/AppShell";
import PopTitle from "@/components/PopTitle";
import Button from "@/components/ui/Button";

export default function PlaygroundPage() {
  const [mode, setMode] = useState<"wave" | "random">("wave");
  const [cycleMs, setCycleMs] = useState(2000);
  const [peakScale, setPeakScale] = useState(1.26);
  const [peakLift, setPeakLift] = useState(4);
  const [baseScale, setBaseScale] = useState(0.94);

  function setPresetGoogley() {
    setMode("wave");
    setCycleMs(2000);
    setPeakScale(1.26);
    setPeakLift(4);
    setBaseScale(0.94);
  }

  function setPresetPunchy() {
    setMode("wave");
    setCycleMs(1800);
    setPeakScale(1.32);
    setPeakLift(6);
    setBaseScale(0.92);
  }

  function setPresetSubtle() {
    setMode("wave");
    setCycleMs(2400);
    setPeakScale(1.12);
    setPeakLift(2);
    setBaseScale(0.97);
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto">
        <h1 className="text-3xl font-bold mb-4">PopTitle Playground</h1>
        <p className="text-sm text-muted mb-6">Tune the animation to match your reference video, then we can lock these values into the homepage.</p>

        <div className="card mb-6 flex items-center justify-center h-48 md:h-60">
          <PopTitle text="BioMind" cycleMs={cycleMs} mode={mode} peakScale={peakScale} peakLiftPx={peakLift} baseScale={baseScale} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card">
            <div className="flex items-center justify-between">
              <label className="text-sm">Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                className="bg-transparent border border-border rounded px-2 py-1"
              >
                <option value="wave">wave</option>
                <option value="random">random</option>
              </select>
            </div>
            <div className="mt-3">
              <label className="text-sm">Cycle (ms): {cycleMs}</label>
              <input type="range" min={1200} max={3000} step={50} value={cycleMs} onChange={(e) => setCycleMs(Number(e.target.value))} className="w-full" />
            </div>
            <div className="mt-3">
              <label className="text-sm">Peak scale: {peakScale.toFixed(2)}</label>
              <input type="range" min={1.05} max={1.40} step={0.01} value={peakScale} onChange={(e) => setPeakScale(Number(e.target.value))} className="w-full" />
            </div>
            <div className="mt-3">
              <label className="text-sm">Peak lift (px): {peakLift}</label>
              <input type="range" min={0} max={10} step={1} value={peakLift} onChange={(e) => setPeakLift(Number(e.target.value))} className="w-full" />
            </div>
            <div className="mt-3">
              <label className="text-sm">Base scale: {baseScale.toFixed(2)}</label>
              <input type="range" min={0.88} max={1.00} step={0.01} value={baseScale} onChange={(e) => setBaseScale(Number(e.target.value))} className="w-full" />
            </div>
          </div>
          <div className="card space-y-3">
            <div className="text-sm font-semibold">Presets</div>
            <div className="flex gap-2">
              <Button data-variant="default" onClick={setPresetGoogley}>Googley</Button>
              <Button data-variant="default" onClick={setPresetPunchy}>Punchy</Button>
              <Button data-variant="default" onClick={setPresetSubtle}>Subtle</Button>
            </div>
            <div className="text-xs text-muted">Tip: open your video beside this page and dial in these sliders to match the cadence, bounce and glow. Then I can bake the chosen values into the homepage.</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

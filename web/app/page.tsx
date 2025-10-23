import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" aria-hidden>
          <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full blur-3xl" style={{ background: "radial-gradient(closest-side, rgba(66,133,244,0.18), transparent)" }} />
          <div className="absolute -bottom-24 -right-24 h-80 w-80 rounded-full blur-3xl" style={{ background: "radial-gradient(closest-side, rgba(52,168,83,0.15), transparent)" }} />
        </div>
        <div className="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center relative">
          <div className="inline-flex items-center gap-2 text-[var(--accent)] font-medium bg-[rgba(255,255,255,0.7)] backdrop-blur px-3 py-1.5 rounded-full border" style={{ borderColor: "var(--border)" }}>
            <span className="h-2 w-2 rounded-full bg-[#34A853]" />
            Futuristic AI for Biology
          </div>
          <h1 className="mt-4 text-5xl md:text-7xl font-extrabold tracking-tight text-text">BioMind — Where Biology Meets Intelligence</h1>
          <p className="mt-4 text-lg text-muted max-w-3xl mx-auto">Clean, minimal, and built with Google-inspired design. A calm, intelligent surface for AI-driven discovery—with citations you can trust.</p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link href="/search" className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-white" style={{ background: "var(--accent)", boxShadow: "0 12px 30px rgba(66,133,244,0.35)" }}>Get Started</Link>
            <Link href="/collections" className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border text-text" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>Manage Sources</Link>
          </div>
        </div>
      </section>

      {/* Feature cards */}
      <section className="py-12">
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          {[{t:"AI Analysis",d:"Summarize, explain, and reason over complex biomedical text."},{t:"Genomic Prediction",d:"Predict variants and interpret signals with modern models."},{t:"Cited Answers",d:"Every answer is backed by sources you can inspect."}].map((c) => (
            <div key={c.t} className="bg-[var(--surface)] border" style={{ borderColor: "var(--border)", borderRadius: 16, padding: 20, boxShadow: "0 8px 30px rgba(17,24,39,0.06)" }}>
              <div className="text-sm font-semibold text-[var(--accent)]">{c.t}</div>
              <div className="text-muted mt-1 text-sm">{c.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Demo teaser */}
      <section className="py-8">
        <div className="max-w-6xl mx-auto px-6">
          <div className="bg-[var(--surface)] border" style={{ borderColor: "var(--border)", borderRadius: 16, overflow: "hidden", boxShadow: "0 8px 30px rgba(17,24,39,0.06)" }}>
            <video controls className="w-full" poster="/api/placeholder/1200x675">
              <source src="/Screen%20Recording%202025-10-20%20at%203.01.29%20PM.mp4" type="video/mp4" />
            </video>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-8 py-10 border-t" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-6xl mx-auto px-6 text-sm text-muted flex flex-col md:flex-row items-center justify-between gap-3">
          <div>© {new Date().getFullYear()} BioMind</div>
          <div className="flex items-center gap-4">
            <a href="mailto:biomindllmagent@gmail.com" className="hover:underline">biomindllmagent@gmail.com</a>
            <a href="https://github.com/affan00733/BioMind" className="hover:underline" target="_blank" rel="noopener noreferrer">GitHub</a>
            <span>Google Hackathon</span>
          </div>
        </div>
      </footer>
    </main>
  );
}

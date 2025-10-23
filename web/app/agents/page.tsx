import AppShell from "@/components/AppShell";
import Link from "next/link";
import { AGENTS } from "@/lib/agents";

export default function AgentsPage() {
  return (
    <AppShell>
      <h1 className="text-3xl font-bold">Agents (Beta)</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {AGENTS.map((a) => (
          <Link key={a.slug} href={`/agents/${a.slug}`} className="card block text-left hover:border-accent">
            <div className="font-medium">{a.name}</div>
            <p className="text-sm text-muted mt-1">{a.description}</p>
            <div className="text-sm mt-3 text-accent font-medium">{a.cta || "Open"} →</div>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}

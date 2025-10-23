"use client";
import { useParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import { AGENTS } from "@/lib/agents";
import AgentHero from "@/components/agents/AgentHero";
import UploadCard from "@/components/agents/UploadCard";
import QueryBox from "@/components/agents/QueryBox";

export default function AgentPage() {
  const params = useParams();
  const slug = (params?.slug as string) || "";
  const agent = AGENTS.find((a) => a.slug === slug);

  return (
    <AppShell>
      {!agent ? (
        <div className="card">Agent not found.</div>
      ) : (
        <div className="max-w-4xl mx-auto space-y-4">
          <AgentHero title={agent.name} description={agent.description} cta={agent.cta} />
          {agent.mode === "upload" ? (
            <UploadCard label={agent.cta || "Upload"} />
          ) : (
            <QueryBox placeholder="Enter your query" primaryCta={agent.cta || "Run"} />
          )}
        </div>
      )}
    </AppShell>
  );
}

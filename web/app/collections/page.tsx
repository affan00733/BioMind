"use client";
import AppShell from "@/components/AppShell";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { useCollections } from "@/lib/collections";
import { useRouter } from "next/navigation";
import { Ellipsis, Plus, Folder } from "lucide-react";

export default function CollectionsListPage() {
  const { collections, addCollection } = useCollections();
  const router = useRouter();
  const handleCreate = () => {
    const name = addCollection();
    router.push(`/collections/${encodeURIComponent(name)}`);
  };
  return (
    <AppShell>
      <h1 className="text-2xl font-semibold">Source collection</h1>
      {/* Hero banner */}
      <section className="mt-4 max-w-5xl">
        <div className="card flex items-center justify-between overflow-hidden">
          <div className="p-2">
            <div className="text-xl md:text-2xl font-semibold">Gather research materials you trust and gain deep insight</div>
            <p className="text-sm text-muted mt-2">Freely upload PDFs, notes and URLs.</p>
          </div>
          <div className="hidden md:flex items-center justify-center pr-6 opacity-80">
            <div className="w-48 h-24 rounded-lg bg-[rgba(255,255,255,0.06)] border border-border" />
          </div>
        </div>
      </section>

      {/* Grid of collections */}
      <section className="mt-5 max-w-5xl">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* New collection card */}
          <button
            onClick={handleCreate}
            className="rounded-xl border border-dashed border-green-500/40 hover:border-green-400/60 hover:bg-green-500/5 p-4 text-left"
          >
            <div className="flex items-center gap-2 text-green-400">
              <Plus className="h-4 w-4" />
              <span className="font-medium">New collection</span>
            </div>
          </button>

          {/* Existing collections */}
          {collections.map((c) => (
            <Link key={c} href={`/collections/${encodeURIComponent(c)}`} className="card group p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 font-medium">
                    <Folder className="h-4 w-4 text-muted" /> {c}
                  </div>
                  <div className="text-sm text-muted">0 source</div>
                </div>
                <Ellipsis className="h-4 w-4 text-muted opacity-0 group-hover:opacity-100" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

"use client";
import Sidebar from "@/components/Sidebar";
import { ReactNode } from "react";
import { useCollections } from "@/lib/collections";

export default function AppShell({ children }: { children: ReactNode }) {
  const { collections } = useCollections();
  return (
    <div className="relative flex min-h-screen overflow-hidden bg-background text-text">
      <Sidebar collections={collections} />
      <main className="relative flex-1 p-8">{children}</main>
    </div>
  );
}

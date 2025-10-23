"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import clsx from "classnames";
import { AGENTS } from "@/lib/agents";
import {
  Grid2x2,
  Plus,
  FolderOpen,
  Star,
  Workflow,
  CheckCircle2,
  BookmarkPlus,
  BookOpen,
  Share2,
  Users,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Sun,
  Moon,
} from "lucide-react";
import { useTheme } from "@/components/theme/ThemeProvider";

type Props = { collections: string[] };

const agentIconFor = (slug: string) => {
  switch (slug) {
    case "hypothesis-generator":
      return <Workflow className="h-4 w-4 text-green-400" />;
    case "hypothesis-evaluator":
      return <CheckCircle2 className="h-4 w-4 text-green-400" />;
    case "citation-recommender":
      return <BookmarkPlus className="h-4 w-4 text-green-400" />;
    case "literature-review":
      return <BookOpen className="h-4 w-4 text-green-400" />;
    case "research-tracer":
      return <Share2 className="h-4 w-4 text-green-400" />;
    case "survey-simulator":
      return <Users className="h-4 w-4 text-green-400" />;
    case "peer-review":
      return <ShieldCheck className="h-4 w-4 text-green-400" />;
    default:
      return <Workflow className="h-4 w-4 text-green-400" />;
  }
};

export default function Sidebar({}: Props) {
  const pathname = usePathname();
  const [profileOpen, setProfileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const { choice, setTheme } = useTheme();
  const [showAppearance, setShowAppearance] = useState(false);

  // Collapse/expand via scroll gesture: scroll up to expand, down to collapse
  function onWheel(e: React.WheelEvent) {
    if (e.deltaY < -20 && collapsed) setCollapsed(false);
    if (e.deltaY > 20 && !collapsed) setCollapsed(true);
  }

  // Close dropdown when collapsing
  useEffect(() => {
    if (collapsed) setProfileOpen(false);
  }, [collapsed]);
  return (
    <aside
      className={`${collapsed ? "w-16" : "w-72"} transition-all duration-200 min-h-screen border-r border-border bg-[var(--surface)] text-text p-3 flex flex-col relative`}
      onWheel={onWheel}
    >
      {/* Header */}
      <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"} px-2 py-2 mb-2`}>
        {!collapsed && <div className="text-lg font-extrabold" style={{ color: "var(--accent)" }}>BioMind</div>}
        <button
          className="p-2 rounded-md hover:bg-[rgba(255,255,255,0.06)] dark:hover:bg-[rgba(255,255,255,0.06)]"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Grid2x2 className="h-4 w-4" />
        </button>
      </div>

      {/* Primary links */}
      <nav className="space-y-1 mb-3">
        <Link
          href="/search"
          className={clsx(
            "flex items-center px-3 py-2 rounded-lg",
            pathname === "/search" ? "bg-[rgba(255,255,255,0.06)]" : "hover:bg-[rgba(255,255,255,0.06)]"
          )}
        >
          <span className={clsx("flex items-center gap-2", collapsed && "justify-center w-full")}> 
            <Plus className="h-4 w-4" />
            {!collapsed && <span>New question</span>}
          </span>
          {!collapsed && (
            <span className="ml-auto text-xs text-muted border border-border rounded px-1.5 py-0.5">⌘K</span>
          )}
        </Link>

        <Link
          href="/collections"
          className={clsx(
            "flex items-center gap-2 px-3 py-2 rounded-lg",
            pathname?.startsWith("/collections") ? "bg-[rgba(255,255,255,0.06)]" : "hover:bg-[rgba(255,255,255,0.06)]"
          )}
        >
          <FolderOpen className="h-4 w-4" />
          {!collapsed && <span>Source collection</span>}
        </Link>

        <Link
          href="/starred"
          className={clsx(
            "flex items-center gap-2 px-3 py-2 rounded-lg",
            pathname === "/starred" ? "bg-[rgba(255,255,255,0.06)]" : "hover:bg-[rgba(255,255,255,0.06)]"
          )}
        >
          <Star className="h-4 w-4" />
          {!collapsed && <span>Starred</span>}
        </Link>
      </nav>

      {/* Agents */}
      {!collapsed && (
        <div className="px-2 text-sm text-muted font-semibold flex items-center gap-2">
          Agents
          <span className="text-[10px] bg-red-500/10 text-red-600 rounded-full px-2 py-0.5">Beta</span>
        </div>
      )}
      <div className="mt-2 space-y-1">
        {AGENTS.map((a) => (
          <Link
            key={a.slug}
            href={`/agents/${a.slug}`}
            className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-lg",
              pathname?.startsWith(`/agents/${a.slug}`)
                ? "bg-[rgba(66,133,244,0.10)]"
                : "hover:bg-[rgba(66,133,244,0.08)]"
            )}
          >
            {agentIconFor(a.slug)}
            {!collapsed && <span className="font-medium">{a.name}</span>}
          </Link>
        ))}
      </div>

      {/* Promo card removed per user request */}

      {/* Account footer */}
      <div className="mt-auto pt-3">
        <button
          type="button"
          className="w-full flex items-center justify-between px-2 py-2 rounded-lg hover:bg-[rgba(255,255,255,0.06)]"
          onClick={() => (collapsed ? setCollapsed(false) : setProfileOpen((v) => !v))}
          aria-expanded={profileOpen}
        >
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-full bg-[rgba(66,133,244,0.12)] grid place-items-center text-sm font-semibold text-[var(--accent)]">M</div>
            {!collapsed && (
              <div className="leading-tight text-left">
                <div className="text-sm">Mohneet San...</div>
                <div className="text-[10px] text-muted border border-border rounded px-1 py-0.5 inline-block">Personal</div>
              </div>
            )}
          </div>
          {collapsed ? (
            <ChevronDown className="h-4 w-4 text-muted" />
          ) : profileOpen ? (
            <ChevronDown className="h-4 w-4 text-muted" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted" />
          )}
        </button>

        {/* Dropdown menu */}
        {profileOpen && !collapsed && (
          <div className="absolute left-2 right-2 bottom-16 rounded-xl border border-border bg-[var(--surface)] shadow-lg overflow-visible z-40">
            <div className="px-3 py-2 text-xs text-muted border-b border-border truncate">mohneet@umd.edu</div>
            <div className="py-1">
              <button className="w-full text-left px-3 py-2 text-sm hover:bg-[rgba(255,255,255,0.06)]">Personal settings</button>
              <button className="w-full text-left px-3 py-2 text-sm hover:bg-[rgba(255,255,255,0.06)]">Custom Instructions</button>
              <button className="w-full text-left px-3 py-2 text-sm hover:bg-[rgba(255,255,255,0.06)]">Support</button>
              {/* Appearance submenu */}
              <div className="relative group">
                <button
                  className="w-full px-3 py-2 text-sm hover:bg-[rgba(255,255,255,0.06)] flex items-center justify-between rounded-lg"
                  onClick={() => setShowAppearance((v) => !v)}
                >
                  <span className="flex items-center gap-2">
                    <Moon className="h-4 w-4" />
                    Appearance
                  </span>
                  <span className="text-muted">›</span>
                </button>
                {/* Inline submenu for small screens */}
                {showAppearance && (
                  <div className="mt-2 rounded-xl border border-border bg-[var(--surface)] shadow-sm p-2 space-y-1 lg:hidden">
                    <button onClick={() => setTheme("light")} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[rgba(0,0,0,0.04)] ${choice==="light" ? "text-[var(--accent)]" : ""}`}>
                      <Sun className="h-4 w-4 text-[var(--accent)]" />
                      <span>Light mode</span>
                    </button>
                    <button onClick={() => setTheme("dark")} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[rgba(0,0,0,0.04)] ${choice==="dark" ? "text-[var(--text)]" : ""}`}>
                      <Moon className="h-4 w-4" />
                      <span>Dark mode</span>
                    </button>
                  </div>
                )}
                {/* Flyout submenu for large screens */}
                <div className={`${showAppearance ? "lg:block" : "hidden lg:group-hover:block"} absolute left-full top-0 ml-2 w-56 rounded-xl border border-border bg-[var(--surface)] shadow-xl p-2 space-y-1 z-50 translate-x-0 rtl:-translate-x-full`}>
                  <button onClick={() => setTheme("light")} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[rgba(0,0,0,0.04)] ${choice==="light" ? "text-[var(--accent)]" : ""}`}>
                    <Sun className="h-4 w-4 text-[var(--accent)]" />
                    <span>Light mode</span>
                  </button>
                  <button onClick={() => setTheme("dark")} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[rgba(0,0,0,0.04)] ${choice==="dark" ? "text-[var(--text)]" : ""}`}>
                    <Moon className="h-4 w-4" />
                    <span>Dark mode</span>
                  </button>
                </div>
              </div>
              <button className="w-full text-left px-3 py-2 text-sm hover:bg-[rgba(255,255,255,0.06)]">Sign Out</button>
            </div>
            <div className="border-t border-border px-3 py-2 text-xs text-muted">Switch workspace</div>
            <div className="px-3 pb-3">
              <div className="flex items-center justify-between px-2 py-2 rounded-lg hover:bg-[rgba(255,255,255,0.06)]">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded-full bg-[rgba(66,133,244,0.12)] grid place-items-center text-xs font-semibold text-[var(--accent)]">M</div>
                  <div className="text-sm">Mohneet San...</div>
                </div>
                <span className="text-[10px] text-muted border border-border rounded px-1 py-0.5">Personal</span>
              </div>
              <button className="mt-2 w-full rounded-lg border border-border py-2 text-sm hover:bg-[rgba(255,255,255,0.06)]">
                Start team plan
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

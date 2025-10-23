import AppShell from "@/components/AppShell";

export default function HistoryPage() {
  return (
    <AppShell>
      <h1 className="text-2xl font-semibold">History</h1>
      <p className="text-sm text-muted mt-2">Your recent searches and answers will appear here.</p>
      <div className="mt-4 space-y-3">
        {[1,2,3].map((i) => (
          <div key={i} className="card">
            <div className="text-sm text-muted">Yesterday</div>
            <div className="mt-1">Sample question #{i}</div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}

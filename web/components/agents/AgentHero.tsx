export default function AgentHero({ title, description, cta }: { title: string; description: string; cta?: string }) {
  return (
    <div className="card">
      <div className="flex items-start gap-4">
        <div className="text-3xl">🧠</div>
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="text-sm text-muted mt-1">{description}</p>
          {cta && <button className="card mt-3 inline-flex items-center">{cta}</button>}
        </div>
      </div>
    </div>
  );
}

import AppShell from "@/components/AppShell";
import CollectionDetail from "@/components/collection/CollectionDetail";

export default function CollectionDetailPage({ params }: { params: { name: string } }) {
  const name = decodeURIComponent(params.name);
  return (
    <AppShell>
      <CollectionDetail name={name} />
    </AppShell>
  );
}

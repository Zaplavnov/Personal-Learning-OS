import { ConceptDetailScreen } from "@/features/concepts/concept-detail-screen";

export default async function ConceptPage({
  params,
}: {
  params: Promise<{ conceptId: string }>;
}) {
  const { conceptId } = await params;
  return <ConceptDetailScreen conceptId={conceptId} />;
}

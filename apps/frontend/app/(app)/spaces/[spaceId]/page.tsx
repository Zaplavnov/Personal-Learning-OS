import { SpaceDetailScreen } from "@/features/spaces/space-detail-screen";

export default async function SpaceDetailPage({
  params,
}: {
  params: Promise<{ spaceId: string }>;
}) {
  const { spaceId } = await params;
  return <SpaceDetailScreen spaceId={spaceId} />;
}

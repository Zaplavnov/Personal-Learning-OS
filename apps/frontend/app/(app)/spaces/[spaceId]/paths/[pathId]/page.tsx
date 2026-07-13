import { LearningPathScreen } from "@/features/learning-paths/learning-path-screen";

export default async function LearningPathPage({ params }: { params: Promise<{ spaceId: string; pathId: string }> }) {
  const { spaceId, pathId } = await params;
  return <LearningPathScreen spaceId={spaceId} pathId={pathId} />;
}

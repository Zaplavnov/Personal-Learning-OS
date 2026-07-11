import { MaterialDetailScreen } from "@/features/materials/material-detail-screen";

export default async function MaterialDetailPage({
  params,
}: {
  params: Promise<{ materialId: string }>;
}) {
  const { materialId } = await params;
  return <MaterialDetailScreen materialId={materialId} />;
}

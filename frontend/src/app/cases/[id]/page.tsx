import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import CaseDetailPage from "./case-detail-client";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "demo" }];
}

export default function Page({ params }: { params: { id: string } }) {
  return (
    <Suspense fallback={<CaseDetailFallback />}>
      <CaseDetailPage caseId={params.id} />
    </Suspense>
  );
}

function CaseDetailFallback() {
  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <Skeleton className="h-20" />
      <Skeleton className="h-80" />
    </div>
  );
}

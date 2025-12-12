'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

// Dynamically import GraphContainer to prevent SSR issues with Three.js/WebGL
const GraphContainer = dynamic(
  () => import('@/components/graph/graph-container').then((mod) => mod.GraphContainer),
  {
    ssr: false,
    loading: () => (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    ),
  }
);

function GraphContent() {
  const searchParams = useSearchParams();
  const entityId = searchParams.get('entity') || undefined;

  return <GraphContainer focusEntityId={entityId} />;
}

export default function GraphPage() {
  return (
    <div className="h-[calc(100vh-7rem)] md:h-[calc(100vh-9rem)]">
      {/* Header - hidden on mobile to maximize graph space */}
      <div className="hidden md:block mb-6 space-y-2">
        <h1 className="text-2xl lg:text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
          Knowledge Graph
        </h1>
        <p className="text-muted-foreground text-base lg:text-lg">
          Explore entities and relationships extracted from your documents
        </p>
      </div>

      {/* Graph container - full height on mobile, adjusted on desktop */}
      <div className="h-full md:h-[calc(100%-5rem)] border border-border/50 rounded-lg md:rounded-xl overflow-hidden shadow-lg bg-card">
        <Suspense fallback={
          <div className="h-full flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        }>
          <GraphContent />
        </Suspense>
      </div>
    </div>
  );
}

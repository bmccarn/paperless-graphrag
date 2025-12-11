'use client';

import { SyncControls, TaskList } from '@/components/operations';

export default function OperationsPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
          Operations
        </h1>
        <p className="text-muted-foreground text-lg">
          Manage sync operations and monitor background tasks
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <SyncControls />
        <div className="lg:col-span-2">
          <TaskList />
        </div>
      </div>
    </div>
  );
}

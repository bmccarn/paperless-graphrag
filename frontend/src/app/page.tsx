'use client';

import {
  HealthStatus,
  StatsCard,
  QuickActions,
  ActivityFeed,
} from '@/components/dashboard';
import { EntityChart } from '@/components/dashboard/entity-chart';
import { ActivityChart } from '@/components/dashboard/activity-chart';

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p className="text-muted-foreground text-lg">
          Monitor your Paperless GraphRAG system
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <HealthStatus />
        <QuickActions />
        <ActivityFeed />
      </div>

      <StatsCard />

      <div className="grid gap-6 md:grid-cols-2">
        <EntityChart />
        <ActivityChart />
      </div>
    </div>
  );
}

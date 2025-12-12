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
    <div className="space-y-4 md:space-y-8">
      <div className="space-y-1 md:space-y-2">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p className="text-muted-foreground text-sm md:text-lg">
          Monitor your Paperless GraphRAG system
        </p>
      </div>

      <div className="grid gap-4 md:gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        <HealthStatus />
        <QuickActions />
        <ActivityFeed />
      </div>

      <StatsCard />

      <div className="grid gap-4 md:gap-6 grid-cols-1 md:grid-cols-2">
        <EntityChart />
        <ActivityChart />
      </div>
    </div>
  );
}

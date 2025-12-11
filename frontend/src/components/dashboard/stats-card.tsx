'use client';

import { FileText, Database, Clock, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useStats } from '@/lib/hooks';
import { formatRelativeTime } from '@/lib/utils';

interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}

function StatItem({ icon, label, value }: StatItemProps) {
  return (
    <div className="flex items-center space-x-4 p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 transition-colors">
      <div className="p-3 bg-primary/10 rounded-xl shadow-sm">{icon}</div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold text-foreground">{value}</p>
      </div>
    </div>
  );
}

export function StatsCard() {
  const { stats, isLoading, error } = useStats();

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
        <CardHeader>
          <CardTitle>Statistics</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center space-x-4 p-4 rounded-xl bg-secondary/30">
              <Skeleton className="h-12 w-12 rounded-xl" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-6 w-16" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
        <CardHeader>
          <CardTitle>Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Failed to load statistics
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
      <CardHeader>
        <CardTitle>Statistics</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatItem
          icon={<FileText className="h-5 w-5 text-primary" />}
          label="Total Documents"
          value={stats?.total_documents ?? 0}
        />
        <StatItem
          icon={<Database className="h-5 w-5 text-primary" />}
          label="Index Version"
          value={stats?.index_version ?? 0}
        />
        <StatItem
          icon={<RefreshCw className="h-5 w-5 text-primary" />}
          label="Last Full Sync"
          value={formatRelativeTime(stats?.last_full_sync ?? null)}
        />
        <StatItem
          icon={<Clock className="h-5 w-5 text-primary" />}
          label="Last Incremental"
          value={formatRelativeTime(stats?.last_incremental_sync ?? null)}
        />
      </CardContent>
    </Card>
  );
}

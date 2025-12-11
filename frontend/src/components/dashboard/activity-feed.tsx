'use client';

import { CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useTasks } from '@/lib/hooks';
import { formatRelativeTime, formatDuration } from '@/lib/utils';
import type { TaskStatus } from '@/types';

const statusConfig: Record<TaskStatus, { icon: React.ReactNode; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { icon: <Clock className="h-3 w-3" />, variant: 'secondary' },
  running: { icon: <Loader2 className="h-3 w-3 animate-spin" />, variant: 'default' },
  completed: { icon: <CheckCircle className="h-3 w-3" />, variant: 'outline' },
  failed: { icon: <XCircle className="h-3 w-3" />, variant: 'destructive' },
};

export function ActivityFeed() {
  const { tasks, isLoading, error } = useTasks(undefined, 10000);

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/80">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/80">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Failed to load activity</p>
        </CardContent>
      </Card>
    );
  }

  const recentTasks = tasks.slice(0, 5);

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/80">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {recentTasks.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No recent activity
          </p>
        ) : (
          <ScrollArea className="h-[200px]">
            <div className="space-y-3">
              {recentTasks.map((task) => {
                const config = statusConfig[task.status];
                return (
                  <div
                    key={task.task_id}
                    className="flex items-start justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors cursor-default"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <Badge variant={config.variant} className="text-xs shadow-sm">
                          {config.icon}
                          <span className="ml-1">{task.status}</span>
                        </Badge>
                        <span className="text-sm font-medium">{task.task_type}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {formatRelativeTime(task.created_at)}
                        {task.duration_seconds && ` • ${formatDuration(task.duration_seconds)}`}
                      </p>
                    </div>
                    {task.error && (
                      <span className="text-xs text-destructive max-w-[150px] truncate">
                        {task.error}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

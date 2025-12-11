'use client';

import { CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useHealth } from '@/lib/hooks';
import { formatRelativeTime } from '@/lib/utils';

export function HealthStatus() {
  const { health, isLoading, error, refetch } = useHealth();

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/80">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>System Health</span>
            <Skeleton className="h-6 w-20" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-destructive/5">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>System Health</span>
            <Badge variant="destructive" className="shadow-sm">Error</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2 text-destructive">
            <XCircle className="h-5 w-5" />
            <span>Failed to connect to backend</span>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            The backend may be busy indexing or not running.
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => refetch()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isHealthy = health?.status === 'healthy';

  return (
    <Card className={`shadow-lg border-0 bg-gradient-to-br ${isHealthy ? 'from-card to-green-500/5' : 'from-card to-yellow-500/5'}`}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>System Health</span>
          <Badge
            variant={isHealthy ? 'default' : 'secondary'}
            className={`shadow-sm ${isHealthy ? 'bg-green-500 hover:bg-green-600' : ''}`}
          >
            {health?.status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between p-2 rounded-lg bg-secondary/50">
          <span className="text-sm text-muted-foreground">Paperless Connected</span>
          <div className="flex items-center space-x-2">
            {health?.paperless_connected ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4 text-destructive" />
            )}
            <span className="text-sm font-medium">
              {health?.paperless_connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between p-2 rounded-lg bg-secondary/50">
          <span className="text-sm text-muted-foreground">GraphRAG Initialized</span>
          <div className="flex items-center space-x-2">
            {health?.graphrag_initialized ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <AlertCircle className="h-4 w-4 text-yellow-500" />
            )}
            <span className="text-sm font-medium">
              {health?.graphrag_initialized ? 'Ready' : 'Not initialized'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between p-2 rounded-lg bg-secondary/50">
          <span className="text-sm text-muted-foreground">Last Sync</span>
          <span className="text-sm font-medium">{formatRelativeTime(health?.last_sync ?? null)}</span>
        </div>

        <div className="flex items-center justify-between p-2 rounded-lg bg-primary/10">
          <span className="text-sm text-muted-foreground">Documents</span>
          <span className="text-lg font-bold text-primary">{health?.document_count ?? 0}</span>
        </div>
      </CardContent>
    </Card>
  );
}

'use client';

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Trash2,
  ChevronRight,
  Plus,
  RefreshCw,
  MinusCircle,
  RotateCcw,
  FileCheck,
  AlertTriangle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useTasks } from '@/lib/hooks';
import { cleanupTasks } from '@/lib/api';
import { formatRelativeTime, formatDuration } from '@/lib/utils';
import { toast } from 'sonner';
import type { Task, TaskStatus, SyncResult } from '@/types';

const statusConfig: Record<TaskStatus, { icon: React.ReactNode; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { icon: <Clock className="h-4 w-4" />, variant: 'secondary' },
  running: { icon: <Loader2 className="h-4 w-4 animate-spin" />, variant: 'default' },
  completed: { icon: <CheckCircle className="h-4 w-4" />, variant: 'outline' },
  failed: { icon: <XCircle className="h-4 w-4" />, variant: 'destructive' },
};

// Check if a result looks like a sync result
function isSyncResult(result: unknown): result is SyncResult {
  if (!result || typeof result !== 'object') return false;
  const r = result as Record<string, unknown>;
  return (
    typeof r.added === 'number' ||
    typeof r.updated === 'number' ||
    typeof r.deleted === 'number' ||
    typeof r.recovered === 'number'
  );
}

// Display sync results in a nice format
function SyncResultDisplay({ result }: { result: SyncResult }) {
  const stats = [
    { key: 'added', label: 'Added', value: result.added || 0, icon: Plus, color: 'text-green-600' },
    { key: 'updated', label: 'Updated', value: result.updated || 0, icon: RefreshCw, color: 'text-blue-600' },
    { key: 'deleted', label: 'Deleted', value: result.deleted || 0, icon: MinusCircle, color: 'text-orange-600' },
    { key: 'recovered', label: 'Recovered', value: result.recovered || 0, icon: RotateCcw, color: 'text-purple-600' },
    { key: 'unchanged', label: 'Unchanged', value: result.unchanged || 0, icon: FileCheck, color: 'text-muted-foreground' },
    { key: 'errors', label: 'Errors', value: result.errors || 0, icon: AlertTriangle, color: 'text-destructive' },
  ].filter(s => s.value > 0 || s.key === 'errors' && result.errors);

  const total = (result.added || 0) + (result.updated || 0) + (result.deleted || 0) +
                (result.recovered || 0) + (result.unchanged || 0);

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3">
        {stats.map(({ key, label, value, icon: Icon, color }) => (
          <div
            key={key}
            className="flex items-center gap-2 p-3 rounded-lg bg-secondary/50"
          >
            <Icon className={`h-4 w-4 ${color}`} />
            <div>
              <p className={`text-lg font-semibold ${color}`}>{value}</p>
              <p className="text-xs text-muted-foreground">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Total processed */}
      <div className="text-sm text-muted-foreground text-center">
        {total} documents processed
      </div>

      {/* Indexing status if present */}
      {result.status && (
        <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
          <p className="text-sm font-medium text-primary">
            {result.operation === 'update' ? 'Incremental Index' : 'Full Index'}: {result.status}
          </p>
        </div>
      )}
    </div>
  );
}

// Display a quick summary of sync results for the task card
function SyncResultSummary({ result }: { result: SyncResult }) {
  const parts = [];
  if (result.added) parts.push(`+${result.added} added`);
  if (result.updated) parts.push(`${result.updated} updated`);
  if (result.deleted) parts.push(`${result.deleted} deleted`);
  if (result.recovered) parts.push(`${result.recovered} recovered`);
  if (result.errors) parts.push(`${result.errors} errors`);

  if (parts.length === 0) {
    if (result.unchanged) return <span className="text-muted-foreground">No changes ({result.unchanged} unchanged)</span>;
    return null;
  }

  return <span className="text-xs">{parts.join(', ')}</span>;
}

export function TaskList() {
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const { tasks, isLoading, error, refetch } = useTasks(
    statusFilter === 'all' ? undefined : statusFilter
  );

  const handleCleanup = async () => {
    try {
      const result = await cleanupTasks(24);
      toast.success('Cleanup complete', {
        description: `Removed ${result.removed} old tasks`,
      });
      refetch();
    } catch (error) {
      toast.error('Cleanup failed', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  return (
    <>
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/80">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Background Tasks</CardTitle>
              <CardDescription>
                Monitor sync and indexing tasks
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as TaskStatus | 'all')}
              >
                <SelectTrigger className="w-[140px] shadow-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tasks</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" onClick={handleCleanup} className="shadow-sm">
                <Trash2 className="h-4 w-4 mr-2" />
                Cleanup
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <p className="text-sm text-destructive text-center py-8">
              Failed to load tasks
            </p>
          ) : tasks.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No tasks found
            </p>
          ) : (
            <ScrollArea className="h-[400px]">
              <div className="space-y-2">
                {tasks.map((task) => {
                  const config = statusConfig[task.status];
                  const isRunning = task.status === 'running';
                  return (
                    <div
                      key={task.task_id}
                      className="p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 cursor-pointer transition-all select-none"
                      onClick={() => setSelectedTask(task)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && setSelectedTask(task)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge variant={config.variant} className="shadow-sm">
                            {config.icon}
                          </Badge>
                          <div>
                            <p className="font-medium text-sm">{task.task_type}</p>
                            <p className="text-xs text-muted-foreground">
                              {formatRelativeTime(task.created_at)}
                              {task.duration_seconds && ` • ${formatDuration(task.duration_seconds)}`}
                            </p>
                            {/* Show quick sync summary for completed sync tasks */}
                            {task.status === 'completed' && task.result && isSyncResult(task.result) && (
                              <div className="mt-1">
                                <SyncResultSummary result={task.result} />
                              </div>
                            )}
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                      {isRunning && task.progress_percent !== null && (
                        <div className="mt-3 space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">
                              {task.progress_message || 'Processing...'}
                            </span>
                            <span className="font-medium text-primary">
                              {task.progress_percent}%
                            </span>
                          </div>
                          <Progress value={task.progress_percent} className="h-2" />
                          {task.progress_detail && (
                            <p className="text-xs text-muted-foreground truncate">
                              {task.progress_detail}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selectedTask} onOpenChange={() => setSelectedTask(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Task Details</DialogTitle>
            <DialogDescription>
              Task ID: {selectedTask?.task_id}
            </DialogDescription>
          </DialogHeader>
          {selectedTask && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <Badge variant={statusConfig[selectedTask.status].variant}>
                    {statusConfig[selectedTask.status].icon}
                    <span className="ml-1">{selectedTask.status}</span>
                  </Badge>
                </div>
                <div>
                  <p className="text-muted-foreground">Type</p>
                  <p className="font-medium">{selectedTask.task_type}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Created</p>
                  <p>{formatRelativeTime(selectedTask.created_at)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Duration</p>
                  <p>{formatDuration(selectedTask.duration_seconds)}</p>
                </div>
              </div>

              {selectedTask.status === 'running' && selectedTask.progress_percent !== null && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {selectedTask.progress_message || 'Processing...'}
                    </span>
                    <span className="font-medium text-primary">
                      {selectedTask.progress_percent}%
                    </span>
                  </div>
                  <Progress value={selectedTask.progress_percent} className="h-3" />
                  {selectedTask.progress_detail && (
                    <p className="text-sm text-muted-foreground">
                      {selectedTask.progress_detail}
                    </p>
                  )}
                </div>
              )}

              {selectedTask.error && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Error</p>
                  <pre className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm overflow-auto">
                    {selectedTask.error}
                  </pre>
                </div>
              )}

              {selectedTask.result && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Result</p>
                  {isSyncResult(selectedTask.result) ? (
                    <SyncResultDisplay result={selectedTask.result} />
                  ) : (
                    <pre className="p-3 rounded-lg bg-muted text-sm overflow-auto max-h-[300px]">
                      {JSON.stringify(selectedTask.result, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

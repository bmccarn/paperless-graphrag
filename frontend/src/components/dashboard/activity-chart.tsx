'use client';

import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Skeleton } from '@/components/ui/skeleton';
import { getTasks } from '@/lib/api';
import type { Task } from '@/types';

const chartConfig: ChartConfig = {
  completed: {
    label: 'Completed',
    color: 'hsl(142, 71%, 45%)',
  },
  failed: {
    label: 'Failed',
    color: 'hsl(0, 84%, 60%)',
  },
  running: {
    label: 'Running',
    color: 'hsl(217, 91%, 60%)',
  },
};

export function ActivityChart() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getTasks();
        setTasks(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-chart-2/5">
        <CardHeader>
          <CardTitle>Task Activity</CardTitle>
          <CardDescription>Recent sync and indexing tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[200px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-chart-2/5">
        <CardHeader>
          <CardTitle>Task Activity</CardTitle>
          <CardDescription>Recent sync and indexing tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">
            {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Group tasks by type and status
  // Get unique task types from actual data
  const uniqueTypes = [...new Set(tasks.map((t) => t.task_type))];

  // If no unique types, use defaults
  const taskTypes = uniqueTypes.length > 0 ? uniqueTypes : ['sync'];

  const chartData = taskTypes.map((type) => {
    const typeTasks = tasks.filter((t) => t.task_type === type);
    return {
      type: type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
      completed: typeTasks.filter((t) => t.status === 'completed').length,
      failed: typeTasks.filter((t) => t.status === 'failed').length,
      running: typeTasks.filter((t) => t.status === 'running' || t.status === 'pending').length,
    };
  });

  const hasData = chartData.some((d) => d.completed > 0 || d.failed > 0 || d.running > 0);

  if (!hasData) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-chart-2/5">
        <CardHeader>
          <CardTitle>Task Activity</CardTitle>
          <CardDescription>Recent sync and indexing tasks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">
            No tasks yet. Trigger a sync to get started.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-chart-2/5">
      <CardHeader>
        <CardTitle>Task Activity</CardTitle>
        <CardDescription>
          {tasks.length} total tasks
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[200px] w-full">
          <BarChart data={chartData} layout="vertical">
            <XAxis type="number" hide />
            <YAxis
              dataKey="type"
              type="category"
              width={100}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar
              dataKey="completed"
              stackId="a"
              fill="var(--color-completed)"
              radius={[0, 0, 0, 0]}
            />
            <Bar
              dataKey="failed"
              stackId="a"
              fill="var(--color-failed)"
              radius={[0, 0, 0, 0]}
            />
            <Bar
              dataKey="running"
              stackId="a"
              fill="var(--color-running)"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ChartContainer>
        <div className="flex justify-center gap-6 mt-4">
          {Object.entries(chartConfig).map(([key, config]) => (
            <div key={key} className="flex items-center gap-1.5 text-xs">
              <div
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: config.color }}
              />
              <span className="text-muted-foreground">{config.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

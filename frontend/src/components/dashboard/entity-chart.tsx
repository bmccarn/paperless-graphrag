'use client';

import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Skeleton } from '@/components/ui/skeleton';
import { getGraphOverview } from '@/lib/api';
import type { GraphOverview } from '@/types';

const COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
  'hsl(217, 91%, 60%)',
  'hsl(280, 65%, 60%)',
  'hsl(142, 71%, 45%)',
];

export function EntityChart() {
  const [data, setData] = useState<GraphOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const overview = await getGraphOverview();
        setData(overview);
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
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
        <CardHeader>
          <CardTitle>Entity Types</CardTitle>
          <CardDescription>Distribution of entities in the knowledge graph</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[200px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.entity_types.length === 0) {
    return (
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
        <CardHeader>
          <CardTitle>Entity Types</CardTitle>
          <CardDescription>Distribution of entities in the knowledge graph</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">
            {error || 'No entity data available. Run a sync to build the graph.'}
          </div>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.entity_types.map((item, index) => ({
    name: item.type,
    value: item.count,
    fill: COLORS[index % COLORS.length],
  }));

  const chartConfig: ChartConfig = data.entity_types.reduce((acc, item, index) => {
    acc[item.type] = {
      label: item.type.charAt(0).toUpperCase() + item.type.slice(1),
      color: COLORS[index % COLORS.length],
    };
    return acc;
  }, {} as ChartConfig);

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
      <CardHeader>
        <CardTitle>Entity Types</CardTitle>
        <CardDescription>
          {data.entity_count.toLocaleString()} entities across {data.entity_types.length} types
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[200px] w-full">
          <PieChart>
            <ChartTooltip content={<ChartTooltipContent />} />
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={2}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className="flex flex-wrap justify-center gap-3 mt-4">
          {chartData.slice(0, 6).map((item, index) => (
            <div key={item.name} className="flex items-center gap-1.5 text-xs">
              <div
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: item.fill }}
              />
              <span className="text-muted-foreground capitalize">{item.name}</span>
              <span className="font-medium">{item.value}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

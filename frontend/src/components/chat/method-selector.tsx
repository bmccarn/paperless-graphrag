'use client';

import { Info, Sparkles, Globe, Zap, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/lib/stores';
import type { QueryMethod } from '@/types';

const methods: {
  id: QueryMethod;
  name: string;
  icon: React.ElementType;
  description: string;
  bestFor: string;
  speed: string;
  cost: string;
}[] = [
  {
    id: 'local',
    name: 'Local',
    icon: Search,
    description: 'Finds relevant entities in the graph and pulls their relationships and source text. Recommended as the default for most questions.',
    bestFor: 'Specific questions about people, dates, documents, or their connections.',
    speed: '5-15 seconds',
    cost: 'Low',
  },
  {
    id: 'global',
    name: 'Global',
    icon: Globe,
    description: 'Uses community-level summaries to answer broad questions. Requires community reports to be built during indexing.',
    bestFor: 'High-level summaries, themes across documents, "what do my documents say about X".',
    speed: '15-30 seconds',
    cost: 'Medium',
  },
  {
    id: 'drift',
    name: 'Drift',
    icon: Sparkles,
    description: 'Iteratively explores the graph following connections. Most thorough but slowest. Use when local answers feel incomplete.',
    bestFor: 'Complex multi-hop questions needing deep reasoning across many documents.',
    speed: '1-3 minutes',
    cost: 'High (5-10x local)',
  },
  {
    id: 'basic',
    name: 'Basic',
    icon: Zap,
    description: 'Pure vector similarity search without graph traversal. Fastest option with minimal processing.',
    bestFor: 'Quick keyword lookups when you know roughly what you are looking for.',
    speed: '2-5 seconds',
    cost: 'Lowest',
  },
];

export function MethodSelector() {
  const { selectedMethod, setMethod } = useChatStore();

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex items-center gap-1 p-1 bg-muted rounded-lg">
        {methods.map((method) => {
          const Icon = method.icon;
          const isSelected = selectedMethod === method.id;

          return (
            <Tooltip key={method.id}>
              <TooltipTrigger asChild>
                <Button
                  variant={isSelected ? 'default' : 'ghost'}
                  size="sm"
                  className={cn(
                    'h-8 px-3 gap-1.5',
                    isSelected && 'shadow-sm'
                  )}
                  onClick={() => setMethod(method.id)}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="text-xs font-medium">{method.name}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-sm">
                <div className="space-y-2">
                  <p className="font-medium">{method.name} Search</p>
                  <p className="text-xs text-muted-foreground">{method.description}</p>
                  <p className="text-xs">
                    <span className="font-medium">Best for:</span> {method.bestFor}
                  </p>
                  <div className="flex gap-4 text-xs pt-1 border-t border-border/50">
                    <span><span className="font-medium">Speed:</span> {method.speed}</span>
                    <span><span className="font-medium">Cost:</span> {method.cost}</span>
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 ml-1">
              <Info className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-sm">
            <div className="space-y-2">
              <p className="font-medium">Search Methods</p>
              <p className="text-xs text-muted-foreground">
                GraphRAG offers different search strategies. <strong>Local</strong> is best for specific entity questions.
                <strong> Global</strong> provides broad summaries. <strong>Drift</strong> combines both approaches.
                <strong> Basic</strong> is fastest for simple lookups.
              </p>
            </div>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}

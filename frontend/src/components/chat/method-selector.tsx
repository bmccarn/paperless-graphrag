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
}[] = [
  {
    id: 'local',
    name: 'Local',
    icon: Search,
    description: 'Searches specific entities and their relationships in the knowledge graph.',
    bestFor: 'Specific questions about people, places, organizations, or their connections.',
  },
  {
    id: 'global',
    name: 'Global',
    icon: Globe,
    description: 'Analyzes community summaries to provide broad overviews and themes.',
    bestFor: 'Summarization, themes, high-level insights across all documents.',
  },
  {
    id: 'drift',
    name: 'Drift',
    icon: Sparkles,
    description: 'Hybrid approach that combines local precision with global context.',
    bestFor: 'Complex questions needing both specific details and broader context.',
  },
  {
    id: 'basic',
    name: 'Basic',
    icon: Zap,
    description: 'Simple vector similarity search without graph traversal.',
    bestFor: 'Quick lookups when you need speed over depth.',
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
              <TooltipContent side="bottom" className="max-w-xs">
                <div className="space-y-1">
                  <p className="font-medium">{method.name} Search</p>
                  <p className="text-xs text-muted-foreground">{method.description}</p>
                  <p className="text-xs">
                    <span className="font-medium">Best for:</span> {method.bestFor}
                  </p>
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

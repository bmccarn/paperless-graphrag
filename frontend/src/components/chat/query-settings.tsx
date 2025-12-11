'use client';

import { Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { useChatStore } from '@/lib/stores';
import type { QueryMethod } from '@/types';

const methodDescriptions: Record<QueryMethod, string> = {
  local: 'Best for specific questions about entities and relationships. Fast and focused.',
  global: 'Best for broad summarization questions. Uses community reports.',
  drift: 'Experimental hybrid approach combining local and global search.',
  basic: 'Simple vector search. Fastest but less context-aware.',
};

export function QuerySettings() {
  const { selectedMethod, communityLevel, setMethod, setCommunityLevel } =
    useChatStore();

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="icon">
          <Settings2 className="h-4 w-4" />
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Query Settings</SheetTitle>
          <SheetDescription>
            Configure how GraphRAG processes your questions
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          <div className="space-y-3">
            <Label>Query Method</Label>
            <Select
              value={selectedMethod}
              onValueChange={(value) => setMethod(value as QueryMethod)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="local">Local Search</SelectItem>
                <SelectItem value="global">Global Search</SelectItem>
                <SelectItem value="drift">Drift Search</SelectItem>
                <SelectItem value="basic">Basic Search</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              {methodDescriptions[selectedMethod]}
            </p>
          </div>

          {selectedMethod === 'local' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Community Level</Label>
                <span className="text-sm text-muted-foreground">
                  {communityLevel}
                </span>
              </div>
              <Slider
                value={[communityLevel]}
                onValueChange={([value]) => setCommunityLevel(value)}
                min={0}
                max={10}
                step={1}
              />
              <p className="text-sm text-muted-foreground">
                Lower levels are more specific, higher levels are more general.
              </p>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

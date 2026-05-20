'use client';

import { useEffect, useState } from 'react';
import { Loader2, RotateCcw, Settings2 } from 'lucide-react';
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
import { getAvailableModels, getCurrentModels, restartBackend, updateSettings } from '@/lib/api';
import { toast } from 'sonner';
import type { AvailableModel, QueryMethod } from '@/types';

const methodDescriptions: Record<QueryMethod, string> = {
  local: 'Best for specific questions about entities and relationships. Fast and focused.',
  global: 'Best for broad summarization questions. Uses community reports.',
  drift: 'Experimental hybrid approach combining local and global search.',
  basic: 'Simple vector search. Fastest but less context-aware.',
};

function getModelLabel(model: AvailableModel) {
  return model.provider_display_name
    ? `${model.provider_display_name} · ${model.display_name}`
    : model.display_name;
}

export function QuerySettings() {
  const { selectedMethod, communityLevel, setMethod, setCommunityLevel } =
    useChatStore();
  const [chatModels, setChatModels] = useState<AvailableModel[]>([]);
  const [queryModel, setQueryModel] = useState('');
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isSavingModel, setIsSavingModel] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);
  const [pendingRestart, setPendingRestart] = useState(false);

  useEffect(() => {
    let mounted = true;

    const loadModels = async () => {
      setIsLoadingModels(true);
      try {
        const [catalog, current] = await Promise.all([
          getAvailableModels('chat'),
          getCurrentModels(),
        ]);
        if (!mounted) return;
        setChatModels(catalog.models);
        setQueryModel(current.query_model);
      } catch (error) {
        console.warn('Failed to load LiteLLM models:', error);
      } finally {
        if (mounted) {
          setIsLoadingModels(false);
        }
      }
    };

    loadModels();

    return () => {
      mounted = false;
    };
  }, []);

  const handleModelChange = async (value: string) => {
    const previousModel = queryModel;
    setQueryModel(value);
    setIsSavingModel(true);

    try {
      const result = await updateSettings({ query_model: value });
      if (!result.success) {
        throw new Error(Object.values(result.errors).join(', ') || 'Failed to save query model');
      }
      setPendingRestart(true);
      toast.success('Query model saved', {
        description: 'Restart the backend before the next GraphRAG query.',
      });
    } catch (error) {
      setQueryModel(previousModel);
      toast.error('Failed to save query model', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSavingModel(false);
    }
  };

  const handleRestart = async () => {
    setIsRestarting(true);
    try {
      await restartBackend();
      toast.success('Restart initiated');
      setPendingRestart(false);
      setTimeout(() => {
        setIsRestarting(false);
      }, 3000);
    } catch (error) {
      toast.error('Failed to restart backend', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
      setIsRestarting(false);
    }
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="icon">
          <Settings2 className="h-4 w-4" />
        </Button>
      </SheetTrigger>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Query Settings</SheetTitle>
          <SheetDescription>
            Configure how GraphRAG processes your questions
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          <div className="space-y-3">
            <Label>Query Model</Label>
            <Select
              value={queryModel || undefined}
              onValueChange={handleModelChange}
              disabled={isLoadingModels || isSavingModel || isRestarting}
            >
              <SelectTrigger>
                <SelectValue placeholder={isLoadingModels ? 'Loading models...' : 'Select model'} />
              </SelectTrigger>
              <SelectContent>
                {queryModel && !chatModels.some((model) => model.id === queryModel) && (
                  <SelectItem value={queryModel}>
                    <div className="flex flex-col">
                      <span>{queryModel}</span>
                      <span className="text-xs text-muted-foreground">Current custom value</span>
                    </div>
                  </SelectItem>
                )}
                {chatModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <div className="flex flex-col">
                      <span>{getModelLabel(model)}</span>
                      <span className="text-xs text-muted-foreground">{model.id}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isSavingModel && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Saving model
              </div>
            )}
            {pendingRestart && (
              <Button
                onClick={handleRestart}
                disabled={isRestarting}
                variant="secondary"
                size="sm"
              >
                {isRestarting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4 mr-2" />
                )}
                Apply & Restart
              </Button>
            )}
          </div>

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

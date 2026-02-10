'use client';

import { useState } from 'react';
import { RefreshCw, RefreshCcw, Loader2, Zap } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { triggerSync } from '@/lib/api';
import { toast } from 'sonner';

export function SyncControls() {
  const [isSyncing, setIsSyncing] = useState(false);
  const [fullSyncOpen, setFullSyncOpen] = useState(false);
  const [reindexOpen, setReindexOpen] = useState(false);

  const handleSync = async (full: boolean = false, reindex: boolean = false) => {
    setIsSyncing(true);
    setFullSyncOpen(false);
    setReindexOpen(false);

    try {
      const result = await triggerSync(full, reindex);
      const label = reindex ? 'Force re-index started' : full ? 'Full sync started' : 'Incremental sync started';
      toast.success(label, {
        description: `Task ID: ${result.task_id}`,
      });
    } catch (error) {
      toast.error('Failed to start sync', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-primary/5">
      <CardHeader>
        <CardTitle>Sync Controls</CardTitle>
        <CardDescription>
          Synchronize documents from Paperless-ngx and update the GraphRAG index
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          <Button
            className="w-full h-12 shadow-md hover:shadow-lg transition-all"
            onClick={() => handleSync(false)}
            disabled={isSyncing}
          >
            {isSyncing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Incremental Sync
          </Button>
          <p className="text-xs text-muted-foreground text-center">
            Only sync changed documents
          </p>

          <Dialog open={fullSyncOpen} onOpenChange={setFullSyncOpen}>
            <DialogTrigger asChild>
              <Button
                className="w-full h-12 shadow-sm"
                variant="secondary"
                disabled={isSyncing}
              >
                <RefreshCcw className="h-4 w-4 mr-2" />
                Full Sync
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirm Full Sync</DialogTitle>
                <DialogDescription>
                  A full sync will re-process all documents from Paperless-ngx.
                  This may take a long time and use significant API credits.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setFullSyncOpen(false)}
                >
                  Cancel
                </Button>
                <Button onClick={() => handleSync(true)}>
                  Start Full Sync
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <p className="text-xs text-muted-foreground text-center">
            Re-sync all documents (takes longer)
          </p>

          <div className="border-t pt-3 mt-3">
            <Dialog open={reindexOpen} onOpenChange={setReindexOpen}>
              <DialogTrigger asChild>
                <Button
                  className="w-full h-12 shadow-sm"
                  variant="outline"
                  disabled={isSyncing}
                >
                  <Zap className="h-4 w-4 mr-2" />
                  Force Re-index
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Confirm Force Re-index</DialogTitle>
                  <DialogDescription>
                    This will skip document sync and run a full GraphRAG index
                    from scratch. Useful after changing the extraction prompt or
                    GraphRAG settings. This may take a long time and use
                    significant API credits.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setReindexOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button onClick={() => handleSync(false, true)}>
                    Start Re-index
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <p className="text-xs text-muted-foreground text-center mt-3">
              Rebuild index without re-syncing documents
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

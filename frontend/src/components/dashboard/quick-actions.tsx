'use client';

import { useState } from 'react';
import Link from 'next/link';
import { RefreshCw, MessageSquare, Network, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { triggerSync } from '@/lib/api';
import { toast } from 'sonner';

export function QuickActions() {
  const [isSyncing, setIsSyncing] = useState(false);

  const handleSync = async (full: boolean = false) => {
    setIsSyncing(true);
    try {
      const result = await triggerSync(full);
      toast.success('Sync started', {
        description: `Task ID: ${result.task_id}. Check Operations for progress.`,
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
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button
          className="w-full justify-start h-12 shadow-sm hover:shadow-md transition-all"
          variant="outline"
          onClick={() => handleSync(false)}
          disabled={isSyncing}
        >
          {isSyncing ? (
            <Loader2 className="h-4 w-4 mr-3 animate-spin" />
          ) : (
            <div className="p-1.5 rounded-md bg-primary/10 mr-3">
              <RefreshCw className="h-4 w-4 text-primary" />
            </div>
          )}
          Sync Documents
        </Button>

        <Button className="w-full justify-start h-12 shadow-sm hover:shadow-md transition-all" variant="outline" asChild>
          <Link href="/chat">
            <div className="p-1.5 rounded-md bg-blue-500/10 mr-3">
              <MessageSquare className="h-4 w-4 text-blue-500" />
            </div>
            Ask a Question
          </Link>
        </Button>

        <Button className="w-full justify-start h-12 shadow-sm hover:shadow-md transition-all" variant="outline" asChild>
          <Link href="/graph">
            <div className="p-1.5 rounded-md bg-purple-500/10 mr-3">
              <Network className="h-4 w-4 text-purple-500" />
            </div>
            Explore Graph
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

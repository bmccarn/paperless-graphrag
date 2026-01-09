'use client';

import { useEffect, useState } from 'react';
import { useAIStore } from '@/lib/stores/ai-store';
import { DocumentBrowser, ProcessingControls, SuggestionReview, PreferencesManager } from '@/components/ai';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  FileText,
  Sparkles,
  CheckSquare,
  Loader2,
  Activity,
  Clock,
  AlertCircle,
  Settings,
} from 'lucide-react';

export default function AIPage() {
  const {
    stats,
    fetchStats,
    fetchTaxonomy,
    selectedDocumentIds,
    pendingSuggestions,
    activeJob,
  } = useAIStore();

  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const init = async () => {
      await Promise.all([fetchStats(), fetchTaxonomy()]);
      setIsInitializing(false);
    };
    init();
  }, [fetchStats, fetchTaxonomy]);

  if (isInitializing) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin mr-3" />
        <span className="text-lg">Loading AI Sync...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Sparkles className="h-8 w-8" />
            AI Document Sync
          </h1>
          <p className="text-muted-foreground mt-1">
            Use AI to analyze documents and suggest titles, tags, and document types
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Selected</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedDocumentIds.size}</div>
            <p className="text-xs text-muted-foreground">documents for processing</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.pendingSuggestions ?? pendingSuggestions.length}
            </div>
            <p className="text-xs text-muted-foreground">suggestions awaiting review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processed</CardTitle>
            <CheckSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.processedDocuments ?? 0}</div>
            <p className="text-xs text-muted-foreground">documents analyzed by AI</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {activeJob && ['pending', 'processing'].includes(activeJob.status) ? 1 : 0}
            </div>
            <p className="text-xs text-muted-foreground">currently running</p>
          </CardContent>
        </Card>
      </div>

      {/* Active Job Alert */}
      {activeJob && ['pending', 'processing'].includes(activeJob.status) && (
        <Card className="border-blue-500 bg-blue-50 dark:bg-blue-950">
          <CardContent className="flex items-center gap-4 py-4">
            <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
            <div className="flex-1">
              <div className="font-medium text-blue-900 dark:text-blue-100">
                Processing in Progress
              </div>
              <div className="text-sm text-blue-700 dark:text-blue-300">
                {activeJob.progress_current} of {activeJob.progress_total} documents
                {activeJob.current_document_title && (
                  <> - Currently: {activeJob.current_document_title}</>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completed Job with Pending Review */}
      {activeJob?.status === 'completed' && pendingSuggestions.length > 0 && (
        <Card className="border-green-500 bg-green-50 dark:bg-green-950">
          <CardContent className="flex items-center gap-4 py-4">
            <CheckSquare className="h-5 w-5 text-green-600" />
            <div className="flex-1">
              <div className="font-medium text-green-900 dark:text-green-100">
                Processing Complete
              </div>
              <div className="text-sm text-green-700 dark:text-green-300">
                {pendingSuggestions.length} documents ready for review in the Review tab
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Tabs */}
      <Tabs defaultValue="browse" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="browse" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Browse
            {selectedDocumentIds.size > 0 && (
              <span className="ml-1 rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
                {selectedDocumentIds.size}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="process" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Process
            {activeJob && ['pending', 'processing'].includes(activeJob.status) && (
              <Loader2 className="ml-1 h-3 w-3 animate-spin" />
            )}
          </TabsTrigger>
          <TabsTrigger value="review" className="flex items-center gap-2">
            <CheckSquare className="h-4 w-4" />
            Review
            {pendingSuggestions.length > 0 && (
              <span className="ml-1 rounded-full bg-amber-500 px-2 py-0.5 text-xs text-white">
                {pendingSuggestions.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Preferences
          </TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Document Browser</CardTitle>
              <p className="text-sm text-muted-foreground">
                Select documents and click &quot;Process Selected&quot; to analyze them with AI.
                After processing, review suggestions in the Review tab.
              </p>
            </CardHeader>
            <CardContent>
              <DocumentBrowser />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="process" className="space-y-4">
          <ProcessingControls />
        </TabsContent>

        <TabsContent value="review" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Review Suggestions</CardTitle>
              <p className="text-sm text-muted-foreground">
                Review AI-generated suggestions before applying them to Paperless. You can approve,
                modify, or reject suggestions for each document.
              </p>
            </CardHeader>
            <CardContent>
              <SuggestionReview />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>AI Preferences</CardTitle>
              <p className="text-sm text-muted-foreground">
                Customize how the AI tags your documents. Define what tags mean, review learned
                rules, and configure consistency settings.
              </p>
            </CardHeader>
            <CardContent>
              <PreferencesManager />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useAIStore } from '@/lib/stores/ai-store';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Loader2, Play, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import type { ProcessingScope } from '@/lib/api/ai';

export function ProcessingControls() {
  const {
    selectedDocumentIds,
    processingOptions,
    activeJob,
    setProcessingOptions,
    startProcessing,
  } = useAIStore();

  const [scope, setScope] = useState<ProcessingScope>('selected');
  const [isStarting, setIsStarting] = useState(false);
  const [showAutoApplyWarning, setShowAutoApplyWarning] = useState(false);

  const isProcessing = activeJob?.status === 'processing' || activeJob?.status === 'pending';
  const canStart =
    !isProcessing &&
    (scope !== 'selected' || selectedDocumentIds.size > 0) &&
    (processingOptions.generateTitles ||
      processingOptions.suggestTags ||
      processingOptions.suggestDocumentType);

  const handleStartProcessing = async () => {
    if (processingOptions.autoApply) {
      setShowAutoApplyWarning(true);
      return;
    }
    await doStartProcessing();
  };

  const doStartProcessing = async () => {
    setIsStarting(true);
    try {
      await startProcessing(scope);
    } catch (error) {
      console.error('Failed to start processing:', error);
    } finally {
      setIsStarting(false);
      setShowAutoApplyWarning(false);
    }
  };

  const progress =
    activeJob && activeJob.progress_total > 0
      ? (activeJob.progress_current / activeJob.progress_total) * 100
      : 0;

  return (
    <div className="space-y-6">
      {/* Processing Options */}
      <Card>
        <CardHeader>
          <CardTitle>Processing Options</CardTitle>
          <CardDescription>
            Configure what the AI should analyze for each document
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Scope Selection */}
          <div className="space-y-2">
            <Label>Documents to Process</Label>
            <Select value={scope} onValueChange={(v) => setScope(v as ProcessingScope)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="selected">
                  Selected Documents ({selectedDocumentIds.size})
                </SelectItem>
                <SelectItem value="unprocessed">Unprocessed Documents Only</SelectItem>
                <SelectItem value="all">All Documents</SelectItem>
              </SelectContent>
            </Select>
            {scope === 'selected' && selectedDocumentIds.size === 0 && (
              <p className="text-sm text-amber-600">
                Select documents in the Browse tab first
              </p>
            )}
          </div>

          {/* Analysis Options */}
          <div className="space-y-3">
            <Label>What to Analyze</Label>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="generate-titles"
                checked={processingOptions.generateTitles}
                onCheckedChange={(checked) =>
                  setProcessingOptions({ generateTitles: !!checked })
                }
              />
              <Label htmlFor="generate-titles" className="font-normal cursor-pointer">
                Generate improved titles
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="suggest-tags"
                checked={processingOptions.suggestTags}
                onCheckedChange={(checked) =>
                  setProcessingOptions({ suggestTags: !!checked })
                }
              />
              <Label htmlFor="suggest-tags" className="font-normal cursor-pointer">
                Suggest tags
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="suggest-type"
                checked={processingOptions.suggestDocumentType}
                onCheckedChange={(checked) =>
                  setProcessingOptions({ suggestDocumentType: !!checked })
                }
              />
              <Label htmlFor="suggest-type" className="font-normal cursor-pointer">
                Suggest document type
              </Label>
            </div>
          </div>

          {/* Auto-Apply Option */}
          <div className="pt-4 border-t">
            <div className="flex items-start space-x-2">
              <Checkbox
                id="auto-apply"
                checked={processingOptions.autoApply}
                onCheckedChange={(checked) =>
                  setProcessingOptions({ autoApply: !!checked })
                }
              />
              <div className="space-y-1">
                <Label htmlFor="auto-apply" className="font-normal cursor-pointer">
                  Auto-apply suggestions (skip review)
                </Label>
                <p className="text-xs text-muted-foreground">
                  Changes will be applied directly to Paperless without review
                </p>
              </div>
            </div>
          </div>

          {/* Start Button */}
          <div className="pt-4">
            <Button
              onClick={handleStartProcessing}
              disabled={!canStart || isStarting}
              className="w-full"
              size="lg"
            >
              {isStarting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start AI Processing
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Active Job Status */}
      {activeJob && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {activeJob.status === 'processing' && (
                <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              )}
              {activeJob.status === 'completed' && (
                <CheckCircle className="h-5 w-5 text-green-500" />
              )}
              {activeJob.status === 'failed' && (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
              {activeJob.status === 'pending' && (
                <Loader2 className="h-5 w-5 animate-spin text-yellow-500" />
              )}
              Processing Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>
                  {activeJob.progress_current} / {activeJob.progress_total}
                </span>
              </div>
              <Progress value={progress} />
            </div>

            {activeJob.current_document_title && (
              <div className="text-sm">
                <span className="text-muted-foreground">Currently processing: </span>
                <span className="font-medium">{activeJob.current_document_title}</span>
              </div>
            )}

            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Status:</span>
              <span
                className={`font-medium capitalize ${
                  activeJob.status === 'completed'
                    ? 'text-green-600'
                    : activeJob.status === 'failed'
                    ? 'text-red-600'
                    : 'text-blue-600'
                }`}
              >
                {activeJob.status}
              </span>
            </div>

            {activeJob.errors.length > 0 && (
              <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg">
                <div className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">
                  Errors ({activeJob.errors.length})
                </div>
                <ul className="text-xs text-red-600 dark:text-red-400 space-y-1">
                  {activeJob.errors.slice(0, 5).map((error, i) => (
                    <li key={i}>{error}</li>
                  ))}
                  {activeJob.errors.length > 5 && (
                    <li>...and {activeJob.errors.length - 5} more</li>
                  )}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Auto-Apply Warning Dialog */}
      <AlertDialog open={showAutoApplyWarning} onOpenChange={setShowAutoApplyWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Auto-Apply Enabled
            </AlertDialogTitle>
            <AlertDialogDescription>
              You have auto-apply enabled. This will immediately apply all AI suggestions
              to your documents in Paperless without giving you a chance to review them.
              <br />
              <br />
              Are you sure you want to continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={doStartProcessing}>
              Yes, Auto-Apply
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useAIStore } from '@/lib/stores/ai-store';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Label } from '@/components/ui/label';
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  Search,
  X,
  Sparkles,
  Tag,
  FileType,
  AlertCircle,
  Play,
  Settings2,
} from 'lucide-react';

export function DocumentBrowser() {
  const {
    documents,
    documentsLoading,
    documentsError,
    totalDocuments,
    currentPage,
    totalPages,
    filters,
    selectedDocumentIds,
    fetchDocuments,
    setPage,
    setFilters,
    clearFilters,
    toggleDocument,
    selectAll,
    clearSelection,
    selectUnprocessed,
    startProcessing,
    processingOptions,
    setProcessingOptions,
    activeJob,
  } = useAIStore();

  const [isStarting, setIsStarting] = useState(false);
  const [showProcessOptions, setShowProcessOptions] = useState(false);

  const isProcessing = activeJob?.status === 'processing' || activeJob?.status === 'pending';

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleQuickProcess = async () => {
    if (selectedDocumentIds.size === 0 || isProcessing) return;
    setIsStarting(true);
    try {
      await startProcessing('selected');
      setShowProcessOptions(false);
    } catch (error) {
      console.error('Failed to start processing:', error);
    } finally {
      setIsStarting(false);
    }
  };

  const allSelected =
    documents.length > 0 && documents.every((d) => selectedDocumentIds.has(d.id));
  const someSelected = documents.some((d) => selectedDocumentIds.has(d.id));

  const handleSelectAll = () => {
    if (allSelected) {
      clearSelection();
    } else {
      selectAll();
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            className="pl-10"
            value={filters.search || ''}
            onChange={(e) => setFilters({ search: e.target.value || undefined })}
          />
        </div>

        <Select
          value={
            filters.ai_processed === true
              ? 'processed'
              : filters.ai_processed === false
              ? 'unprocessed'
              : 'all'
          }
          onValueChange={(value) =>
            setFilters({
              ai_processed:
                value === 'processed' ? true : value === 'unprocessed' ? false : undefined,
            })
          }
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="AI Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Documents</SelectItem>
            <SelectItem value="unprocessed">Not Processed</SelectItem>
            <SelectItem value="processed">AI Processed</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={
            filters.has_tags === true
              ? 'has-tags'
              : filters.has_tags === false
              ? 'no-tags'
              : 'any-tags'
          }
          onValueChange={(value) =>
            setFilters({
              has_tags:
                value === 'has-tags' ? true : value === 'no-tags' ? false : undefined,
            })
          }
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Tags" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any-tags">Any Tags</SelectItem>
            <SelectItem value="has-tags">Has Tags</SelectItem>
            <SelectItem value="no-tags">No Tags</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={
            filters.has_document_type === true
              ? 'has-type'
              : filters.has_document_type === false
              ? 'no-type'
              : 'any-type'
          }
          onValueChange={(value) =>
            setFilters({
              has_document_type:
                value === 'has-type' ? true : value === 'no-type' ? false : undefined,
            })
          }
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Document Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any-type">Any Type</SelectItem>
            <SelectItem value="has-type">Has Type</SelectItem>
            <SelectItem value="no-type">No Type</SelectItem>
          </SelectContent>
        </Select>

        {(filters.search ||
          filters.ai_processed !== undefined ||
          filters.has_tags !== undefined ||
          filters.has_document_type !== undefined) && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {/* Selection Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">
            {selectedDocumentIds.size} of {totalDocuments} selected
          </span>
          <Button variant="outline" size="sm" onClick={selectUnprocessed}>
            Select Unprocessed
          </Button>
          <Button variant="outline" size="sm" onClick={clearSelection}>
            Clear Selection
          </Button>
        </div>

        {/* Quick Process Button */}
        {selectedDocumentIds.size > 0 && (
          <div className="flex items-center gap-2">
            <Popover open={showProcessOptions} onOpenChange={setShowProcessOptions}>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="sm" className="h-9 px-2">
                  <Settings2 className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-64" align="end">
                <div className="space-y-3">
                  <div className="font-medium text-sm">Processing Options</div>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="quick-titles"
                        checked={processingOptions.generateTitles}
                        onCheckedChange={(checked) =>
                          setProcessingOptions({ generateTitles: !!checked })
                        }
                      />
                      <Label htmlFor="quick-titles" className="text-sm font-normal cursor-pointer">
                        Generate titles
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="quick-tags"
                        checked={processingOptions.suggestTags}
                        onCheckedChange={(checked) =>
                          setProcessingOptions({ suggestTags: !!checked })
                        }
                      />
                      <Label htmlFor="quick-tags" className="text-sm font-normal cursor-pointer">
                        Suggest tags
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="quick-type"
                        checked={processingOptions.suggestDocumentType}
                        onCheckedChange={(checked) =>
                          setProcessingOptions({ suggestDocumentType: !!checked })
                        }
                      />
                      <Label htmlFor="quick-type" className="text-sm font-normal cursor-pointer">
                        Suggest document type
                      </Label>
                    </div>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
            <Button
              onClick={handleQuickProcess}
              disabled={isStarting || isProcessing || !(processingOptions.generateTitles || processingOptions.suggestTags || processingOptions.suggestDocumentType)}
              size="sm"
            >
              {isStarting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Process {selectedDocumentIds.size} Selected
                </>
              )}
            </Button>
          </div>
        )}
      </div>

      {/* Error State */}
      {documentsError && (
        <div className="flex items-center gap-2 p-4 bg-destructive/10 text-destructive rounded-lg">
          <AlertCircle className="h-4 w-4" />
          {documentsError}
        </div>
      )}

      {/* Loading State */}
      {documentsLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          Loading documents...
        </div>
      )}

      {/* Document Table */}
      {!documentsLoading && !documentsError && (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={handleSelectAll}
                    aria-label="Select all"
                  />
                </TableHead>
                <TableHead>Title</TableHead>
                <TableHead className="w-[120px]">Type</TableHead>
                <TableHead className="w-[200px]">Tags</TableHead>
                <TableHead className="w-[100px]">Created</TableHead>
                <TableHead className="w-[80px]">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No documents found
                  </TableCell>
                </TableRow>
              ) : (
                documents.map((doc) => (
                  <TableRow
                    key={doc.id}
                    className={selectedDocumentIds.has(doc.id) ? 'bg-muted/50' : ''}
                  >
                    <TableCell>
                      <Checkbox
                        checked={selectedDocumentIds.has(doc.id)}
                        onCheckedChange={() => toggleDocument(doc.id)}
                        aria-label={`Select ${doc.title}`}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate max-w-[300px]" title={doc.title}>
                          {doc.title}
                        </span>
                        {doc.has_pending_suggestions && (
                          <Badge variant="secondary" className="text-xs">
                            <Sparkles className="h-3 w-3 mr-1" />
                            Pending
                          </Badge>
                        )}
                      </div>
                      {doc.correspondent && (
                        <div className="text-xs text-muted-foreground">{doc.correspondent}</div>
                      )}
                    </TableCell>
                    <TableCell>
                      {doc.document_type ? (
                        <Badge variant="outline" className="text-xs">
                          <FileType className="h-3 w-3 mr-1" />
                          {doc.document_type}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">None</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {doc.tags.length > 0 ? (
                          doc.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              <Tag className="h-3 w-3 mr-1" />
                              {tag}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-muted-foreground text-xs">No tags</span>
                        )}
                        {doc.tags.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{doc.tags.length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(doc.created)}
                    </TableCell>
                    <TableCell>
                      {doc.ai_processed_at ? (
                        <Badge variant="default" className="text-xs bg-green-600">
                          <Sparkles className="h-3 w-3 mr-1" />
                          Done
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          New
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages} ({totalDocuments} documents)
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useAIStore } from '@/lib/stores/ai-store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Loader2,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Tag,
  FileType,
  Type,
  AlertCircle,
  Plus,
  MessageSquare,
  ArrowRight,
  RefreshCw,
  Undo2,
} from 'lucide-react';
import type { DocumentSuggestion, TagSuggestion, Tag as TagType } from '@/lib/api/ai';

function SuggestionCard({ suggestion }: { suggestion: DocumentSuggestion }) {
  const {
    approveSuggestion,
    rejectSuggestion,
    applySuggestion,
    markForReprocess,
    resetSuggestion,
    tags: availableTags,
    createTag,
  } = useAIStore();

  const [isOpen, setIsOpen] = useState(true);
  const [isApplying, setIsApplying] = useState(false);
  const [modifiedTitle, setModifiedTitle] = useState(suggestion.suggested_title || '');
  const [selectedTagIndices, setSelectedTagIndices] = useState<number[]>(
    suggestion.suggested_tags.map((_, i) => i)
  );
  const [additionalTagIds, setAdditionalTagIds] = useState<number[]>(
    suggestion.additional_tag_ids || []
  );
  const [rejectionNotes, setRejectionNotes] = useState(suggestion.rejection_notes || '');
  const [tagSelectorOpen, setTagSelectorOpen] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [isCreatingTag, setIsCreatingTag] = useState(false);

  const hasPendingTitle =
    suggestion.title_status === 'pending' && suggestion.suggested_title;
  const hasPendingTags =
    suggestion.tags_status === 'pending' && suggestion.suggested_tags.length > 0;
  const hasPendingType =
    suggestion.doc_type_status === 'pending' && suggestion.suggested_document_type;

  const hasApprovedSuggestions =
    suggestion.title_status === 'approved' ||
    suggestion.tags_status === 'approved' ||
    suggestion.doc_type_status === 'approved';

  // Filter out tags that are already suggested or on the document
  const suggestedTagNames = suggestion.suggested_tags.map((t) => t.tag_name.toLowerCase());
  const currentTagNames = suggestion.current_tags.map((t) => t.toLowerCase());
  const additionalTagNames = additionalTagIds
    .map((id) => availableTags.find((t) => t.id === id)?.name || '')
    .filter(Boolean);

  const availableTagsToAdd = availableTags.filter(
    (tag) =>
      !suggestedTagNames.includes(tag.name.toLowerCase()) &&
      !currentTagNames.includes(tag.name.toLowerCase()) &&
      !additionalTagIds.includes(tag.id)
  );

  // Filter tags based on search term, then limit to 20 for display
  const filteredTagsToAdd = availableTagsToAdd
    .filter((tag) =>
      newTagName.trim() === '' ||
      tag.name.toLowerCase().includes(newTagName.trim().toLowerCase())
    )
    .slice(0, 20);

  const toggleTag = (index: number) => {
    setSelectedTagIndices((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const addTag = (tagId: number) => {
    setAdditionalTagIds((prev) => [...prev, tagId]);
    setTagSelectorOpen(false);
  };

  const removeAdditionalTag = (tagId: number) => {
    setAdditionalTagIds((prev) => prev.filter((id) => id !== tagId));
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim() || isCreatingTag) return;

    setIsCreatingTag(true);
    try {
      const newTag = await createTag(newTagName.trim());
      setAdditionalTagIds((prev) => [...prev, newTag.id]);
      setNewTagName('');
      setTagSelectorOpen(false);
    } catch (error) {
      console.error('Failed to create tag:', error);
    } finally {
      setIsCreatingTag(false);
    }
  };

  const handleApproveTitle = async () => {
    await approveSuggestion(suggestion.document_id, {
      approve_title: true,
      modified_title: modifiedTitle !== suggestion.suggested_title ? modifiedTitle : null,
    });
  };

  const handleRejectTitle = async () => {
    await approveSuggestion(suggestion.document_id, { approve_title: false });
  };

  const handleApproveTags = async () => {
    await approveSuggestion(suggestion.document_id, {
      approve_tags: true,
      selected_tag_indices: selectedTagIndices,
      additional_tag_ids: additionalTagIds.length > 0 ? additionalTagIds : null,
      rejection_notes: rejectionNotes || null,
    });
  };

  const handleRejectTags = async () => {
    await approveSuggestion(suggestion.document_id, {
      approve_tags: false,
      rejection_notes: rejectionNotes || null,
    });
  };

  const handleApproveType = async () => {
    await approveSuggestion(suggestion.document_id, { approve_document_type: true });
  };

  const handleRejectType = async () => {
    await approveSuggestion(suggestion.document_id, { approve_document_type: false });
  };

  const handleApply = async () => {
    setIsApplying(true);
    try {
      await applySuggestion(suggestion.document_id);
    } finally {
      setIsApplying(false);
    }
  };

  const handleRejectAll = async () => {
    await rejectSuggestion(suggestion.document_id);
  };

  const handleReset = async () => {
    await resetSuggestion(suggestion.document_id);
  };

  // Compute what will be applied for the summary
  const selectedSuggestedTags = selectedTagIndices.map((i) => suggestion.suggested_tags[i]?.tag_name).filter(Boolean);
  const rejectedSuggestedTags = suggestion.suggested_tags
    .filter((_, i) => !selectedTagIndices.includes(i))
    .map((t) => t.tag_name);

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <CardTitle className="text-base">{suggestion.current_title}</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {hasPendingTitle && (
                  <Badge variant="secondary">
                    <Type className="h-3 w-3 mr-1" />
                    Title
                  </Badge>
                )}
                {hasPendingTags && (
                  <Badge variant="secondary">
                    <Tag className="h-3 w-3 mr-1" />
                    Tags
                  </Badge>
                )}
                {hasPendingType && (
                  <Badge variant="secondary">
                    <FileType className="h-3 w-3 mr-1" />
                    Type
                  </Badge>
                )}
                {hasApprovedSuggestions && (
                  <Badge variant="default" className="bg-green-600">
                    <Check className="h-3 w-3 mr-1" />
                    Ready
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-6 pt-0">
            {/* Title Suggestion */}
            {suggestion.suggested_title && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Type className="h-4 w-4" />
                    Title Suggestion
                  </Label>
                  <StatusBadge status={suggestion.title_status} />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-muted-foreground">Current</Label>
                    <div className="p-2 bg-muted rounded text-sm">
                      {suggestion.current_title}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Suggested</Label>
                    {suggestion.title_status === 'pending' ? (
                      <Input
                        value={modifiedTitle}
                        onChange={(e) => setModifiedTitle(e.target.value)}
                        className="text-sm"
                      />
                    ) : (
                      <div className="p-2 bg-muted rounded text-sm">
                        {suggestion.suggested_title}
                      </div>
                    )}
                  </div>
                </div>

                {suggestion.title_status === 'pending' && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="default" onClick={handleApproveTitle}>
                      <Check className="h-4 w-4 mr-1" />
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleRejectTitle}>
                      <X className="h-4 w-4 mr-1" />
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Tags Suggestion */}
            {suggestion.suggested_tags.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Tag Suggestions
                  </Label>
                  <StatusBadge status={suggestion.tags_status} />
                </div>

                <div>
                  <Label className="text-xs text-muted-foreground">Current Tags</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {suggestion.current_tags.length > 0 ? (
                      suggestion.current_tags.map((tag) => (
                        <Badge key={tag} variant="outline">
                          {tag}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">None</span>
                    )}
                  </div>
                </div>

                <div>
                  <Label className="text-xs text-muted-foreground">AI Suggested Tags</Label>
                  <div className="space-y-2 mt-1">
                    {suggestion.suggested_tags.map((tag, index) => (
                      <div key={index} className="flex items-center gap-2">
                        {suggestion.tags_status === 'pending' && (
                          <Checkbox
                            checked={selectedTagIndices.includes(index)}
                            onCheckedChange={() => toggleTag(index)}
                          />
                        )}
                        <Badge
                          variant={tag.is_new ? 'default' : 'secondary'}
                          className={`${tag.is_new ? 'bg-amber-600' : ''} ${
                            suggestion.tags_status === 'pending' && !selectedTagIndices.includes(index)
                              ? 'opacity-50 line-through'
                              : ''
                          }`}
                        >
                          {tag.is_new && <Plus className="h-3 w-3 mr-1" />}
                          {tag.tag_name}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {Math.round(tag.confidence * 100)}% confidence
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Additional Tags Section */}
                {suggestion.tags_status === 'pending' && (
                  <div>
                    <Label className="text-xs text-muted-foreground">Add Other Tags</Label>
                    <div className="flex flex-wrap gap-1 mt-1 items-center">
                      {additionalTagIds.map((tagId) => {
                        const tag = availableTags.find((t) => t.id === tagId);
                        return tag ? (
                          <Badge key={tagId} variant="default" className="bg-blue-600">
                            {tag.name}
                            <button
                              onClick={() => removeAdditionalTag(tagId)}
                              className="ml-1 hover:text-red-200"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </Badge>
                        ) : null;
                      })}
                      <Popover open={tagSelectorOpen} onOpenChange={setTagSelectorOpen}>
                        <PopoverTrigger asChild>
                          <Button variant="outline" size="sm" className="h-7">
                            <Plus className="h-3 w-3 mr-1" />
                            Add Tag
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="p-0 w-[250px]" align="start">
                          <Command shouldFilter={false}>
                            <CommandInput
                              placeholder="Search or create tag..."
                              value={newTagName}
                              onValueChange={setNewTagName}
                            />
                            <CommandList>
                              <CommandEmpty>
                                {newTagName.trim() ? (
                                  <button
                                    className="w-full px-2 py-3 text-sm text-left hover:bg-accent flex items-center gap-2"
                                    onClick={handleCreateTag}
                                    disabled={isCreatingTag}
                                  >
                                    {isCreatingTag ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <Plus className="h-4 w-4" />
                                    )}
                                    Create &quot;{newTagName.trim()}&quot;
                                  </button>
                                ) : (
                                  'No tags found.'
                                )}
                              </CommandEmpty>
                              {filteredTagsToAdd.length > 0 && (
                                <CommandGroup heading={newTagName.trim() ? `Matching (${filteredTagsToAdd.length}${availableTagsToAdd.length > 20 ? '+' : ''})` : `All Tags (${availableTagsToAdd.length})`}>
                                  {filteredTagsToAdd.map((tag) => (
                                    <CommandItem
                                      key={tag.id}
                                      value={tag.name}
                                      onSelect={() => addTag(tag.id)}
                                    >
                                      {tag.name}
                                    </CommandItem>
                                  ))}
                                </CommandGroup>
                              )}
                              {newTagName.trim() &&
                                !availableTagsToAdd.some(
                                  (t) => t.name.toLowerCase() === newTagName.trim().toLowerCase()
                                ) && (
                                  <CommandGroup heading="Create New">
                                    <CommandItem
                                      value={`create-${newTagName}`}
                                      onSelect={handleCreateTag}
                                      disabled={isCreatingTag}
                                    >
                                      {isCreatingTag ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                      ) : (
                                        <Plus className="h-4 w-4 mr-2" />
                                      )}
                                      Create &quot;{newTagName.trim()}&quot;
                                    </CommandItem>
                                  </CommandGroup>
                                )}
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </div>
                )}

                {/* Summary of what will be applied */}
                {suggestion.tags_status === 'pending' && (
                  <div className="p-3 bg-muted/50 rounded-lg space-y-2">
                    <div className="text-xs font-medium text-muted-foreground">Summary</div>
                    {rejectedSuggestedTags.length > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <X className="h-3 w-3 text-red-500" />
                        <span className="text-muted-foreground">Rejecting:</span>
                        <span className="line-through text-red-600">
                          {rejectedSuggestedTags.join(', ')}
                        </span>
                      </div>
                    )}
                    {(selectedSuggestedTags.length > 0 || additionalTagNames.length > 0) && (
                      <div className="flex items-center gap-2 text-sm">
                        <Check className="h-3 w-3 text-green-500" />
                        <span className="text-muted-foreground">Applying:</span>
                        <span className="text-green-600">
                          {[...selectedSuggestedTags, ...additionalTagNames].join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Notes Section */}
                {suggestion.tags_status === 'pending' && (
                  <div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs p-0 h-auto"
                      onClick={() => setShowNotes(!showNotes)}
                    >
                      <MessageSquare className="h-3 w-3 mr-1" />
                      {showNotes ? 'Hide notes' : 'Add notes (helps AI learn)'}
                    </Button>
                    {showNotes && (
                      <Textarea
                        placeholder="Explain why you're making these choices (optional). Example: 'medical should only be for human health records, not pet/vet bills'"
                        value={rejectionNotes}
                        onChange={(e) => setRejectionNotes(e.target.value)}
                        className="mt-2 text-sm"
                        rows={2}
                      />
                    )}
                  </div>
                )}

                {suggestion.tags_status === 'pending' && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="default"
                      onClick={handleApproveTags}
                      disabled={selectedTagIndices.length === 0 && additionalTagIds.length === 0}
                    >
                      <Check className="h-4 w-4 mr-1" />
                      Approve Selection
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleRejectTags}>
                      <X className="h-4 w-4 mr-1" />
                      Reject All
                    </Button>
                  </div>
                )}

                {/* Show applied state with what was chosen */}
                {suggestion.tags_status === 'approved' && (
                  <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="text-xs font-medium text-green-800 dark:text-green-200 mb-1">
                      Tags to be applied:
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {suggestion.selected_tag_indices?.map((i) => (
                        <Badge key={i} variant="secondary">
                          {suggestion.suggested_tags[i]?.tag_name}
                        </Badge>
                      ))}
                      {suggestion.additional_tag_ids?.map((tagId) => {
                        const tag = availableTags.find((t) => t.id === tagId);
                        return tag ? (
                          <Badge key={tagId} className="bg-blue-600">
                            {tag.name}
                          </Badge>
                        ) : null;
                      })}
                    </div>
                    {suggestion.rejection_notes && (
                      <div className="mt-2 pt-2 border-t border-green-200 dark:border-green-800">
                        <div className="text-xs text-green-700 dark:text-green-300 flex items-start gap-1">
                          <MessageSquare className="h-3 w-3 mt-0.5 flex-shrink-0" />
                          <span>{suggestion.rejection_notes}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Show rejection notes if tags were rejected */}
                {suggestion.tags_status === 'rejected' && suggestion.rejection_notes && (
                  <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                    <div className="text-xs text-red-700 dark:text-red-300 flex items-start gap-1">
                      <MessageSquare className="h-3 w-3 mt-0.5 flex-shrink-0" />
                      <span>{suggestion.rejection_notes}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Document Type Suggestion */}
            {suggestion.suggested_document_type && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <FileType className="h-4 w-4" />
                    Document Type Suggestion
                  </Label>
                  <StatusBadge status={suggestion.doc_type_status} />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-muted-foreground">Current</Label>
                    <div className="p-2 bg-muted rounded text-sm">
                      {suggestion.current_document_type || 'None'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Suggested</Label>
                    <div className="p-2 bg-muted rounded text-sm flex items-center gap-2">
                      {suggestion.suggested_document_type.is_new && (
                        <Badge variant="default" className="bg-amber-600 text-xs">
                          <Plus className="h-3 w-3 mr-1" />
                          New
                        </Badge>
                      )}
                      {suggestion.suggested_document_type.doc_type_name}
                      <span className="text-xs text-muted-foreground">
                        ({Math.round(suggestion.suggested_document_type.confidence * 100)}%)
                      </span>
                    </div>
                  </div>
                </div>

                {suggestion.doc_type_status === 'pending' && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="default" onClick={handleApproveType}>
                      <Check className="h-4 w-4 mr-1" />
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleRejectType}>
                      <X className="h-4 w-4 mr-1" />
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>

          <CardFooter className="flex justify-between border-t pt-4">
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={handleRejectAll}>
                Reject All
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => markForReprocess(suggestion.document_id)}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                Reprocess
              </Button>
              {hasApprovedSuggestions && (
                <Button variant="ghost" size="sm" onClick={handleReset}>
                  <Undo2 className="h-4 w-4 mr-1" />
                  Reset
                </Button>
              )}
            </div>
            {hasApprovedSuggestions && (
              <Button onClick={handleApply} disabled={isApplying}>
                {isApplying ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Applying...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Apply to Paperless
                  </>
                )}
              </Button>
            )}
          </CardFooter>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'pending':
      return (
        <Badge variant="outline" className="text-yellow-600 border-yellow-600">
          Pending
        </Badge>
      );
    case 'approved':
      return (
        <Badge variant="outline" className="text-green-600 border-green-600">
          <Check className="h-3 w-3 mr-1" />
          Approved
        </Badge>
      );
    case 'rejected':
      return (
        <Badge variant="outline" className="text-red-600 border-red-600">
          <X className="h-3 w-3 mr-1" />
          Rejected
        </Badge>
      );
    case 'applied':
      return (
        <Badge variant="default" className="bg-green-600">
          <Check className="h-3 w-3 mr-1" />
          Applied
        </Badge>
      );
    default:
      return null;
  }
}

export function SuggestionReview() {
  const {
    pendingSuggestions,
    suggestionsLoading,
    fetchPendingSuggestions,
    fetchTaxonomy,
    applyAllApproved,
    bulkApprove,
  } = useAIStore();

  const [isApplyingAll, setIsApplyingAll] = useState(false);

  useEffect(() => {
    fetchPendingSuggestions();
    fetchTaxonomy(); // Load all tags from Paperless-ngx
  }, [fetchPendingSuggestions, fetchTaxonomy]);

  const approvedCount = pendingSuggestions.filter(
    (s) =>
      s.title_status === 'approved' ||
      s.tags_status === 'approved' ||
      s.doc_type_status === 'approved'
  ).length;

  const handleApplyAll = async () => {
    setIsApplyingAll(true);
    try {
      await applyAllApproved();
    } finally {
      setIsApplyingAll(false);
    }
  };

  const handleBulkApprove = async () => {
    const docIds = pendingSuggestions.map((s) => s.document_id);
    await bulkApprove(docIds);
  };

  if (suggestionsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        Loading suggestions...
      </div>
    );
  }

  if (pendingSuggestions.length === 0) {
    return (
      <div className="text-center py-12">
        <Sparkles className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
        <h3 className="text-lg font-medium mb-2">No Pending Suggestions</h3>
        <p className="text-muted-foreground">
          Process some documents to generate AI suggestions
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Bulk Actions */}
      <Card>
        <CardContent className="flex items-center justify-between py-4">
          <div className="text-sm text-muted-foreground">
            {pendingSuggestions.length} documents with suggestions
            {approvedCount > 0 && ` (${approvedCount} approved)`}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleBulkApprove}>
              <Check className="h-4 w-4 mr-1" />
              Approve All
            </Button>
            {approvedCount > 0 && (
              <Button size="sm" onClick={handleApplyAll} disabled={isApplyingAll}>
                {isApplyingAll ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Applying...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-1" />
                    Apply All Approved ({approvedCount})
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Suggestion Cards */}
      <div className="space-y-4">
        {pendingSuggestions.map((suggestion) => (
          <SuggestionCard key={suggestion.document_id} suggestion={suggestion} />
        ))}
      </div>
    </div>
  );
}

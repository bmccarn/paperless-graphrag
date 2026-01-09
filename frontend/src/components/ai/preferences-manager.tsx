'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tag,
  FileType,
  History,
  Settings,
  Plus,
  Trash2,
  Edit,
  Loader2,
  AlertCircle,
  Info,
  User,
} from 'lucide-react';
import {
  TagDefinition,
  TagDefinitionRequest,
  DocTypeDefinition,
  DocTypeDefinitionRequest,
  CorrespondentDefinition,
  CorrespondentDefinitionRequest,
  TagCorrection,
  PreferenceSettings,
  PreferencesSummary,
  getTagDefinitions,
  setTagDefinition,
  deleteTagDefinition,
  getDocTypeDefinitions,
  setDocTypeDefinition,
  deleteDocTypeDefinition,
  getCorrespondentDefinitions,
  setCorrespondentDefinition,
  deleteCorrespondentDefinition,
  getCorrespondents,
  getCorrections,
  deleteCorrection,
  getPreferenceSettings,
  updatePreferenceSettings,
  getPreferencesSummary,
  getTags,
} from '@/lib/api/ai';

export function PreferencesManager() {
  const [summary, setSummary] = useState<PreferencesSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    try {
      const data = await getPreferencesSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to fetch preferences summary:', err);
    }
  };

  useEffect(() => {
    fetchSummary().finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        <span>Loading preferences...</span>
      </div>
    );
  }

  return (
    <Tabs defaultValue="tags" className="space-y-4">
      <TabsList className="grid w-full grid-cols-5">
        <TabsTrigger value="tags" className="flex items-center gap-2">
          <Tag className="h-4 w-4" />
          Tags
          {summary && summary.tag_definitions_count > 0 && (
            <Badge variant="secondary" className="ml-1">
              {summary.tag_definitions_count}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="doctypes" className="flex items-center gap-2">
          <FileType className="h-4 w-4" />
          Doc Types
          {summary && summary.doc_type_definitions_count > 0 && (
            <Badge variant="secondary" className="ml-1">
              {summary.doc_type_definitions_count}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="correspondents" className="flex items-center gap-2">
          <User className="h-4 w-4" />
          Correspondents
          {summary && summary.correspondent_definitions_count > 0 && (
            <Badge variant="secondary" className="ml-1">
              {summary.correspondent_definitions_count}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="corrections" className="flex items-center gap-2">
          <History className="h-4 w-4" />
          Corrections
          {summary && summary.corrections_count > 0 && (
            <Badge variant="secondary" className="ml-1">
              {summary.corrections_count}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="settings" className="flex items-center gap-2">
          <Settings className="h-4 w-4" />
          Settings
        </TabsTrigger>
      </TabsList>

      <TabsContent value="tags">
        <TagDefinitionsTab onUpdate={fetchSummary} />
      </TabsContent>

      <TabsContent value="doctypes">
        <DocTypeDefinitionsTab onUpdate={fetchSummary} />
      </TabsContent>

      <TabsContent value="correspondents">
        <CorrespondentDefinitionsTab onUpdate={fetchSummary} />
      </TabsContent>

      <TabsContent value="corrections">
        <CorrectionsTab onUpdate={fetchSummary} />
      </TabsContent>

      <TabsContent value="settings">
        <SettingsTab />
      </TabsContent>
    </Tabs>
  );
}

// =============================================================================
// Tag Definitions Tab
// =============================================================================

function TagDefinitionsTab({ onUpdate }: { onUpdate: () => void }) {
  const [definitions, setDefinitions] = useState<TagDefinition[]>([]);
  const [existingTags, setExistingTags] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingTag, setEditingTag] = useState<TagDefinition | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const fetchData = async () => {
    try {
      const [defs, tags] = await Promise.all([getTagDefinitions(), getTags()]);
      setDefinitions(defs);
      setExistingTags(tags.map((t) => t.name));
    } catch (err) {
      console.error('Failed to fetch tag definitions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSave = async (request: TagDefinitionRequest) => {
    await setTagDefinition(request);
    await fetchData();
    onUpdate();
    setIsDialogOpen(false);
    setEditingTag(null);
  };

  const handleDelete = async (tagName: string) => {
    await deleteTagDefinition(tagName);
    await fetchData();
    onUpdate();
  };

  // Find tags without definitions
  const undefinedTags = existingTags.filter(
    (tag) => !definitions.find((d) => d.tag_name.toLowerCase() === tag.toLowerCase())
  );

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Tag Definitions</CardTitle>
            <CardDescription>
              Define what each tag means to improve AI tagging accuracy and consistency.
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingTag(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Definition
              </Button>
            </DialogTrigger>
            <TagDefinitionDialog
              existingTags={existingTags}
              initialData={editingTag}
              onSave={handleSave}
              onCancel={() => {
                setIsDialogOpen(false);
                setEditingTag(null);
              }}
            />
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {undefinedTags.length > 0 && (
          <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-950 rounded-lg border border-amber-200 dark:border-amber-800">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div>
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  {undefinedTags.length} tags without definitions
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Consider adding definitions for: {undefinedTags.slice(0, 5).join(', ')}
                  {undefinedTags.length > 5 && ` and ${undefinedTags.length - 5} more`}
                </p>
              </div>
            </div>
          </div>
        )}

        {definitions.length === 0 ? (
          <EmptyState
            icon={Tag}
            title="No tag definitions yet"
            description="Add definitions to help the AI understand what each tag means in your document library."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tag</TableHead>
                <TableHead>Definition</TableHead>
                <TableHead>Exclude Contexts</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {definitions.map((def) => (
                <TableRow key={def.tag_name}>
                  <TableCell className="font-medium">
                    <Badge variant="outline">{def.tag_name}</Badge>
                  </TableCell>
                  <TableCell className="max-w-md truncate">{def.definition || '-'}</TableCell>
                  <TableCell>
                    {def.exclude_contexts.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {def.exclude_contexts.map((ctx) => (
                          <Badge key={ctx} variant="destructive" className="text-xs">
                            {ctx}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setEditingTag(def);
                          setIsDialogOpen(true);
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete tag definition?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will remove the definition for &quot;{def.tag_name}&quot;. The AI
                              will no longer have semantic guidance for this tag.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleDelete(def.tag_name)}>
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function TagDefinitionDialog({
  existingTags,
  initialData,
  onSave,
  onCancel,
}: {
  existingTags: string[];
  initialData: TagDefinition | null;
  onSave: (request: TagDefinitionRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [tagName, setTagName] = useState(initialData?.tag_name || '');
  const [definition, setDefinition] = useState(initialData?.definition || '');
  const [excludeContexts, setExcludeContexts] = useState(
    initialData?.exclude_contexts.join(', ') || ''
  );
  const [includeContexts, setIncludeContexts] = useState(
    initialData?.include_contexts.join(', ') || ''
  );
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      await onSave({
        tag_name: tagName,
        definition,
        exclude_contexts: excludeContexts
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        include_contexts: includeContexts
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <DialogContent className="sm:max-w-[500px]">
      <DialogHeader>
        <DialogTitle>{initialData ? 'Edit Tag Definition' : 'Add Tag Definition'}</DialogTitle>
        <DialogDescription>
          Define what this tag means to improve AI tagging accuracy.
        </DialogDescription>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label htmlFor="tagName">Tag Name</Label>
          {initialData ? (
            <Input id="tagName" value={tagName} disabled />
          ) : (
            <select
              id="tagName"
              value={tagName}
              onChange={(e) => setTagName(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">Select a tag...</option>
              {existingTags.map((tag) => (
                <option key={tag} value={tag}>
                  {tag}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="definition">Definition</Label>
          <Textarea
            id="definition"
            placeholder="e.g., Human health records including doctor visits, prescriptions, and medical bills"
            value={definition}
            onChange={(e) => setDefinition(e.target.value)}
            rows={3}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="excludeContexts">Exclude Contexts (comma-separated)</Label>
          <Input
            id="excludeContexts"
            placeholder="e.g., veterinary, pet, animal"
            value={excludeContexts}
            onChange={(e) => setExcludeContexts(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Keywords that should NOT trigger this tag
          </p>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="includeContexts">Include Contexts (comma-separated)</Label>
          <Input
            id="includeContexts"
            placeholder="e.g., doctor, hospital, prescription"
            value={includeContexts}
            onChange={(e) => setIncludeContexts(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">Keywords that should trigger this tag</p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!tagName || isSaving}>
          {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          Save
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

// =============================================================================
// Doc Type Definitions Tab
// =============================================================================

function DocTypeDefinitionsTab({ onUpdate }: { onUpdate: () => void }) {
  const [definitions, setDefinitions] = useState<DocTypeDefinition[]>([]);
  const [existingDocTypes, setExistingDocTypes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingDocType, setEditingDocType] = useState<DocTypeDefinition | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const fetchData = async () => {
    try {
      const [defs, docTypes] = await Promise.all([
        getDocTypeDefinitions(),
        import('@/lib/api/ai').then((m) => m.getDocumentTypes()),
      ]);
      setDefinitions(defs);
      setExistingDocTypes(docTypes.map((dt) => dt.name));
    } catch (err) {
      console.error('Failed to fetch doc type definitions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSave = async (request: DocTypeDefinitionRequest) => {
    await setDocTypeDefinition(request);
    await fetchData();
    onUpdate();
    setIsDialogOpen(false);
    setEditingDocType(null);
  };

  const handleDelete = async (docTypeName: string) => {
    await deleteDocTypeDefinition(docTypeName);
    await fetchData();
    onUpdate();
  };

  // Find doc types without definitions
  const undefinedDocTypes = existingDocTypes.filter(
    (dt) => !definitions.find((d) => d.doc_type_name.toLowerCase() === dt.toLowerCase())
  );

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Document Type Definitions</CardTitle>
            <CardDescription>
              Define what each document type means for better classification accuracy.
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingDocType(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Definition
              </Button>
            </DialogTrigger>
            <DocTypeDefinitionDialog
              existingDocTypes={existingDocTypes}
              initialData={editingDocType}
              onSave={handleSave}
              onCancel={() => {
                setIsDialogOpen(false);
                setEditingDocType(null);
              }}
            />
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {undefinedDocTypes.length > 0 && (
          <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-950 rounded-lg border border-amber-200 dark:border-amber-800">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div>
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  {undefinedDocTypes.length} document types without definitions
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Consider adding definitions for: {undefinedDocTypes.slice(0, 5).join(', ')}
                  {undefinedDocTypes.length > 5 && ` and ${undefinedDocTypes.length - 5} more`}
                </p>
              </div>
            </div>
          </div>
        )}

        {definitions.length === 0 ? (
          <EmptyState
            icon={FileType}
            title="No document type definitions yet"
            description="Document type definitions help the AI understand your document classification system."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Document Type</TableHead>
                <TableHead>Definition</TableHead>
                <TableHead>Exclude Contexts</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {definitions.map((def) => (
                <TableRow key={def.doc_type_name}>
                  <TableCell className="font-medium">
                    <Badge variant="outline">{def.doc_type_name}</Badge>
                  </TableCell>
                  <TableCell className="max-w-md truncate">{def.definition || '-'}</TableCell>
                  <TableCell>
                    {def.exclude_contexts.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {def.exclude_contexts.map((ctx) => (
                          <Badge key={ctx} variant="destructive" className="text-xs">
                            {ctx}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setEditingDocType(def);
                          setIsDialogOpen(true);
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete document type definition?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will remove the definition for &quot;{def.doc_type_name}&quot;.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleDelete(def.doc_type_name)}>
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function DocTypeDefinitionDialog({
  existingDocTypes,
  initialData,
  onSave,
  onCancel,
}: {
  existingDocTypes: string[];
  initialData: DocTypeDefinition | null;
  onSave: (request: DocTypeDefinitionRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [docTypeName, setDocTypeName] = useState(initialData?.doc_type_name || '');
  const [definition, setDefinition] = useState(initialData?.definition || '');
  const [excludeContexts, setExcludeContexts] = useState(
    initialData?.exclude_contexts.join(', ') || ''
  );
  const [includeContexts, setIncludeContexts] = useState(
    initialData?.include_contexts.join(', ') || ''
  );
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      await onSave({
        doc_type_name: docTypeName,
        definition,
        exclude_contexts: excludeContexts
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        include_contexts: includeContexts
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <DialogContent className="sm:max-w-[500px]">
      <DialogHeader>
        <DialogTitle>
          {initialData ? 'Edit Document Type Definition' : 'Add Document Type Definition'}
        </DialogTitle>
        <DialogDescription>
          Define what this document type means to improve AI classification accuracy.
        </DialogDescription>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label htmlFor="docTypeName">Document Type</Label>
          {initialData ? (
            <Input id="docTypeName" value={docTypeName} disabled />
          ) : (
            <select
              id="docTypeName"
              value={docTypeName}
              onChange={(e) => setDocTypeName(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">Select a document type...</option>
              {existingDocTypes.map((dt) => (
                <option key={dt} value={dt}>
                  {dt}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="definition">Definition</Label>
          <Textarea
            id="definition"
            placeholder="e.g., Official receipts showing payment confirmation for purchases or services"
            value={definition}
            onChange={(e) => setDefinition(e.target.value)}
            rows={3}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="excludeContexts">Exclude Contexts (comma-separated)</Label>
          <Input
            id="excludeContexts"
            placeholder="e.g., quote, estimate, proposal"
            value={excludeContexts}
            onChange={(e) => setExcludeContexts(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Keywords that should NOT trigger this document type
          </p>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="includeContexts">Include Contexts (comma-separated)</Label>
          <Input
            id="includeContexts"
            placeholder="e.g., paid, payment confirmed, transaction"
            value={includeContexts}
            onChange={(e) => setIncludeContexts(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Keywords that should trigger this document type
          </p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!docTypeName || isSaving}>
          {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          Save
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

// =============================================================================
// Correspondent Definitions Tab
// =============================================================================

function CorrespondentDefinitionsTab({ onUpdate }: { onUpdate: () => void }) {
  const [definitions, setDefinitions] = useState<CorrespondentDefinition[]>([]);
  const [existingCorrespondents, setExistingCorrespondents] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingCorrespondent, setEditingCorrespondent] = useState<CorrespondentDefinition | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const fetchData = async () => {
    try {
      const [defs, correspondents] = await Promise.all([
        getCorrespondentDefinitions(),
        getCorrespondents(),
      ]);
      setDefinitions(defs);
      setExistingCorrespondents(correspondents.map((c) => c.name));
    } catch (err) {
      console.error('Failed to fetch correspondent definitions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSave = async (request: CorrespondentDefinitionRequest) => {
    await setCorrespondentDefinition(request);
    await fetchData();
    onUpdate();
    setIsDialogOpen(false);
    setEditingCorrespondent(null);
  };

  const handleDelete = async (correspondentName: string) => {
    await deleteCorrespondentDefinition(correspondentName);
    await fetchData();
    onUpdate();
  };

  // Find correspondents without definitions
  const undefinedCorrespondents = existingCorrespondents.filter(
    (c) => !definitions.find((d) => d.correspondent_name.toLowerCase() === c.toLowerCase())
  );

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Correspondent Definitions</CardTitle>
            <CardDescription>
              Define what each correspondent means for consistent tagging and classification.
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => setEditingCorrespondent(null)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Definition
              </Button>
            </DialogTrigger>
            <CorrespondentDefinitionDialog
              existingCorrespondents={existingCorrespondents}
              initialData={editingCorrespondent}
              onSave={handleSave}
              onCancel={() => {
                setIsDialogOpen(false);
                setEditingCorrespondent(null);
              }}
            />
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {undefinedCorrespondents.length > 0 && (
          <div className="mb-4 p-4 bg-amber-50 dark:bg-amber-950 rounded-lg border border-amber-200 dark:border-amber-800">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div>
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  {undefinedCorrespondents.length} correspondents without definitions
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Consider adding definitions for: {undefinedCorrespondents.slice(0, 5).join(', ')}
                  {undefinedCorrespondents.length > 5 && ` and ${undefinedCorrespondents.length - 5} more`}
                </p>
              </div>
            </div>
          </div>
        )}

        {definitions.length === 0 ? (
          <EmptyState
            icon={User}
            title="No correspondent definitions yet"
            description="Add definitions to help the AI understand who each correspondent is and how to tag their documents."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Correspondent</TableHead>
                <TableHead>Definition</TableHead>
                <TableHead>Standard Tags</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {definitions.map((def) => (
                <TableRow key={def.correspondent_name}>
                  <TableCell className="font-medium">
                    <Badge variant="outline">{def.correspondent_name}</Badge>
                  </TableCell>
                  <TableCell className="max-w-md truncate">{def.definition || '-'}</TableCell>
                  <TableCell>
                    {def.standard_tags.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {def.standard_tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setEditingCorrespondent(def);
                          setIsDialogOpen(true);
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete correspondent definition?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will remove the definition for &quot;{def.correspondent_name}&quot;.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleDelete(def.correspondent_name)}>
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function CorrespondentDefinitionDialog({
  existingCorrespondents,
  initialData,
  onSave,
  onCancel,
}: {
  existingCorrespondents: string[];
  initialData: CorrespondentDefinition | null;
  onSave: (request: CorrespondentDefinitionRequest) => Promise<void>;
  onCancel: () => void;
}) {
  const [correspondentName, setCorrespondentName] = useState(initialData?.correspondent_name || '');
  const [definition, setDefinition] = useState(initialData?.definition || '');
  const [standardTags, setStandardTags] = useState(initialData?.standard_tags.join(', ') || '');
  const [standardDocType, setStandardDocType] = useState(initialData?.standard_document_type || '');
  const [notes, setNotes] = useState(initialData?.notes || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      await onSave({
        correspondent_name: correspondentName,
        definition,
        standard_tags: standardTags
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        standard_document_type: standardDocType || null,
        notes,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <DialogContent className="sm:max-w-[500px]">
      <DialogHeader>
        <DialogTitle>
          {initialData ? 'Edit Correspondent Definition' : 'Add Correspondent Definition'}
        </DialogTitle>
        <DialogDescription>
          Define what this correspondent means to improve AI tagging consistency.
        </DialogDescription>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label htmlFor="correspondentName">Correspondent</Label>
          {initialData ? (
            <Input id="correspondentName" value={correspondentName} disabled />
          ) : (
            <select
              id="correspondentName"
              value={correspondentName}
              onChange={(e) => setCorrespondentName(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">Select a correspondent...</option>
              {existingCorrespondents.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="definition">Definition</Label>
          <Textarea
            id="definition"
            placeholder="e.g., Chase Bank - our primary bank for personal checking and savings accounts"
            value={definition}
            onChange={(e) => setDefinition(e.target.value)}
            rows={3}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="standardTags">Standard Tags (comma-separated)</Label>
          <Input
            id="standardTags"
            placeholder="e.g., financial, banking, statement"
            value={standardTags}
            onChange={(e) => setStandardTags(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Tags commonly associated with documents from this correspondent
          </p>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="standardDocType">Standard Document Type</Label>
          <Input
            id="standardDocType"
            placeholder="e.g., Bank Statement"
            value={standardDocType}
            onChange={(e) => setStandardDocType(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Default document type for this correspondent
          </p>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="notes">Notes</Label>
          <Textarea
            id="notes"
            placeholder="Any additional context or notes about this correspondent..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!correspondentName || isSaving}>
          {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          Save
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

// =============================================================================
// Corrections Tab
// =============================================================================

function CorrectionsTab({ onUpdate }: { onUpdate: () => void }) {
  const [corrections, setCorrections] = useState<TagCorrection[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = async () => {
    try {
      const data = await getCorrections();
      setCorrections(data);
    } catch (err) {
      console.error('Failed to fetch corrections:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDelete = async (correctionId: string) => {
    await deleteCorrection(correctionId);
    await fetchData();
    onUpdate();
  };

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Learned Corrections</CardTitle>
        <CardDescription>
          Rules learned from your tag rejections. When you reject a suggested tag and accept
          others, the AI learns to avoid that mistake in similar contexts.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {corrections.length === 0 ? (
          <EmptyState
            icon={History}
            title="No corrections yet"
            description="Corrections are learned automatically when you reject tags during the approval process. The AI uses these to avoid repeating mistakes."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rejected Tag</TableHead>
                <TableHead>Use Instead</TableHead>
                <TableHead>Reason / Keywords</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {corrections.map((correction) => (
                <TableRow key={correction.id}>
                  <TableCell>
                    <Badge variant="destructive">{correction.rejected_tag}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {correction.preferred_tags.map((tag) => (
                        <Badge key={tag} variant="default">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1 max-w-sm">
                      {correction.reason && (
                        <p className="text-sm text-muted-foreground italic">
                          &quot;{correction.reason}&quot;
                        </p>
                      )}
                      {correction.context_keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {correction.context_keywords.slice(0, 5).map((kw) => (
                            <Badge key={kw} variant="outline" className="text-xs">
                              {kw}
                            </Badge>
                          ))}
                          {correction.context_keywords.length > 5 && (
                            <Badge variant="outline" className="text-xs">
                              +{correction.context_keywords.length - 5} more
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete correction?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will remove this learned rule. The AI may suggest &quot;
                            {correction.rejected_tag}&quot; again in similar contexts.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => handleDelete(correction.id)}>
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Settings Tab
// =============================================================================

function SettingsTab() {
  const [settings, setSettings] = useState<PreferenceSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const fetchSettings = async () => {
    try {
      const data = await getPreferenceSettings();
      setSettings(data);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleUpdate = async (updates: Partial<PreferenceSettings>) => {
    if (!settings) return;
    setIsSaving(true);
    try {
      const updated = await updatePreferenceSettings(updates);
      setSettings(updated);
    } catch (err) {
      console.error('Failed to update settings:', err);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !settings) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Consistency Settings</CardTitle>
          <CardDescription>Control how the AI prioritizes consistency vs novelty.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Consistency Mode</Label>
              <p className="text-sm text-muted-foreground">
                Prioritize consistent tagging across similar documents
              </p>
            </div>
            <Switch
              checked={settings.consistency_mode}
              onCheckedChange={(checked: boolean) => handleUpdate({ consistency_mode: checked })}
              disabled={isSaving}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Prefer Existing Tags</Label>
              <p className="text-sm text-muted-foreground">
                Strongly prefer existing tags over creating new ones
              </p>
            </div>
            <Switch
              checked={settings.prefer_existing_tags}
              onCheckedChange={(checked: boolean) => handleUpdate({ prefer_existing_tags: checked })}
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>New Taxonomy</CardTitle>
          <CardDescription>Control whether the AI can suggest new tags or types.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Allow New Tags</Label>
              <p className="text-sm text-muted-foreground">
                Allow AI to suggest creating new tags
              </p>
            </div>
            <Switch
              checked={settings.allow_new_tags}
              onCheckedChange={(checked: boolean) => handleUpdate({ allow_new_tags: checked })}
              disabled={isSaving}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Allow New Document Types</Label>
              <p className="text-sm text-muted-foreground">
                Allow AI to suggest creating new document types
              </p>
            </div>
            <Switch
              checked={settings.allow_new_doc_types}
              onCheckedChange={(checked: boolean) => handleUpdate({ allow_new_doc_types: checked })}
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Learning Settings</CardTitle>
          <CardDescription>Control automatic learning from your actions.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Learn from Corrections</Label>
              <p className="text-sm text-muted-foreground">
                Automatically learn when you reject suggested tags
              </p>
            </div>
            <Switch
              checked={settings.auto_learn_from_corrections}
              onCheckedChange={(checked: boolean) => handleUpdate({ auto_learn_from_corrections: checked })}
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Confidence Thresholds</CardTitle>
          <CardDescription>Minimum confidence levels for suggestions.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>Minimum Tag Confidence: {Math.round(settings.min_tag_confidence * 100)}%</Label>
            <input
              type="range"
              min="0"
              max="100"
              value={settings.min_tag_confidence * 100}
              onChange={(e) =>
                handleUpdate({ min_tag_confidence: parseInt(e.target.value) / 100 })
              }
              className="w-full"
              disabled={isSaving}
            />
          </div>
          <div className="grid gap-2">
            <Label>
              Minimum Document Type Confidence: {Math.round(settings.min_doc_type_confidence * 100)}
              %
            </Label>
            <input
              type="range"
              min="0"
              max="100"
              value={settings.min_doc_type_confidence * 100}
              onChange={(e) =>
                handleUpdate({ min_doc_type_confidence: parseInt(e.target.value) / 100 })
              }
              className="w-full"
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Helper Components
// =============================================================================

function LoadingState() {
  return (
    <div className="flex items-center justify-center p-8">
      <Loader2 className="h-6 w-6 animate-spin mr-2" />
      <span>Loading...</span>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icon className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-md">{description}</p>
    </div>
  );
}

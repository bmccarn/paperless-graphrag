/**
 * API client for AI-powered document processing
 */

import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export type SuggestionStatus = 'pending' | 'approved' | 'rejected' | 'applied' | 'failed';
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type ProcessingScope = 'selected' | 'unprocessed' | 'all';

export interface TagSuggestion {
  tag_id: number | null;
  tag_name: string;
  is_new: boolean;
  confidence: number;
}

export interface DocumentTypeSuggestion {
  doc_type_id: number | null;
  doc_type_name: string;
  is_new: boolean;
  confidence: number;
}

export interface DocumentSuggestion {
  document_id: number;
  current_title: string;
  current_tags: string[];
  current_document_type: string | null;
  suggested_title: string | null;
  suggested_tags: TagSuggestion[];
  suggested_document_type: DocumentTypeSuggestion | null;
  title_status: SuggestionStatus;
  tags_status: SuggestionStatus;
  doc_type_status: SuggestionStatus;
  modified_title: string | null;
  selected_tag_indices: number[] | null;
  additional_tag_ids: number[] | null;
  rejection_notes: string | null;
  created_at: string;
  processed_at: string | null;
  error: string | null;
}

export interface DocumentListItem {
  id: number;
  title: string;
  correspondent: string | null;
  document_type: string | null;
  tags: string[];
  created: string;
  added: string;
  has_pending_suggestions: boolean;
  ai_processed_at: string | null;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentDetail {
  id: number;
  title: string;
  content: string;
  correspondent: string | null;
  document_type: string | null;
  tags: { id: number; name: string }[];
  created: string;
  modified: string;
  added: string;
  ai_processed_at: string | null;
  suggestion: DocumentSuggestion | null;
}

export interface Tag {
  id: number;
  name: string;
  color: string | null;
}

export interface DocumentType {
  id: number;
  name: string;
}

export interface ProcessingRequest {
  scope: ProcessingScope;
  document_ids: number[];
  generate_titles: boolean;
  suggest_tags: boolean;
  suggest_document_type: boolean;
  auto_apply: boolean;
}

export interface ProcessingResponse {
  job_id: string;
  status: JobStatus;
  document_count: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress_current: number;
  progress_total: number;
  current_document_title: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  errors: string[];
}

export interface ApprovalRequest {
  approve_title?: boolean | null;
  approve_tags?: boolean | null;
  approve_document_type?: boolean | null;
  modified_title?: string | null;
  selected_tag_indices?: number[] | null;
  additional_tag_ids?: number[] | null;
  rejection_notes?: string | null;
}

export interface ApplyResult {
  document_id: number;
  success: boolean;
  title_applied: boolean;
  tags_applied: boolean;
  document_type_applied: boolean;
  tags_created: string[];
  document_type_created: string | null;
  error: string | null;
}

export interface BulkApplyResponse {
  total: number;
  successful: number;
  failed: number;
  results: ApplyResult[];
}

export interface AIStats {
  pending_suggestions: number;
  processed_documents: number;
  active_jobs: number;
  completed_jobs: number;
  total_jobs: number;
}

// =============================================================================
// Document Discovery
// =============================================================================

export interface DocumentFilters {
  page?: number;
  page_size?: number;
  search?: string;
  has_tags?: boolean;
  has_document_type?: boolean;
  ai_processed?: boolean;
}

export async function getDocuments(filters: DocumentFilters = {}): Promise<DocumentListResponse> {
  const params = new URLSearchParams();

  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  if (filters.search) params.set('search', filters.search);
  if (filters.has_tags !== undefined) params.set('has_tags', String(filters.has_tags));
  if (filters.has_document_type !== undefined) params.set('has_document_type', String(filters.has_document_type));
  if (filters.ai_processed !== undefined) params.set('ai_processed', String(filters.ai_processed));

  const queryString = params.toString();
  const endpoint = queryString ? `/ai/documents?${queryString}` : '/ai/documents';

  return apiClient.get<DocumentListResponse>(endpoint);
}

export async function getDocumentDetail(docId: number): Promise<DocumentDetail> {
  return apiClient.get<DocumentDetail>(`/ai/documents/${docId}`);
}

// =============================================================================
// Taxonomy
// =============================================================================

export async function getTags(): Promise<Tag[]> {
  return apiClient.get<Tag[]>('/ai/tags');
}

export async function getDocumentTypes(): Promise<DocumentType[]> {
  return apiClient.get<DocumentType[]>('/ai/document-types');
}

export async function createTag(name: string, color?: string): Promise<Tag> {
  return apiClient.post<Tag>('/ai/tags', { name, color });
}

export async function createDocumentType(name: string): Promise<DocumentType> {
  return apiClient.post<DocumentType>('/ai/document-types', { name });
}

// =============================================================================
// AI Processing
// =============================================================================

export async function startProcessing(request: ProcessingRequest): Promise<ProcessingResponse> {
  return apiClient.post<ProcessingResponse>('/ai/process', request);
}

export async function getJobs(limit: number = 20): Promise<JobStatusResponse[]> {
  return apiClient.get<JobStatusResponse[]>(`/ai/jobs?limit=${limit}`);
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return apiClient.get<JobStatusResponse>(`/ai/jobs/${jobId}`);
}

// =============================================================================
// Suggestions
// =============================================================================

export async function getPendingSuggestions(): Promise<DocumentSuggestion[]> {
  return apiClient.get<DocumentSuggestion[]>('/ai/suggestions');
}

export async function getDocumentSuggestion(docId: number): Promise<DocumentSuggestion> {
  return apiClient.get<DocumentSuggestion>(`/ai/suggestions/${docId}`);
}

export async function approveSuggestion(
  docId: number,
  request: ApprovalRequest
): Promise<{ success: boolean; suggestion: DocumentSuggestion }> {
  return apiClient.post(`/ai/suggestions/${docId}/approve`, request);
}

export async function rejectSuggestion(docId: number): Promise<{ success: boolean }> {
  return apiClient.post(`/ai/suggestions/${docId}/reject`);
}

export async function applySuggestion(docId: number): Promise<ApplyResult> {
  return apiClient.post<ApplyResult>(`/ai/suggestions/${docId}/apply`);
}

export async function applyAllApproved(): Promise<BulkApplyResponse> {
  return apiClient.post<BulkApplyResponse>('/ai/suggestions/apply-all');
}

export async function bulkApprove(
  documentIds: number[],
  options: {
    approve_titles?: boolean;
    approve_tags?: boolean;
    approve_document_types?: boolean;
  } = {}
): Promise<{ success: boolean; approved_count: number }> {
  return apiClient.post('/ai/suggestions/bulk-approve', {
    document_ids: documentIds,
    approve_titles: options.approve_titles ?? true,
    approve_tags: options.approve_tags ?? true,
    approve_document_types: options.approve_document_types ?? true,
  });
}

export async function deleteSuggestion(docId: number): Promise<{ success: boolean }> {
  return apiClient.delete(`/ai/suggestions/${docId}`);
}

export async function markForReprocess(docId: number): Promise<{ success: boolean; was_processed: boolean }> {
  return apiClient.post(`/ai/documents/${docId}/reprocess`);
}

export async function resetSuggestion(docId: number): Promise<{ success: boolean; suggestion: DocumentSuggestion }> {
  return apiClient.post(`/ai/suggestions/${docId}/reset`);
}

// =============================================================================
// Stats
// =============================================================================

export async function getAIStats(): Promise<AIStats> {
  return apiClient.get<AIStats>('/ai/stats');
}

// =============================================================================
// Preferences Types
// =============================================================================

export interface TagDefinition {
  tag_name: string;
  definition: string;
  examples: string[];
  exclude_contexts: string[];
  include_contexts: string[];
  created_at: string;
  updated_at: string;
}

export interface TagDefinitionRequest {
  tag_name: string;
  definition?: string;
  examples?: string[];
  exclude_contexts?: string[];
  include_contexts?: string[];
}

export interface DocTypeDefinition {
  doc_type_name: string;
  definition: string;
  examples: string[];
  exclude_contexts: string[];
  include_contexts: string[];
  created_at: string;
  updated_at: string;
}

export interface DocTypeDefinitionRequest {
  doc_type_name: string;
  definition?: string;
  examples?: string[];
  exclude_contexts?: string[];
  include_contexts?: string[];
}

export interface CorrespondentDefinition {
  correspondent_name: string;
  definition: string;
  standard_tags: string[];
  standard_document_type: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CorrespondentDefinitionRequest {
  correspondent_name: string;
  definition?: string;
  standard_tags?: string[];
  standard_document_type?: string | null;
  notes?: string;
}

export interface Correspondent {
  id: number;
  name: string;
}

export interface TagCorrection {
  id: string;
  created_at: string;
  document_id: number | null;
  document_snippet: string | null;
  context_keywords: string[];
  rejected_tag: string;
  preferred_tags: string[];
  reason: string | null;
}

export interface PreferenceSettings {
  consistency_mode: boolean;
  prefer_existing_tags: boolean;
  min_similar_docs_for_tag: number;
  similar_doc_count: number;
  min_tag_confidence: number;
  min_doc_type_confidence: number;
  allow_new_tags: boolean;
  allow_new_doc_types: boolean;
  new_tag_confidence_boost: number;
  auto_learn_from_corrections: boolean;
}

export interface PreferenceSettingsRequest {
  consistency_mode?: boolean;
  prefer_existing_tags?: boolean;
  min_similar_docs_for_tag?: number;
  similar_doc_count?: number;
  min_tag_confidence?: number;
  min_doc_type_confidence?: number;
  allow_new_tags?: boolean;
  allow_new_doc_types?: boolean;
  auto_learn_from_corrections?: boolean;
}

export interface PreferencesSummary {
  settings: PreferenceSettings;
  tag_definitions_count: number;
  doc_type_definitions_count: number;
  correspondent_definitions_count: number;
  corrections_count: number;
  updated_at: string;
}

// =============================================================================
// Preferences API
// =============================================================================

export async function getPreferencesSummary(): Promise<PreferencesSummary> {
  return apiClient.get<PreferencesSummary>('/ai/preferences');
}

export async function getPreferenceSettings(): Promise<PreferenceSettings> {
  return apiClient.get<PreferenceSettings>('/ai/preferences/settings');
}

export async function updatePreferenceSettings(
  settings: PreferenceSettingsRequest
): Promise<PreferenceSettings> {
  return apiClient.put<PreferenceSettings>('/ai/preferences/settings', settings);
}

// Tag Definitions
export async function getTagDefinitions(): Promise<TagDefinition[]> {
  return apiClient.get<TagDefinition[]>('/ai/preferences/tags');
}

export async function getTagDefinition(tagName: string): Promise<TagDefinition> {
  return apiClient.get<TagDefinition>(`/ai/preferences/tags/${encodeURIComponent(tagName)}`);
}

export async function setTagDefinition(request: TagDefinitionRequest): Promise<TagDefinition> {
  return apiClient.put<TagDefinition>('/ai/preferences/tags', request);
}

export async function deleteTagDefinition(tagName: string): Promise<{ success: boolean }> {
  return apiClient.delete(`/ai/preferences/tags/${encodeURIComponent(tagName)}`);
}

// Document Type Definitions
export async function getDocTypeDefinitions(): Promise<DocTypeDefinition[]> {
  return apiClient.get<DocTypeDefinition[]>('/ai/preferences/doc-types');
}

export async function getDocTypeDefinition(docTypeName: string): Promise<DocTypeDefinition> {
  return apiClient.get<DocTypeDefinition>(`/ai/preferences/doc-types/${encodeURIComponent(docTypeName)}`);
}

export async function setDocTypeDefinition(request: DocTypeDefinitionRequest): Promise<DocTypeDefinition> {
  return apiClient.put<DocTypeDefinition>('/ai/preferences/doc-types', request);
}

export async function deleteDocTypeDefinition(docTypeName: string): Promise<{ success: boolean }> {
  return apiClient.delete(`/ai/preferences/doc-types/${encodeURIComponent(docTypeName)}`);
}

// Correspondents
export async function getCorrespondents(): Promise<Correspondent[]> {
  return apiClient.get<Correspondent[]>('/ai/correspondents');
}

// Correspondent Definitions
export async function getCorrespondentDefinitions(): Promise<CorrespondentDefinition[]> {
  return apiClient.get<CorrespondentDefinition[]>('/ai/preferences/correspondents');
}

export async function getCorrespondentDefinition(correspondentName: string): Promise<CorrespondentDefinition> {
  return apiClient.get<CorrespondentDefinition>(`/ai/preferences/correspondents/${encodeURIComponent(correspondentName)}`);
}

export async function setCorrespondentDefinition(request: CorrespondentDefinitionRequest): Promise<CorrespondentDefinition> {
  return apiClient.put<CorrespondentDefinition>('/ai/preferences/correspondents', request);
}

export async function deleteCorrespondentDefinition(correspondentName: string): Promise<{ success: boolean }> {
  return apiClient.delete(`/ai/preferences/correspondents/${encodeURIComponent(correspondentName)}`);
}

// Corrections
export async function getCorrections(): Promise<TagCorrection[]> {
  return apiClient.get<TagCorrection[]>('/ai/preferences/corrections');
}

export async function deleteCorrection(correctionId: string): Promise<{ success: boolean }> {
  return apiClient.delete(`/ai/preferences/corrections/${correctionId}`);
}

